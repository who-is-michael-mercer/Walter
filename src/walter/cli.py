from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

from agents import Runner, SQLiteSession, trace
from dotenv import load_dotenv

from .runtime import build_walter


DEFAULT_SESSION = "main"
DEFAULT_MAX_TURNS = 30


def _session_db() -> str:
    local_dir = Path.cwd() / ".local"
    local_dir.mkdir(parents=True, exist_ok=True)
    return str(local_dir / "walter-sessions.db")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="walter",
        description="Run Walter, the general-purpose orchestration Manager.",
    )
    parser.add_argument(
        "goal",
        nargs="*",
        help="Optional one-shot goal. Omit it to start an interactive Walter session.",
    )
    parser.add_argument(
        "--session",
        default=None,
        help=(
            "Persist conversation state under this session ID. Interactive mode defaults "
            f"to '{DEFAULT_SESSION}'."
        ),
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=DEFAULT_MAX_TURNS,
        help=f"Maximum manager turns per run (default: {DEFAULT_MAX_TURNS}).",
    )
    parser.add_argument(
        "--trace-sensitive",
        action="store_true",
        help=(
            "Include model/tool inputs and outputs in exported OpenAI traces. Off by default "
            "so trace structure is visible without exporting prompt contents."
        ),
    )
    return parser


def _require_api_key() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit(
            "OPENAI_API_KEY is not set. Export it in your shell or add it to a local .env file."
        )


def _configure_trace_privacy(include_sensitive: bool) -> None:
    os.environ["OPENAI_AGENTS_TRACE_INCLUDE_SENSITIVE_DATA"] = (
        "1" if include_sensitive else "0"
    )


async def _execute(
    walter,
    goal: str,
    *,
    session=None,
    session_id: str | None = None,
    max_turns: int,
):
    metadata = {"runtime": "agents-sdk", "manager": "Walter"}
    with trace(
        "Walter orchestration",
        group_id=session_id,
        metadata=metadata,
    ) as workflow_trace:
        result = await Runner.run(
            walter,
            goal,
            session=session,
            max_turns=max_turns,
        )
    return result, workflow_trace.trace_id


async def _run_once(goal: str, session_id: str | None, max_turns: int) -> None:
    walter = build_walter()
    session = SQLiteSession(session_id, _session_db()) if session_id else None
    result, trace_id = await _execute(
        walter,
        goal,
        session=session,
        session_id=session_id,
        max_turns=max_turns,
    )
    print(result.final_output)
    print(f"\nTrace ID: {trace_id}")


async def _run_interactive(session_id: str, max_turns: int) -> None:
    walter = build_walter()
    session = SQLiteSession(session_id, _session_db())

    print(f"Walter ready. Session: {session_id}")
    print("Commands: :clear resets this conversation, :quit exits.")
    print("Tracing: enabled. Each completed goal prints its OpenAI trace ID.")

    while True:
        try:
            goal = input("\nwalter> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if not goal:
            continue
        if goal in {":quit", ":q", "quit", "exit"}:
            return
        if goal == ":clear":
            await session.clear_session()
            print("Session cleared.")
            continue

        try:
            result, trace_id = await _execute(
                walter,
                goal,
                session=session,
                session_id=session_id,
                max_turns=max_turns,
            )
            print(f"\n{result.final_output}")
            print(f"\nTrace ID: {trace_id}")
        except KeyboardInterrupt:
            print("\nRun interrupted.")


def main() -> None:
    load_dotenv()
    _require_api_key()
    args = _parser().parse_args()
    _configure_trace_privacy(args.trace_sensitive)

    if args.max_turns < 1:
        raise SystemExit("--max-turns must be at least 1.")

    goal = " ".join(args.goal).strip()
    if goal:
        asyncio.run(_run_once(goal, args.session, args.max_turns))
        return

    asyncio.run(_run_interactive(args.session or DEFAULT_SESSION, args.max_turns))


if __name__ == "__main__":
    main()
