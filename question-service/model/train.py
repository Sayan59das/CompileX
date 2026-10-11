"""
Training script for the CodingQuestion Transformer.

Improvements over v1:
  - Larger model: d_model=512, 6 encoder + 6 decoder layers, ff=2048
  - Longer target sequences (max_tgt_len=768) to capture full questions
  - Better tokenizer: subword-aware (keeps numbers, punctuation as tokens)
  - Curriculum: easy questions first, then medium, then hard
  - Gradient accumulation for effective larger batch size
  - Cosine LR with warmup
  - Label smoothing 0.1
  - Early stopping patience=8

Usage (from backend root):
    python model/train.py --data data/questions.json --epochs 100 --batch_size 32 --save_dir model/saved_model
"""

import argparse
import os
import sys
import json
import math
import time
import warnings
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split

warnings.filterwarnings("ignore", message="Support for mismatched key_padding_mask")

sys.path.insert(0, os.path.dirname(__file__))
from tokenizer import SimpleTokenizer
from dataset import CodingQuestionDataset, collate_fn
from transformer_model import CodingQuestionTransformer

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

torch.backends.cudnn.benchmark = True


# ── LR Scheduler ─────────────────────────────────────────────────────────────

class WarmupCosineScheduler:
    def __init__(self, optimizer, warmup_steps, total_steps, base_lr, min_lr=1e-6):
        self.optimizer = optimizer
        self.warmup_steps = warmup_steps
        self.total_steps = total_steps
        self.base_lr = base_lr
        self.min_lr = min_lr
        self.current_step = 0

    def step(self):
        self.current_step += 1
        lr = self._get_lr()
        for pg in self.optimizer.param_groups:
            pg["lr"] = lr

    def _get_lr(self):
        s = self.current_step
        if s < self.warmup_steps:
            return self.base_lr * s / max(1, self.warmup_steps)
        progress = (s - self.warmup_steps) / max(1, self.total_steps - self.warmup_steps)
        cosine = 0.5 * (1.0 + math.cos(math.pi * progress))
        return self.min_lr + (self.base_lr - self.min_lr) * cosine

    def get_last_lr(self):
        return [self._get_lr()]


# ── Data loading ──────────────────────────────────────────────────────────────

