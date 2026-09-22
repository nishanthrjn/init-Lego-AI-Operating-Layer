"""`legoai-documind` CLI entry point: `ingest`, `ask`, `status`.

Understandable errors by default (task's own instruction): known failure
modes (unsupported file extension, parsing/chunking validation errors,
governed-invocation denial/dispatch/provider failures) are caught and
printed as one-line messages with exit code 1, never a raw traceback --
unless `--debug` is passed, in which case the original exception
propagates so a developer can see the full stack.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from legoai_document.parsing.errors import (
    EncryptedDocumentError,
    MalformedDocumentError,
    UnsupportedDocumentFormatError,
)

from documind_app.app import DocuMindApplication, UnrecognizedFileExtensionError
from documind_app.composition import DocuMindRuntime, GovernedInvocationError
from documind_app.config import DocuMindConfig
from documind_app.status import check_ollama_status

_EXPECTED_ERRORS = (
    UnrecognizedFileExtensionError,
    UnsupportedDocumentFormatError,
    MalformedDocumentError,
    EncryptedDocumentError,
    GovernedInvocationError,
    OSError,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="legoai-documind")
    parser.add_argument(
        "--debug", action="store_true", help="show full tracebacks on failure"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser(
        "ingest", help="parse, chunk, embed, and index one or more documents"
    )
    ingest_parser.add_argument(
        "paths", nargs="+", help="files or directories to ingest"
    )

    ask_parser = subparsers.add_parser(
        "ask", help="ask a question over ingested documents"
    )
    ask_parser.add_argument("question")

    subparsers.add_parser(
        "status", help="check Ollama reachability and model availability"
    )

    return parser


def _iter_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path)
        if path.is_dir():
            files.extend(sorted(p for p in path.rglob("*") if p.is_file()))
        else:
            files.append(path)
    return files


async def _run_ingest(app: DocuMindApplication, paths: list[str]) -> int:
    exit_code = 0
    for path in _iter_files(paths):
        try:
            result = await app.ingest_path(path)
        except _EXPECTED_ERRORS as exc:
            print(f"skipped {path}: {exc}", file=sys.stderr)
            exit_code = 1
            continue
        print(
            f"ingested {path}: {result.page_count} page(s), "
            f"{result.indexed_chunk_count}/{result.chunk_count} chunk(s) indexed"
            + (
                f" via {result.model_identity}/{result.provider_identity}"
                if result.model_identity
                else ""
            )
        )
    return exit_code


async def _run_ask(app: DocuMindApplication, question: str) -> int:
    result = await app.ask(question)
    print(result.answer)
    if result.citations:
        print("\nSources:")
        for citation in result.citations:
            print(
                f"  [{citation.index}] {citation.document_id} (chunk {citation.chunk_index})"
            )
    print(
        f"\n(model: {result.provenance.model_identity} via "
        f"{result.provenance.provider_identity}; reranker: {result.provenance.reranker}; "
        f"candidates considered: {result.provenance.retrieval_candidate_count})"
    )
    return 0


def _run_status(config: DocuMindConfig) -> int:
    status = check_ollama_status(config)
    if not status.reachable:
        print(f"Ollama: UNREACHABLE -- {status.detail}")
        print(f"  Expected base URL: {config.base_url}")
        return 1
    print(f"Ollama: reachable ({status.detail})")
    print(
        f"  chat model {config.chat_model!r}: {'available' if status.chat_model_available else 'NOT PULLED'}"
    )
    print(
        "  embedding model "
        f"{config.embedding_model!r}: "
        f"{'available' if status.embedding_model_available else 'NOT PULLED'}"
    )
    if not status.chat_model_available or not status.embedding_model_available:
        print(
            f"\n  run: ollama pull {config.chat_model}; ollama pull {config.embedding_model}"
        )
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    config = DocuMindConfig.from_environment()

    if args.command == "status":
        return _run_status(config)

    try:
        runtime = DocuMindRuntime(config)
        app = DocuMindApplication(runtime)
        if args.command == "ingest":
            return asyncio.run(_run_ingest(app, args.paths))
        if args.command == "ask":
            return asyncio.run(_run_ask(app, args.question))
    except _EXPECTED_ERRORS as exc:
        if args.debug:
            raise
        print(f"error: {exc}", file=sys.stderr)
        return 1

    raise AssertionError(f"unreachable: unknown command {args.command!r}")


if __name__ == "__main__":
    raise SystemExit(main())
