"""FAISS index build + query for code block retrieval."""

import json
from pathlib import Path

import numpy as np

from config import EMBEDDING_DIM, INDEX_DIR


def build_faiss_index() -> None:
    """Build a FAISS index from pre-computed embeddings."""
    embeddings_path = INDEX_DIR / "embeddings.npy"
    if not embeddings_path.exists():
        print("No embeddings found. Run 'codelm embed' first.")
        return

    embeddings = np.load(embeddings_path).astype(np.float32)
    n, d = embeddings.shape
    print(f"Building FAISS index: {n} vectors, dim={d}")

    try:
        import faiss
        index = faiss.IndexFlatIP(d)  # inner product (cosine after normalization)
        faiss.normalize_L2(embeddings)
        index.add(embeddings)
        faiss.write_index(index, str(INDEX_DIR / "blocks.index"))
        print(f"FAISS index saved: {n} vectors")
    except ImportError:
        # Fallback: brute-force numpy search
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized = embeddings / (norms + 1e-8)
        np.save(INDEX_DIR / "normalized_embeddings.npy", normalized)
        print(f"Numpy fallback index saved: {n} vectors (install faiss for GPU acceleration)")


def query_similar(query_embedding: np.ndarray, top_k: int = 10) -> list[tuple[str, float]]:
    """Find the top-k most similar blocks to a query embedding."""
    block_ids_path = INDEX_DIR / "block_ids.json"
    if not block_ids_path.exists():
        return []

    with open(block_ids_path) as f:
        block_ids = json.load(f)

    try:
        import faiss
        index_path = INDEX_DIR / "blocks.index"
        if index_path.exists():
            index = faiss.read_index(str(index_path))
            query = query_embedding.reshape(1, -1).astype(np.float32)
            faiss.normalize_L2(query)
            distances, indices = index.search(query, top_k)
            return [(block_ids[i], float(d)) for i, d in zip(indices[0], distances[0]) if i < len(block_ids)]
    except ImportError:
        pass

    # Numpy fallback
    norm_path = INDEX_DIR / "normalized_embeddings.npy"
    if norm_path.exists():
        normalized = np.load(norm_path)
        query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)
        scores = normalized @ query_norm
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [(block_ids[i], float(scores[i])) for i in top_indices]

    return []