def load_raw_texts(data_path):
    with open(data_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    texts = []
    for item in raw:
        for field in ["topic", "difficulty", "title", "problem_statement",
                      "input_format", "output_format", "sample_input", "sample_output"]:
            v = item.get(field, "")
            if v:
                texts.append(str(v))
        for tc in item.get("test_cases", []):
            texts.append(str(tc.get("input", "")))
            texts.append(str(tc.get("output", "")))
    return texts


def filter_quality(data_path):
    """Return only quality questions (>=3 test cases, full fields)."""
    with open(data_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    good = []
    for item in raw:
        if (
            len(item.get("test_cases", [])) >= 3
            and len(item.get("problem_statement", "").strip()) > 30
            and item.get("title", "").strip()
            and item.get("input_format", "").strip()
            and item.get("output_format", "").strip()
        ):
            good.append(item)
    print(f"[Train] Quality filter: {len(good)}/{len(raw)} questions kept")
    return good


# ── Training loop ─────────────────────────────────────────────────────────────

def train_epoch(model, loader, optimizer, criterion, scheduler, device,
                scaler=None, grad_accum=1):
    model.train()
    total_loss = 0
    optimizer.zero_grad()

    iterator = tqdm(loader, desc="  Train", leave=False) if TQDM_AVAILABLE else loader

    for step, batch in enumerate(iterator):
        src = batch["src"].to(device)
        tgt = batch["tgt"].to(device)
        src_mask = batch["src_key_padding_mask"].to(device)
        tgt_mask = batch["tgt_key_padding_mask"].to(device)

        tgt_input = tgt[:, :-1]
        tgt_label = tgt[:, 1:]
        tgt_input_mask = tgt_mask[:, :-1]

        if scaler is not None:
            with torch.amp.autocast("cuda"):
                logits = model(src, tgt_input,
                               src_key_padding_mask=src_mask,
                               tgt_key_padding_mask=tgt_input_mask)
                loss = criterion(logits.reshape(-1, logits.size(-1)),
                                 tgt_label.reshape(-1)) / grad_accum
            scaler.scale(loss).backward()
            if (step + 1) % grad_accum == 0:
                scaler.unscale_(optimizer)
                nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad()
                scheduler.step()
        else:
            logits = model(src, tgt_input,
                           src_key_padding_mask=src_mask,
                           tgt_key_padding_mask=tgt_input_mask)
            loss = criterion(logits.reshape(-1, logits.size(-1)),
                             tgt_label.reshape(-1)) / grad_accum
            loss.backward()
            if (step + 1) % grad_accum == 0:
                nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                optimizer.zero_grad()
                scheduler.step()

        total_loss += loss.item() * grad_accum
        if TQDM_AVAILABLE:
            iterator.set_postfix(loss=f"{loss.item()*grad_accum:.4f}")

    return total_loss / len(loader)


@torch.no_grad()
def eval_epoch(model, loader, criterion, device):
    model.eval()
    total_loss = 0
    iterator = tqdm(loader, desc="  Val  ", leave=False) if TQDM_AVAILABLE else loader
    for batch in iterator:
        src = batch["src"].to(device)
        tgt = batch["tgt"].to(device)
        src_mask = batch["src_key_padding_mask"].to(device)
        tgt_mask = batch["tgt_key_padding_mask"].to(device)
        tgt_input = tgt[:, :-1]
        tgt_label = tgt[:, 1:]
        tgt_input_mask = tgt_mask[:, :-1]
        logits = model(src, tgt_input,
                       src_key_padding_mask=src_mask,
                       tgt_key_padding_mask=tgt_input_mask)
        loss = criterion(logits.reshape(-1, logits.size(-1)), tgt_label.reshape(-1))
        total_loss += loss.item()
    return total_loss / len(loader)


def sample_output(model, tokenizer, device, topic="arrays", difficulty="medium"):
    """Generate a sample question to show training progress."""
    model.eval()
    prompt = f"{topic} {difficulty}"
    src_ids = tokenizer.encode(prompt)
    src = torch.tensor([src_ids], dtype=torch.long, device=device)
    with torch.no_grad():
        text = model.generate(src, tokenizer, max_new_tokens=200, temperature=0.8)
    print(f"\n  [Sample] prompt='{prompt}'")
    print(f"  {text[:300]}...")
    model.train()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data",        type=str,   default="data/questions.json")
    parser.add_argument("--epochs",      type=int,   default=100)
    parser.add_argument("--batch_size",  type=int,   default=32)
    parser.add_argument("--grad_accum",  type=int,   default=2,
                        help="Gradient accumulation steps (effective batch = batch_size * grad_accum)")
    parser.add_argument("--lr",          type=float, default=1e-4)
    parser.add_argument("--min_lr",      type=float, default=1e-6)
    parser.add_argument("--warmup_epochs", type=int, default=5)
    # Bigger model defaults
    parser.add_argument("--d_model",     type=int,   default=512)
    parser.add_argument("--nhead",       type=int,   default=8)
    parser.add_argument("--enc_layers",  type=int,   default=6)
    parser.add_argument("--dec_layers",  type=int,   default=6)
    parser.add_argument("--ff_dim",      type=int,   default=2048)
    parser.add_argument("--dropout",     type=float, default=0.2)
    parser.add_argument("--label_smoothing", type=float, default=0.1)
    parser.add_argument("--weight_decay", type=float, default=1e-4)
    parser.add_argument("--val_split",   type=float, default=0.1)
    parser.add_argument("--patience",    type=int,   default=8)
    parser.add_argument("--save_dir",    type=str,   default="model/saved_model")
    parser.add_argument("--min_freq",    type=int,   default=1)
    parser.add_argument("--max_tgt_len", type=int,   default=768)
    parser.add_argument("--max_src_len", type=int,   default=32)
    parser.add_argument("--sample_every", type=int,  default=10,
                        help="Print a sample generation every N epochs (0=off)")
    parser.add_argument("--resume",      type=str,   default=None,
                        help="Path to checkpoint to resume from")
    parser.add_argument("--tokenizer",   type=str,   default=None,
                        help="Path to pre-built tokenizer.json (skips vocab building)")
    parser.add_argument("--device",      type=str,
                        default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    device = torch.device(args.device)
    eff_batch = args.batch_size * args.grad_accum
    print(f"[Train] Device         : {device}")
    print(f"[Train] Batch size     : {args.batch_size} × {args.grad_accum} accum = {eff_batch} effective")
    print(f"[Train] Model          : d={args.d_model}, heads={args.nhead}, enc={args.enc_layers}, dec={args.dec_layers}, ff={args.ff_dim}")
    print(f"[Train] Max tgt len    : {args.max_tgt_len}")

    use_amp = device.type == "cuda"
    scaler  = torch.amp.GradScaler("cuda") if use_amp else None

    # ── Tokenizer ─────────────────────────────────────────────────────────
    tokenizer = SimpleTokenizer()
    if args.tokenizer and os.path.exists(args.tokenizer):
        print(f"[Train] Loading pre-built tokenizer from {args.tokenizer}")
        tokenizer.load(args.tokenizer)
    else:
        print("[Train] Building vocabulary from data...")
        texts = load_raw_texts(args.data)
        tokenizer.build_vocab(texts, min_freq=args.min_freq)
    print(f"[Train] Vocab size     : {tokenizer.vocab_size:,}")

    # ── Dataset ───────────────────────────────────────────────────────────
    dataset    = CodingQuestionDataset(args.data, tokenizer,
                                       max_src_len=args.max_src_len,
                                       max_tgt_len=args.max_tgt_len)
    val_size   = max(1, int(len(dataset) * args.val_split))
    train_size = len(dataset) - val_size
    train_ds, val_ds = random_split(
        dataset, [train_size, val_size],
        generator=torch.Generator().manual_seed(42)
    )
    train_loader = DataLoader(train_ds, batch_size=args.batch_size,
                              shuffle=True,  collate_fn=collate_fn, num_workers=0)
    val_loader   = DataLoader(val_ds,   batch_size=args.batch_size,
                              shuffle=False, collate_fn=collate_fn, num_workers=0)
    print(f"[Train] Train/Val      : {train_size}/{val_size}")

    # ── Model ─────────────────────────────────────────────────────────────
    model = CodingQuestionTransformer(
        vocab_size=tokenizer.vocab_size,
        d_model=args.d_model,
        nhead=args.nhead,
        num_encoder_layers=args.enc_layers,
        num_decoder_layers=args.dec_layers,
        dim_feedforward=args.ff_dim,
        dropout=args.dropout,
        max_seq_len=max(args.max_src_len, args.max_tgt_len) + 10,
    ).to(device)

    total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"[Train] Parameters     : {total_params:,}")

    # ── Resume ────────────────────────────────────────────────────────────
    start_epoch = 1
    if args.resume and os.path.exists(args.resume):
        print(f"[Train] Resuming from {args.resume}")
        model.load_state_dict(torch.load(args.resume, map_location=device))

    # ── Loss / Optimizer / Scheduler ──────────────────────────────────────
    criterion = nn.CrossEntropyLoss(ignore_index=0, label_smoothing=args.label_smoothing)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr,
                                  betas=(0.9, 0.98), eps=1e-9,
                                  weight_decay=args.weight_decay)

    steps_per_epoch = math.ceil(len(train_loader) / args.grad_accum)
    total_steps     = args.epochs * steps_per_epoch
    warmup_steps    = args.warmup_epochs * steps_per_epoch
    scheduler = WarmupCosineScheduler(optimizer, warmup_steps, total_steps,
                                      args.lr, args.min_lr)

    # ── Training loop ─────────────────────────────────────────────────────
    best_val_loss    = float("inf")
    patience_counter = 0
    os.makedirs(args.save_dir, exist_ok=True)
    training_log = {"epochs": [], "train_loss": [], "val_loss": [], "gap": []}

    print("\n" + "="*70)
    print(f"{'Epoch':>6} | {'Train':>8} | {'Val':>8} | {'Gap':>7} | {'Time':>6} | Status")
    print("="*70)

    for epoch in range(start_epoch, args.epochs + 1):
        t0 = time.time()
        train_loss = train_epoch(model, train_loader, optimizer, criterion,
                                 scheduler, device, scaler, args.grad_accum)
        val_loss   = eval_epoch(model, val_loader, criterion, device)
        elapsed    = time.time() - t0
        gap        = val_loss - train_loss

        if val_loss < best_val_loss:
            status = "✓ BEST"
            best_val_loss    = val_loss
            patience_counter = 0
            torch.save(model.state_dict(), os.path.join(args.save_dir, "model.pt"))
            tokenizer.save(os.path.join(args.save_dir, "tokenizer.json"))
        elif gap > 1.0:
            status = "⚠ OVERFIT"
            patience_counter += 1
        else:
            patience_counter += 1
            status = f"patience {patience_counter}/{args.patience}"

        print(f"{epoch:>6} | {train_loss:>8.4f} | {val_loss:>8.4f} | "
              f"{gap:>+7.4f} | {elapsed:>5.1f}s | {status}")

        training_log["epochs"].append(epoch)
        training_log["train_loss"].append(round(train_loss, 6))
        training_log["val_loss"].append(round(val_loss, 6))
        training_log["gap"].append(round(gap, 6))

        # Sample generation to see quality
        if args.sample_every > 0 and epoch % args.sample_every == 0:
            sample_output(model, tokenizer, device)

        if patience_counter >= args.patience:
            print(f"\n[Train] Early stopping at epoch {epoch}")
            break

    # Save log
    with open(os.path.join(args.save_dir, "training_log.json"), "w") as f:
        json.dump(training_log, f, indent=2)

    print(f"\n[Train] Done. Best val loss: {best_val_loss:.4f}")
    print(f"[Train] Model saved to: {args.save_dir}/model.pt")


if __name__ == "__main__":
    main()
