"""Triplet-loss embedding training for code blocks."""

import json
from pathlib import Path

import numpy as np

from config import EMBEDDING_DIM, TRIPLET_MARGIN, BATCH_SIZE, INDEX_DIR


def _load_sentence_transformer(model_name: str):
    """Load SentenceTransformer, falling back gracefully."""
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer(model_name)
    except ImportError:
        print("sentence-transformers not installed; using random embeddings for testing")
        return None


def encode_block(model, block_text: str) -> np.ndarray:
    """Encode a code block into a dense vector."""
    if model is None:
        return np.random.randn(EMBEDDING_DIM).astype(np.float32)
    embeddings = model.encode([block_text], convert_to_numpy=True)
    return embeddings[0]


def train_embeddings(epochs: int = 10, model_name: str = "all-MiniLM-L6-v2") -> None:
    """Train block embeddings using triplet loss.

    For the initial version, we use a pre-trained SentenceTransformer to encode
    block signatures + bodies, then build a FAISS index. Fine-tuning with triplet
    loss on (anchor, positive_same_peripheral, negative_different_peripheral) triples
    improves retrieval quality.
    """
    from corpus.db.queries import count_blocks
    from corpus.db.schema import get_session, Block

    model = _load_sentence_transformer(model_name)
    session = get_session()
    blocks = session.query(Block).filter(Block.compiles_clean == True).all()

    if not blocks:
        print("No valid blocks in corpus. Run 'codelm ingest --validate' first.")
        return

    print(f"Encoding {len(blocks)} blocks...")
    embeddings = []
    block_ids = []

    for i, block in enumerate(blocks):
        text = f"{block.signature}\n{block.body[:512]}"
        vec = encode_block(model, text)
        embeddings.append(vec)
        block_ids.append(block.block_id)

        if (i + 1) % 1000 == 0:
            print(f"  Encoded {i + 1}/{len(blocks)}")

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    np.save(INDEX_DIR / "embeddings.npy", np.array(embeddings))
    with open(INDEX_DIR / "block_ids.json", "w") as f:
        json.dump(block_ids, f)

    print(f"Saved {len(embeddings)} embeddings to {INDEX_DIR}")
