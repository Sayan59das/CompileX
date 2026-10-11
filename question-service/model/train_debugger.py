"""
Training script for the Debugger Hint Transformer.

Usage (from backend root):
    python model/train_debugger.py --data data/debugger_hints.json --epochs 200 --save_dir model/saved_debugger_model
"""

import argparse
import os
import sys
import json
import time
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split

sys.path.insert(0, os.path.dirname(__file__))
from tokenizer import SimpleTokenizer
from debugger_dataset import DebuggerDataset, collate_fn, load_debugger_texts
from transformer_model import CodingQuestionTransformer

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

torch.backends.cudnn.benchmark = True


def train_epoch(model, loader, optimizer, criterion, device, scaler=None):
    model.train()
    total_loss = 0
    iterator = tqdm(loader, desc="  Train", leave=False) if TQDM_AVAILABLE else loader
    for batch in iterator:
        src = batch["src"].to(device)
        tgt = batch["tgt"].to(device)
        src_mask = batch["src_key_padding_mask"].to(device)
        tgt_mask = batch["tgt_key_padding_mask"].to(device)

        tgt_input = tgt[:, :-1]
        tgt_label = tgt[:, 1:]
        tgt_input_mask = tgt_mask[:, :-1]

        optimizer.zero_grad()
        if scaler:
            with torch.amp.autocast("cuda"):
                logits = model(src, tgt_input, src_key_padding_mask=src_mask, tgt_key_padding_mask=tgt_input_mask)
                loss = criterion(logits.reshape(-1, logits.size(-1)), tgt_label.reshape(-1))
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(optimizer)
            scaler.update()
        else:
            logits = model(src, tgt_input, src_key_padding_mask=src_mask, tgt_key_padding_mask=tgt_input_mask)
            loss = criterion(logits.reshape(-1, logits.size(-1)), tgt_label.reshape(-1))
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

        total_loss += loss.item()
        if TQDM_AVAILABLE:
            iterator.set_postfix(loss=f"{loss.item():.4f}")
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
        logits = model(src, tgt_input, src_key_padding_mask=src_mask, tgt_key_padding_mask=tgt_input_mask)
        loss = criterion(logits.reshape(-1, logits.size(-1)), tgt_label.reshape(-1))
        total_loss += loss.item()
    return total_loss / len(loader)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, default="data/debugger_hints.json")
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--batch_size", type=int, default=4)
    parser.add_argument("--lr", type=float, default=5e-4)
    parser.add_argument("--d_model", type=int, default=256)
    parser.add_argument("--nhead", type=int, default=8)
    parser.add_argument("--enc_layers", type=int, default=3)
    parser.add_argument("--dec_layers", type=int, default=3)
    parser.add_argument("--save_dir", type=str, default="model/saved_debugger_model")
    parser.add_argument("--val_split", type=float, default=0.15)
    parser.add_argument("--min_freq", type=int, default=1)
    parser.add_argument("--max_src_len", type=int, default=512)
    parser.add_argument("--max_tgt_len", type=int, default=128)
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    device = torch.device(args.device)
    print(f"[Debugger Train] Device: {device}")

    use_amp = device.type == "cuda"
    scaler = torch.amp.GradScaler("cuda") if use_amp else None

    print("[Debugger Train] Building vocabulary...")
    tokenizer = SimpleTokenizer()
    texts = load_debugger_texts(args.data)
    tokenizer.build_vocab(texts, min_freq=args.min_freq)

    dataset = DebuggerDataset(args.data, tokenizer, args.max_src_len, args.max_tgt_len)
    val_size = max(1, int(len(dataset) * args.val_split))
    train_size = len(dataset) - val_size
    train_ds, val_ds = random_split(dataset, [train_size, val_size])

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, collate_fn=collate_fn)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, collate_fn=collate_fn)
    print(f"[Debugger Train] Train: {train_size} | Val: {val_size}")

    model = CodingQuestionTransformer(
        vocab_size=tokenizer.vocab_size,
        d_model=args.d_model,
        nhead=args.nhead,
        num_encoder_layers=args.enc_layers,
        num_decoder_layers=args.dec_layers,
        dim_feedforward=args.d_model * 2,
        max_seq_len=max(args.max_src_len, args.max_tgt_len) + 10,
    ).to(device)

    print(f"[Debugger Train] Parameters: {sum(p.numel() for p in model.parameters() if p.requires_grad):,}")

    criterion = nn.CrossEntropyLoss(ignore_index=0)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr, betas=(0.9, 0.98), eps=1e-9, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", patience=3, factor=0.5)

    best_val_loss = float("inf")
    patience_counter = 0
    early_stop_patience = 10
    os.makedirs(args.save_dir, exist_ok=True)
    training_log = {"epochs": [], "train_loss": [], "val_loss": []}

    for epoch in range(1, args.epochs + 1):
        t0 = time.time()
        train_loss = train_epoch(model, train_loader, optimizer, criterion, device, scaler)
        val_loss = eval_epoch(model, val_loader, criterion, device)
        scheduler.step(val_loss)
        print(f"Epoch {epoch:03d} | Train: {train_loss:.4f} | Val: {val_loss:.4f} | {time.time()-t0:.1f}s")

        training_log["epochs"].append(epoch)
        training_log["train_loss"].append(round(train_loss, 6))
        training_log["val_loss"].append(round(val_loss, 6))

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            torch.save(model.state_dict(), os.path.join(args.save_dir, "model.pt"))
            tokenizer.save(os.path.join(args.save_dir, "tokenizer.json"))
            print(f"  Saved best model (val_loss={val_loss:.4f})")
        else:
            patience_counter += 1
            if patience_counter >= early_stop_patience:
                print(f"[Debugger Train] Early stopping at epoch {epoch}")
                break

    with open(os.path.join(args.save_dir, "training_log.json"), "w") as f:
        json.dump(training_log, f, indent=2)
    print("[Debugger Train] Done.")


if __name__ == "__main__":
    main()
