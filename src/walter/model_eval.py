"""Opt-in, six-request provider probe; no model output is executed or applied.

Run: python -m walter.model_eval --live
Redirect stdout to preserve the JSON report. Credentials are never included.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from urllib.request import urlopen

from agents import Agent, ModelRetrySettings, ModelSettings, RunConfig, Runner
from dotenv import load_dotenv

from .runtime import (
    DEFAULT_OPENROUTER_BASE_URL, PREFERRED_LOW_COST_MODEL, PREFERRED_REASONING_MODEL,
    RuntimeConfig, _openrouter_client, build_models,
)

MODELS = (PREFERRED_REASONING_MODEL, PREFERRED_LOW_COST_MODEL)
MAX_CALLS = 6
MAX_OUTPUT_TOKENS = 1024
MAX_INPUT_TOKENS = 8192  # <=4096 UTF-8 prompt bytes, plus ample framing allowance.
MAX_PRICE = {"prompt": 5, "completion": 20, "request": 0}  # USD per million tokens.
SOFT_BUDGET = 2.0
HARD_BUDGET = 3.0
CALL_RESERVE = (MAX_INPUT_TOKENS * 5 + MAX_OUTPUT_TOKENS * 20) / 1_000_000
INSTRUCTIONS = "Return only the requested JSON object. Be concise. Do not use tools."
CASES = (
    ("reasoning", 'Classify pending tasks by accepted dependencies only. A is accepted; '
     'B pending depends on A; C pending depends on B; D pending depends on X; X has a '
     'worker submission marked completed but no Manager acceptance. Return '
     '{"ready":[IDs],"blocked":[IDs]} with sorted arrays; classify only B,C,D.',
     {"ready": ["B"], "blocked": ["C", "D"]}),
    ("implementation", 'Implement one exact source edit. Existing Python expression: '
     'all(states[d] == "completed" for d in deps). Dependency gate must require '
     '"accepted" for every dependency. Preserve the expression otherwise. Return '
     '{"replacement":"the corrected expression"}.',
     {"replacement": 'all(states[d] == "accepted" for d in deps)'}),
    ("review", 'Review this proposed dependency gate: ready = '
     'all(states[d] in {"completed", "accepted"} for d in deps). A completed worker '
     'submission is provisional; only Manager acceptance releases dependencies. '
     'Return {"accept":boolean,"counterexample":{"dependency_state":string,'
     '"actual_ready":boolean,"expected_ready":boolean}} for a single dependency '
     'demonstrating the bug.',
     {"accept": False, "counterexample": {"dependency_state": "completed",
      "actual_ready": True, "expected_ready": False}}),
)


def accepted(role: str, output: str) -> bool:
    """Strict JSON + exact fixture oracle. Generated implementation is never executed."""
    expected = next(expected for name, _, expected in CASES if name == role)
    try:
        return json.loads(output) == expected
    except (ValueError, TypeError):
        return False


def request_settings() -> ModelSettings:
    return ModelSettings(
        max_tokens=MAX_OUTPUT_TOKENS, retry=ModelRetrySettings(max_retries=0),
        preserve_raw_usage=True,
        extra_body={"provider": {"allow_fallbacks": False, "require_parameters": True,
                                 "max_price": MAX_PRICE},
                    "reasoning": {"effort": "low"}},
    )


def validate_plan(catalog: dict) -> list[dict]:
    if MAX_CALLS != len(MODELS) * len(CASES):
        raise ValueError("call plan mismatch")
    if MAX_CALLS * CALL_RESERVE > min(SOFT_BUDGET, HARD_BUDGET):
        raise ValueError("call plan exceeds budget")
    for _, prompt, _ in CASES:
        if len((INSTRUCTIONS + prompt).encode("utf-8")) > 4096:
            raise ValueError("fixture exceeds conservative input bound")
    found = {item["id"]: item for item in catalog["data"]}
    selected = []
    for model in MODELS:
        item = found.get(model)
        if item is None:
            raise ValueError("requested model unavailable in current catalog")
        if not {"max_tokens", "reasoning"} <= set(item["supported_parameters"]):
            raise ValueError("required bounded request parameters unavailable")
        pricing = item["pricing"]
        for rates in [pricing, *pricing.get("overrides", [])]:
            if any(float(rates.get(k, pricing[k])) * 1_000_000 > MAX_PRICE[k]
                   for k in ("prompt", "completion")):
                raise ValueError("catalog price exceeds request ceiling")
        selected.append({"id": model, "pricing": pricing})
    return selected


def fetch_catalog() -> dict:
    with urlopen(f"{DEFAULT_OPENROUTER_BASE_URL}/models", timeout=20) as response:
        return json.load(response)


async def evaluate() -> dict:
    config = RuntimeConfig.from_env()
    if config.base_url != DEFAULT_OPENROUTER_BASE_URL:
        raise ValueError("evaluation requires official OpenRouter endpoint")
    catalog = validate_plan(await asyncio.to_thread(fetch_catalog))
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "catalog_source": f"{DEFAULT_OPENROUTER_BASE_URL}/models",
        "catalog": catalog, "max_calls": MAX_CALLS,
        "max_output_tokens_per_call": MAX_OUTPUT_TOKENS,
        "soft_budget_usd": SOFT_BUDGET, "hard_budget_usd": HARD_BUDGET,
        "planned_reserve_usd": MAX_CALLS * CALL_RESERVE,
        "price_ceiling_usd_per_million_tokens": MAX_PRICE,
        "results": [], "reserved_usd": 0.0,
    }
    for model in MODELS:
        pricing = next(item["pricing"] for item in catalog if item["id"] == model)
        scoped = RuntimeConfig(config.provider, config.api_key, config.base_url, model, model)
        manager_model, _ = build_models(scoped)
        try:
            for role, prompt, _ in CASES:
                if report["reserved_usd"] + CALL_RESERVE > min(SOFT_BUDGET, HARD_BUDGET):
                    report["stop_reason"] = "budget"
                    return report
                report["reserved_usd"] += CALL_RESERVE  # charge reserve even on timeout
                row = {"model": model, "role": role, "attempts": 1,
                       "reserved_cost_usd": CALL_RESERVE}
                report["results"].append(row)
                start = time.monotonic()
                try:
                    result = await asyncio.wait_for(Runner.run(
                        Agent(name=f"Walter {role} evaluation", instructions=INSTRUCTIONS,
                              model=manager_model, model_settings=request_settings()),
                        prompt, max_turns=1,
                        run_config=RunConfig(tracing_disabled=True,
                                             trace_include_sensitive_data=False),
                    ), timeout=60)
                    usage = result.context_wrapper.usage
                    reported_costs = [response.raw_usage.get("cost")
                                      for response in result.raw_responses
                                      if isinstance(response.raw_usage, dict)]
                    billed_cost = (sum(reported_costs) if reported_costs and
                                   all(isinstance(cost, (int, float)) for cost in reported_costs)
                                   else None)
                    row.update(output=result.final_output, accepted=accepted(role, result.final_output),
                               input_tokens=usage.input_tokens, output_tokens=usage.output_tokens,
                               provider_reported_cost_usd=billed_cost,
                               cost_upper_estimate_usd=(usage.input_tokens * 5 + usage.output_tokens * 20)
                               / 1_000_000,
                               catalog_base_cost_estimate_usd=(
                                   usage.input_tokens * float(pricing["prompt"])
                                   + usage.output_tokens * float(pricing["completion"])),
                               outcome="returned")
                    if usage.input_tokens > MAX_INPUT_TOKENS or usage.output_tokens > MAX_OUTPUT_TOKENS:
                        row["outcome"] = "usage_bound_violated"
                        report["stop_reason"] = "usage_bound_violated"
                        return report
                except Exception as error:
                    # Exception strings/bodies can contain credentials or request contents.
                    row.update(outcome="provider_or_sdk_error", accepted=False,
                               error_type=type(error).__name__,
                               http_status=getattr(error, "status_code", None))
                    report["stop_reason"] = "availability_uncertain_no_retry"
                    return report
                finally:
                    row["latency_seconds"] = round(time.monotonic() - start, 3)
        finally:
            await _openrouter_client(scoped).close()
            _openrouter_client.cache_clear()
    report["stop_reason"] = "completed_bounded_plan"
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="authorize up to six paid requests")
    args = parser.parse_args()
    if not args.live:
        parser.error("explicit --live is required; maximum reserved spend is $0.36864")
    load_dotenv(override=False)
    # Third-party error logs may include provider request/response bodies.
    logging.disable(logging.CRITICAL)
    try:
        report = asyncio.run(evaluate())
    except Exception as error:
        report = {"stop_reason": "preflight_failed_no_requests", "error_type": type(error).__name__}
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
