"""
RAG Engine — Retrieval-Augmented Generation for firmware code.

Uses Ollama's nomic-embed-text model to embed all 43 hardware library
firmware templates. At generation time, retrieves the K most relevant
templates as in-context examples for the code LLM.

Vector store is in-memory (numpy) — no external database required.
"""

import os
import json
import math
import hashlib
import asyncio
from typing import Optional

import aiohttp


OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL = "nomic-embed-text"
HARDWARE_LIB_DIR = os.path.join(os.path.dirname(__file__), "..", "hardware_library")
CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", ".cache")
CACHE_FILE = os.path.join(CACHE_DIR, "rag_embeddings.json")


class RAGEngine:
    """Firmware template retrieval engine using Ollama embeddings."""

    def __init__(self):
        self._documents: list[dict] = []    # [{id, text, metadata, embedding}]
        self._initialized = False

    async def initialize(self):
        """Load and embed all hardware library templates on startup."""
        if self._initialized:
            return

        print("[RAG] Initializing firmware knowledge base...")
        templates = self._load_templates()
        print(f"[RAG] Found {len(templates)} firmware templates")

        # Try loading from cache first
        lib_hash = self._compute_library_hash()
        cached = self._load_cache(lib_hash)

        if cached:
            self._documents = cached
            valid = sum(1 for d in self._documents if d.get("embedding"))
            print(f"[RAG] Loaded {valid} embeddings from cache (instant)")
        else:
            # Embed all templates
            texts = [t["text"] for t in templates]
            embeddings = await self._embed_batch(texts)

            for i, tmpl in enumerate(templates):
                tmpl["embedding"] = embeddings[i] if i < len(embeddings) else []
                self._documents.append(tmpl)

            valid = sum(1 for d in self._documents if d.get("embedding"))
            print(f"[RAG] Embedded {valid}/{len(templates)} templates, saving cache...")
            self._save_cache(lib_hash)

        self._initialized = True

    def _compute_library_hash(self) -> str:
        """Hash all hardware library JSONs to detect changes."""
        hasher = hashlib.md5()
        for cat in sorted(os.listdir(HARDWARE_LIB_DIR)):
            cat_path = os.path.join(HARDWARE_LIB_DIR, cat)
            if not os.path.isdir(cat_path):
                continue
            for fname in sorted(os.listdir(cat_path)):
                if fname.endswith(".json"):
                    fpath = os.path.join(cat_path, fname)
                    hasher.update(fname.encode())
                    hasher.update(str(os.path.getmtime(fpath)).encode())
        return hasher.hexdigest()

    def _load_cache(self, lib_hash: str) -> list[dict]:
        """Load cached embeddings if hash matches."""
        try:
            if not os.path.exists(CACHE_FILE):
                return []
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
            if cache.get("hash") != lib_hash:
                print("[RAG] Cache invalidated (library files changed)")
                return []
            return cache.get("documents", [])
        except Exception as e:
            print(f"[RAG] Cache load error: {e}")
            return []

    def _save_cache(self, lib_hash: str):
        """Save embeddings to disk cache."""
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            cache = {
                "hash": lib_hash,
                "model": EMBED_MODEL,
                "documents": self._documents,
            }
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache, f)
            print(f"[RAG] Cache saved ({os.path.getsize(CACHE_FILE) // 1024}KB)")
        except Exception as e:
            print(f"[RAG] Cache save error: {e}")

    def _load_templates(self) -> list[dict]:
        """Load all hardware library JSONs and extract firmware templates."""
        templates = []
        categories = [
            "sensors", "communication", "actuators", "audio",
            "display", "security", "freertos", "control_blocks",
        ]

        for category in categories:
            cat_dir = os.path.join(HARDWARE_LIB_DIR, category)
            if not os.path.isdir(cat_dir):
                continue

            for fname in os.listdir(cat_dir):
                if not fname.endswith(".json"):
                    continue

                fpath = os.path.join(cat_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        block = json.load(f)

                    # Build a rich text representation for embedding
                    block_id = block.get("id", fname.replace(".json", ""))
                    name = block.get("name", block_id)
                    desc = block.get("description", "")
                    cat = block.get("category", category)
                    inputs = block.get("inputs", [])
                    outputs = block.get("outputs", [])
                    config = block.get("configuration", [])
                    libs = block.get("libraries", [])
                    fw_template = block.get("firmware_template", {})

                    # Build embedding text: name + description + IO + code
                    io_text = ""
                    if inputs:
                        io_text += " Inputs: " + ", ".join(
                            f"{p.get('name', '')}({p.get('data_type', '')})" for p in inputs
                        )
                    if outputs:
                        io_text += " Outputs: " + ", ".join(
                            f"{p.get('name', '')}({p.get('data_type', '')})" for p in outputs
                        )

                    config_text = ""
                    if config:
                        config_text = " Config: " + ", ".join(
                            f"{c.get('key', '')}={c.get('default', '')}" for c in config
                        )

                    embed_text = (
                        f"{name}: {desc}{io_text}{config_text}. "
                        f"Category: {cat}. Libraries: {', '.join(libs)}."
                    )

                    templates.append({
                        "id": block_id,
                        "text": embed_text,
                        "metadata": {
                            "name": name,
                            "category": cat,
                            "description": desc,
                            "libraries": libs,
                            "inputs": inputs,
                            "outputs": outputs,
                            "configuration": config,
                        },
                        "firmware_template": fw_template,
                        "embedding": [],
                    })

                except Exception as e:
                    print(f"[RAG] Error loading {fpath}: {e}")

        return templates

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts using Ollama nomic-embed-text."""
        embeddings = []
        async with aiohttp.ClientSession() as session:
            for text in texts:
                try:
                    async with session.post(
                        f"{OLLAMA_BASE_URL}/api/embed",
                        json={"model": EMBED_MODEL, "input": text},
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            # Ollama /api/embed returns {"embeddings": [[...]]}
                            embs = data.get("embeddings", [])
                            embeddings.append(embs[0] if embs else [])
                        else:
                            print(f"[RAG] Embed failed: HTTP {resp.status}")
                            embeddings.append([])
                except Exception as e:
                    print(f"[RAG] Embed error: {e}")
                    embeddings.append([])
        return embeddings

    async def _embed_single(self, text: str) -> list[float]:
        """Embed a single text."""
        results = await self._embed_batch([text])
        return results[0] if results else []

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    async def retrieve(self, query: str, top_k: int = 3) -> list[dict]:
        """
        Retrieve the top-K most relevant firmware templates for a query.

        Args:
            query: Description of the block or task
            top_k: Number of results to return

        Returns:
            List of {id, name, similarity, firmware_template, metadata}
        """
        if not self._initialized:
            await self.initialize()

        query_embedding = await self._embed_single(query)
        if not query_embedding:
            return []

        # Score all documents
        scored = []
        for doc in self._documents:
            if not doc.get("embedding"):
                continue
            sim = self._cosine_similarity(query_embedding, doc["embedding"])
            scored.append((sim, doc))

        # Sort by similarity descending
        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        for sim, doc in scored[:top_k]:
            results.append({
                "id": doc["id"],
                "name": doc["metadata"]["name"],
                "category": doc["metadata"]["category"],
                "similarity": round(sim, 4),
                "firmware_template": doc.get("firmware_template", {}),
                "metadata": doc["metadata"],
            })

        return results

    def get_template_by_id(self, block_id: str) -> Optional[dict]:
        """Get a specific firmware template by block ID (exact match)."""
        for doc in self._documents:
            if doc["id"] == block_id:
                return doc.get("firmware_template", {})
        return None

    @property
    def document_count(self) -> int:
        return len(self._documents)

    @property
    def is_initialized(self) -> bool:
        return self._initialized


# Singleton instance
_rag_instance: Optional[RAGEngine] = None


def get_rag_engine() -> RAGEngine:
    """Get or create the singleton RAG engine."""
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RAGEngine()
    return _rag_instance
