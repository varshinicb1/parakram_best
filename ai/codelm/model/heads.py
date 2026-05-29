"""Constraint head + Composition head for CodeLM.

The constraint head predicts whether a candidate block sequence satisfies
hardware constraints (stack budget, peripheral conflicts, timing deadlines).

The composition head predicts the most probable next block given the current
sequence and the target MCU context.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

from config import BLOCK_DIM


class ConstraintHead(nn.Module):
    """Predicts constraint satisfaction scores for a block sequence.

    Outputs 4 binary predictions:
      - stack_ok: total stack usage <= target MCU SRAM
      - no_conflicts: no peripheral bus conflicts (e.g., two SPI masters)
      - timing_ok: all blocks meet real-time deadline
      - deps_ok: all include dependencies are satisfied
    """

    def __init__(self, dim: int = BLOCK_DIM):
        super().__init__()
        self.proj = nn.Sequential(
            nn.Linear(dim, dim // 2),
            nn.GELU(),
            nn.Linear(dim // 2, 4),
        )

    def forward(self, hidden_states: torch.Tensor) -> torch.Tensor:
        """Takes the [CLS] or mean-pooled hidden state, returns 4 constraint scores."""
        pooled = hidden_states.mean(dim=1)  # (B, D)
        return torch.sigmoid(self.proj(pooled))  # (B, 4)


class CompositionHead(nn.Module):
    """Re-ranks candidate blocks based on composition compatibility.

    Given the current sequence context and a set of candidate block embeddings,
    scores each candidate on how well it fits the existing sequence.
    """

    def __init__(self, dim: int = BLOCK_DIM):
        super().__init__()
        self.context_proj = nn.Linear(dim, dim)
        self.candidate_proj = nn.Linear(dim, dim)
        self.score = nn.Linear(dim, 1)

    def forward(
        self,
        context: torch.Tensor,       # (B, D) — mean-pooled sequence
        candidates: torch.Tensor,     # (B, K, D) — K candidate block embeddings
    ) -> torch.Tensor:
        """Returns compatibility scores (B, K)."""
        ctx = self.context_proj(context).unsqueeze(1)  # (B, 1, D)
        cand = self.candidate_proj(candidates)          # (B, K, D)
        combined = F.gelu(ctx + cand)                   # (B, K, D)
        scores = self.score(combined).squeeze(-1)       # (B, K)
        return scores
