"""Training loop — LoRA on RTX 4050 (6GB VRAM)."""

import time
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

from config import (
    LEARNING_RATE, WEIGHT_DECAY, WARMUP_STEPS, MAX_EPOCHS,
    LORA_RANK, LORA_ALPHA, GRADIENT_ACCUMULATION_STEPS,
    BATCH_SIZE, MAX_SEQ_LEN, MODEL_DIR,
)
from model.architecture import CodeLM
from model.heads import ConstraintHead


class BlockSequenceDataset(Dataset):
    """Dataset of block-token sequences for training."""

    def __init__(self, sequences: list[list[int]], max_len: int = MAX_SEQ_LEN):
        self.sequences = sequences
        self.max_len = max_len

    def __len__(self) -> int:
        return len(self.sequences)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        seq = self.sequences[idx][:self.max_len]
        # Pad
        padded = seq + [0] * (self.max_len - len(seq))
        input_ids = torch.tensor(padded[:-1], dtype=torch.long)
        labels = torch.tensor(padded[1:], dtype=torch.long)
        mask = torch.tensor([1] * (len(seq) - 1) + [0] * (self.max_len - len(seq)), dtype=torch.long)
        return {"input_ids": input_ids, "labels": labels, "attention_mask": mask}


def apply_lora(model: CodeLM, rank: int = LORA_RANK, alpha: int = LORA_ALPHA) -> CodeLM:
    """Apply LoRA to attention projection layers for memory-efficient fine-tuning."""
    try:
        from peft import get_peft_model, LoraConfig, TaskType
        config = LoraConfig(
            r=rank,
            lora_alpha=alpha,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
            lora_dropout=0.05,
            bias="none",
            task_type=TaskType.CAUSAL_LM,
        )
        return get_peft_model(model, config)
    except ImportError:
        print("peft not installed — training full model (requires more VRAM)")
        return model


def train_codelm(
    epochs: int = MAX_EPOCHS,
    batch_size: int = BATCH_SIZE,
    resume_from: Path | None = None,
) -> None:
    """Main training loop."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    model = CodeLM()
    if resume_from and resume_from.exists():
        model.load_state_dict(torch.load(resume_from, map_location=device))
        print(f"Resumed from {resume_from}")

    model = apply_lora(model)
    model = model.to(device)

    trainable = model.count_trainable_parameters() if hasattr(model, 'count_trainable_parameters') else sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    print(f"Parameters: {total:,} total, {trainable:,} trainable ({100 * trainable / total:.1f}%)")

    # Placeholder dataset — real training uses corpus sequences
    dummy_sequences = [[1, 5, 10, 15, 20, 25, 30, 2]] * 100
    dataset = BlockSequenceDataset(dummy_sequences)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY,
    )

    criterion = nn.CrossEntropyLoss(ignore_index=0)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    for epoch in range(epochs):
        model.train()
        total_loss = 0.0
        n_batches = 0
        t0 = time.time()

        for step, batch in enumerate(loader):
            input_ids = batch["input_ids"].to(device)
            labels = batch["labels"].to(device)

            logits = model(input_ids)
            loss = criterion(logits.view(-1, logits.size(-1)), labels.view(-1))
            loss = loss / GRADIENT_ACCUMULATION_STEPS
            loss.backward()

            if (step + 1) % GRADIENT_ACCUMULATION_STEPS == 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                optimizer.zero_grad()

            total_loss += loss.item() * GRADIENT_ACCUMULATION_STEPS
            n_batches += 1

        avg_loss = total_loss / max(n_batches, 1)
        elapsed = time.time() - t0
        print(f"Epoch {epoch + 1}/{epochs} — loss: {avg_loss:.4f} — {elapsed:.1f}s")

        # Save checkpoint
        ckpt_path = MODEL_DIR / f"codelm_epoch_{epoch + 1}.pt"
        torch.save(model.state_dict(), ckpt_path)

    print(f"Training complete. Checkpoints saved to {MODEL_DIR}")
