"""The CodeLM transformer — block-token sequence model.

Architecture:
  - Input: sequence of block-token IDs (each = a verified C function)
  - Output: next block-token prediction + constraint satisfaction scores
  - Designed to fit in 6GB VRAM with LoRA fine-tuning

The model does NOT generate source code character-by-character.
It composes verified blocks into complete firmware programs.
"""

import math

import torch
import torch.nn as nn
import torch.nn.functional as F

from config import VOCAB_SIZE, BLOCK_DIM, N_HEADS, N_LAYERS, MAX_SEQ_LEN, DROPOUT


class RotaryPositionalEmbedding(nn.Module):
    """RoPE — better than learned positional embeddings for sequence models."""

    def __init__(self, dim: int, max_len: int = MAX_SEQ_LEN):
        super().__init__()
        inv_freq = 1.0 / (10000 ** (torch.arange(0, dim, 2).float() / dim))
        self.register_buffer("inv_freq", inv_freq)
        self.max_len = max_len

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        seq_len = x.shape[1]
        t = torch.arange(seq_len, device=x.device, dtype=self.inv_freq.dtype)
        freqs = torch.outer(t, self.inv_freq)
        return freqs.cos(), freqs.sin()


def apply_rotary(x: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor) -> torch.Tensor:
    d = x.shape[-1] // 2
    x1, x2 = x[..., :d], x[..., d:]
    return torch.cat([x1 * cos - x2 * sin, x2 * cos + x1 * sin], dim=-1)


class MultiHeadAttention(nn.Module):
    def __init__(self, dim: int, n_heads: int, dropout: float = DROPOUT):
        super().__init__()
        self.n_heads = n_heads
        self.head_dim = dim // n_heads

        self.q_proj = nn.Linear(dim, dim, bias=False)
        self.k_proj = nn.Linear(dim, dim, bias=False)
        self.v_proj = nn.Linear(dim, dim, bias=False)
        self.o_proj = nn.Linear(dim, dim, bias=False)
        self.dropout = nn.Dropout(dropout)

    def forward(
        self,
        x: torch.Tensor,
        cos: torch.Tensor,
        sin: torch.Tensor,
        mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        B, T, D = x.shape

        q = self.q_proj(x).view(B, T, self.n_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(B, T, self.n_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(B, T, self.n_heads, self.head_dim).transpose(1, 2)

        q = apply_rotary(q, cos.unsqueeze(0).unsqueeze(0), sin.unsqueeze(0).unsqueeze(0))
        k = apply_rotary(k, cos.unsqueeze(0).unsqueeze(0), sin.unsqueeze(0).unsqueeze(0))

        scale = math.sqrt(self.head_dim)
        attn = (q @ k.transpose(-2, -1)) / scale

        if mask is not None:
            attn = attn.masked_fill(mask == 0, float("-inf"))

        attn = F.softmax(attn, dim=-1)
        attn = self.dropout(attn)

        out = (attn @ v).transpose(1, 2).contiguous().view(B, T, D)
        return self.o_proj(out)


class FeedForward(nn.Module):
    """SwiGLU feed-forward network."""
    def __init__(self, dim: int, dropout: float = DROPOUT):
        super().__init__()
        hidden = int(dim * 8 / 3)  # SwiGLU uses 8/3 ratio
        self.gate = nn.Linear(dim, hidden, bias=False)
        self.up = nn.Linear(dim, hidden, bias=False)
        self.down = nn.Linear(hidden, dim, bias=False)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.dropout(self.down(F.silu(self.gate(x)) * self.up(x)))


class TransformerBlock(nn.Module):
    def __init__(self, dim: int, n_heads: int, dropout: float = DROPOUT):
        super().__init__()
        self.attn_norm = nn.RMSNorm(dim)
        self.attn = MultiHeadAttention(dim, n_heads, dropout)
        self.ff_norm = nn.RMSNorm(dim)
        self.ff = FeedForward(dim, dropout)

    def forward(
        self, x: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor, mask: torch.Tensor | None = None
    ) -> torch.Tensor:
        x = x + self.attn(self.attn_norm(x), cos, sin, mask)
        x = x + self.ff(self.ff_norm(x))
        return x


class CodeLM(nn.Module):
    """Block-token transformer for firmware synthesis.

    Input: sequence of block-token IDs
    Output: logits over block vocabulary + constraint scores
    """

    def __init__(
        self,
        vocab_size: int = VOCAB_SIZE,
        dim: int = BLOCK_DIM,
        n_heads: int = N_HEADS,
        n_layers: int = N_LAYERS,
        max_seq_len: int = MAX_SEQ_LEN,
        dropout: float = DROPOUT,
    ):
        super().__init__()
        self.dim = dim
        self.max_seq_len = max_seq_len

        self.token_embed = nn.Embedding(vocab_size, dim)
        self.rope = RotaryPositionalEmbedding(dim // n_heads, max_seq_len)
        self.dropout = nn.Dropout(dropout)

        self.layers = nn.ModuleList([
            TransformerBlock(dim, n_heads, dropout) for _ in range(n_layers)
        ])

        self.norm = nn.RMSNorm(dim)
        self.lm_head = nn.Linear(dim, vocab_size, bias=False)

        # Weight tying
        self.lm_head.weight = self.token_embed.weight

        self.apply(self._init_weights)

    def _init_weights(self, module: nn.Module) -> None:
        if isinstance(module, nn.Linear):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        B, T = input_ids.shape
        x = self.dropout(self.token_embed(input_ids))

        cos, sin = self.rope(x)

        if attention_mask is None:
            mask = torch.tril(torch.ones(T, T, device=input_ids.device)).unsqueeze(0).unsqueeze(0)
        else:
            mask = attention_mask.unsqueeze(1).unsqueeze(2) * \
                   torch.tril(torch.ones(T, T, device=input_ids.device)).unsqueeze(0).unsqueeze(0)

        for layer in self.layers:
            x = layer(x, cos, sin, mask)

        x = self.norm(x)
        logits = self.lm_head(x)
        return logits

    def count_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters())

    def count_trainable_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
