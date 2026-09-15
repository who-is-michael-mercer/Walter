from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

from agents import Runner, SQLiteSession
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
    return parser


def _require_api_key() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit(
            "OPENAI_API_KEY is not set. Export it in your shell or add it to a local .env file."
        )


async def _run_once(goal: str, session_id: str | None, max_turns: int) -> None:
    walter = build_walter()
    kwargs = {}
    if session_id:
        kwargs["session"] = SQLiteSession(session_id, _session_db())

    result = await Runner.run(walter, goal, max_turns=max_turns, **kwargs)
    print(result.final_output)


async def _run_interactive(session_id: str, max_turns: int) -> None:
    walter = build_walter()
    session = SQLiteSession(session_id, _session_db())

    print(f"Walter ready. Session: {session_id}")
    print("Commands: :clear resets this conversation, :quit exits.")

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
            result = await Runner.run(
                walter,
                goal,
                session=session,
                max_turns=max_turns,
            )
            print(f"\n{result.final_output}")
        except KeyboardInterrupt:
            print("\nRun interrupted.")


def main() -> None:
    load_dotenv()
    _require_api_key()
    args = _parser().parse_args()

    if args.max_turns < 1:
        raise SystemExit("--max-turns must be at least 1.")

    goal = " ".join(args.goal).strip()
    if goal:
        asyncio.run(_run_once(goal, args.session, args.max_turns))
        return

    asyncio.run(_run_interactive(args.session or DEFAULT_SESSION, args.max_turns))


if __name__ == "__main__":
    main()
