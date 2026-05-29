"""Block tokenizer — maps intent → block-token IDs.

Unlike subword tokenizers (BPE, SentencePiece), CodeLM's tokenizer maps
each verified code block to a unique token ID. The vocabulary is the corpus
itself: each token is a compilable, validated function.

Special tokens:
  0: <PAD>
  1: <BOS> (begin of sequence)
  2: <EOS> (end of sequence)
  3: <UNK> (unknown block)
  4: <SEP> (separator between sections)
"""

import json
from pathlib import Path

from config import VOCAB_SIZE


SPECIAL_TOKENS = {
    "<PAD>": 0,
    "<BOS>": 1,
    "<EOS>": 2,
    "<UNK>": 3,
    "<SEP>": 4,
}

NUM_SPECIAL = len(SPECIAL_TOKENS)


class BlockTokenizer:
    """Maps block IDs ↔ token IDs."""

    def __init__(self):
        self.block_to_id: dict[str, int] = {}
        self.id_to_block: dict[int, str] = {}
        self.vocab_size = NUM_SPECIAL

        for token, idx in SPECIAL_TOKENS.items():
            self.block_to_id[token] = idx
            self.id_to_block[idx] = token

    def add_block(self, block_id: str) -> int:
        """Register a block and return its token ID."""
        if block_id in self.block_to_id:
            return self.block_to_id[block_id]

        if self.vocab_size >= VOCAB_SIZE:
            return SPECIAL_TOKENS["<UNK>"]

        token_id = self.vocab_size
        self.block_to_id[block_id] = token_id
        self.id_to_block[token_id] = block_id
        self.vocab_size += 1
        return token_id

    def encode(self, block_ids: list[str]) -> list[int]:
        """Encode a sequence of block IDs into token IDs."""
        tokens = [SPECIAL_TOKENS["<BOS>"]]
        for bid in block_ids:
            tokens.append(self.block_to_id.get(bid, SPECIAL_TOKENS["<UNK>"]))
        tokens.append(SPECIAL_TOKENS["<EOS>"])
        return tokens

    def decode(self, token_ids: list[int]) -> list[str]:
        """Decode token IDs back to block IDs."""
        blocks = []
        for tid in token_ids:
            if tid in (0, 1, 2):  # PAD, BOS, EOS
                continue
            blocks.append(self.id_to_block.get(tid, "<UNK>"))
        return blocks

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump({
                "block_to_id": self.block_to_id,
                "vocab_size": self.vocab_size,
            }, f)

    @classmethod
    def load(cls, path: Path) -> "BlockTokenizer":
        tokenizer = cls()
        with open(path) as f:
            data = json.load(f)
        tokenizer.block_to_id = data["block_to_id"]
        tokenizer.id_to_block = {int(v): k for k, v in data["block_to_id"].items()}
        tokenizer.vocab_size = data["vocab_size"]
        return tokenizer
