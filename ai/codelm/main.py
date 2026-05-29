"""CodeLM CLI — block-token firmware synthesis model."""

import argparse
import sys
from pathlib import Path


def cmd_ingest(args: argparse.Namespace) -> None:
    """Download and ingest upstream sources into the corpus."""
    from corpus.ingest.downloader import download_all_sources
    from corpus.ingest.extractor import extract_all_blocks
    from corpus.ingest.validator import validate_corpus

    print("=== Phase 1: Download sources ===")
    download_all_sources(args.sources_file)

    print("=== Phase 2: Extract blocks ===")
    stats = extract_all_blocks()
    print(f"Extracted {stats['total_blocks']} blocks from {stats['total_files']} files")

    if args.validate:
        print("=== Phase 3: Validate blocks ===")
        results = validate_corpus()
        print(f"Valid: {results['valid']}, Invalid: {results['invalid']}")


def cmd_embed(args: argparse.Namespace) -> None:
    """Build or update the embedding index."""
    from embedding.trainer import train_embeddings
    from embedding.index import build_faiss_index

    print("=== Training embeddings ===")
    train_embeddings(epochs=args.epochs)

    print("=== Building FAISS index ===")
    build_faiss_index()


def cmd_train(args: argparse.Namespace) -> None:
    """Train the block-token transformer."""
    from model.train import train_codelm

    print("=== Training CodeLM ===")
    train_codelm(
        epochs=args.epochs,
        batch_size=args.batch_size,
        resume_from=args.resume,
    )


def cmd_generate(args: argparse.Namespace) -> None:
    """Generate firmware from a natural-language intent."""
    from model.inference import generate_firmware

    result = generate_firmware(
        intent=args.intent,
        target_mcu=args.mcu,
        checkpoint=args.checkpoint,
    )
    print(result.source_code)


def cmd_serve(args: argparse.Namespace) -> None:
    """Start the CodeLM bridge API server."""
    from parakram.codelm_bridge import start_bridge_server

    start_bridge_server(port=args.port)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="codelm",
        description="CodeLM — Block-Token Firmware Synthesis Model",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ingest
    p_ingest = subparsers.add_parser("ingest", help="Ingest upstream sources")
    p_ingest.add_argument("--sources-file", type=Path, default=Path("sources.md"))
    p_ingest.add_argument("--validate", action="store_true")
    p_ingest.set_defaults(func=cmd_ingest)

    # embed
    p_embed = subparsers.add_parser("embed", help="Build embedding index")
    p_embed.add_argument("--epochs", type=int, default=10)
    p_embed.set_defaults(func=cmd_embed)

    # train
    p_train = subparsers.add_parser("train", help="Train the model")
    p_train.add_argument("--epochs", type=int, default=20)
    p_train.add_argument("--batch-size", type=int, default=64)
    p_train.add_argument("--resume", type=Path, default=None)
    p_train.set_defaults(func=cmd_train)

    # generate
    p_gen = subparsers.add_parser("generate", help="Generate firmware from intent")
    p_gen.add_argument("intent", type=str)
    p_gen.add_argument("--mcu", type=str, default="esp32s3")
    p_gen.add_argument("--checkpoint", type=Path, default=None)
    p_gen.set_defaults(func=cmd_generate)

    # serve
    p_serve = subparsers.add_parser("serve", help="Start bridge API server")
    p_serve.add_argument("--port", type=int, default=8401)
    p_serve.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
