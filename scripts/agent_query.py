from __future__ import annotations

import argparse
from pathlib import Path

import _bootstrap  # noqa: F401

from opengrid_mvp.agent import (
    format_plan_preview,
    format_run_result,
    preview_agent_request,
    run_agent_request,
)
from opengrid_mvp.source_registry import REGISTERED_SOURCES


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plan, geocode, fetch, and save GeoJSON for a natural-language request."
    )
    parser.add_argument(
        "query",
        nargs="*",
        help="Natural-language geospatial data request. Omit it to enter interactive mode.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory where GeoJSON outputs should be written.",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Use deterministic keyword planning instead of the LangChain LLM planner.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="LLM chat model name for LangChain planning (overrides LLM_PROVIDER env default).",
    )
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Show the planned place, BBOX, and sources. Do not fetch datasets.",
    )
    parser.add_argument(
        "--no-geocode-preview",
        action="store_true",
        help="With --plan-only, skip geocoding and only show place/radius/source planning.",
    )
    parser.add_argument(
        "--list-sources",
        action="store_true",
        help="List registered data sources and exit.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Enter an interactive query loop.",
    )
    args = parser.parse_args()

    if args.list_sources:
        print_source_list()
        return

    query = " ".join(args.query).strip()
    if args.interactive or not query:
        run_interactive(args)
        return

    run_single_query(query, args)


def run_single_query(query: str, args: argparse.Namespace) -> None:
    if args.plan_only:
        if args.no_geocode_preview:
            from opengrid_mvp.agent import plan_request

            plan = plan_request(query, model=args.model, use_llm=not args.no_llm)
            aoi = None
        else:
            plan, aoi = preview_agent_request(
                query,
                model=args.model,
                use_llm=not args.no_llm,
            )
        print(format_plan_preview(plan, aoi))
        return

    result = run_agent_request(
        query,
        output_dir=args.output_dir,
        model=args.model,
        use_llm=not args.no_llm,
    )
    print(format_run_result(result))


def run_interactive(args: argparse.Namespace) -> None:
    print("OpenGridWorks agent query mode")
    print("Type a natural-language request. Type 'exit' or 'quit' to stop.")
    print("Use --plan-only before launching if you only want previews.")
    while True:
        try:
            query = input("\nQuery> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not query or query.lower() in {"exit", "quit", "q"}:
            return
        try:
            run_single_query(query, args)
        except Exception as exc:
            print(f"Error: {exc}")


def print_source_list() -> None:
    print("Registered data sources:")
    for source in REGISTERED_SOURCES.values():
        print(f"- {source.source_id}")
        print(f"  name: {source.source_name}")
        print(f"  category: {source.category}")
        print(f"  output: {source.output_kind}")
        print(f"  description: {source.description}")
        print(f"  aliases: {', '.join(source.aliases)}")


if __name__ == "__main__":
    main()
