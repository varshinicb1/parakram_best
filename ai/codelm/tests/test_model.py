"""Tests for the CodeLM transformer model."""

import torch
import pytest


def test_model_forward_pass():
    """Model produces correct output shape."""
    from model.architecture import CodeLM

    model = CodeLM(vocab_size=1024, dim=128, n_heads=4, n_layers=2, max_seq_len=32)
    input_ids = torch.randint(0, 1024, (2, 16))
    logits = model(input_ids)

    assert logits.shape == (2, 16, 1024), f"Expected (2, 16, 1024), got {logits.shape}"


def test_model_parameter_count():
    """Model has reasonable parameter count for 6GB VRAM."""
    from model.architecture import CodeLM

    model = CodeLM()
    params = model.count_parameters()
    assert params < 200_000_000, f"Model too large for 6GB VRAM: {params:,} params"
    assert params > 1_000_000, f"Model suspiciously small: {params:,} params"


def test_tokenizer_roundtrip():
    """Tokenizer encode/decode is lossless."""
    from model.tokenizer import BlockTokenizer

    tok = BlockTokenizer()
    tok.add_block("block_gpio_init")
    tok.add_block("block_spi_transfer")
    tok.add_block("block_i2c_read")

    block_ids = ["block_gpio_init", "block_spi_transfer", "block_i2c_read"]
    encoded = tok.encode(block_ids)
    decoded = tok.decode(encoded)

    assert decoded == block_ids, f"Roundtrip failed: {block_ids} → {encoded} → {decoded}"


def test_constraint_head():
    """Constraint head outputs 4 values in [0, 1]."""
    from model.heads import ConstraintHead

    head = ConstraintHead(dim=128)
    hidden = torch.randn(2, 16, 128)
    scores = head(hidden)

    assert scores.shape == (2, 4)
    assert (scores >= 0).all() and (scores <= 1).all(), "Constraint scores must be in [0, 1]"


def test_composition_head():
    """Composition head scores candidates correctly."""
    from model.heads import CompositionHead

    head = CompositionHead(dim=128)
    context = torch.randn(2, 128)
    candidates = torch.randn(2, 10, 128)
    scores = head(context, candidates)

    assert scores.shape == (2, 10), f"Expected (2, 10), got {scores.shape}"
