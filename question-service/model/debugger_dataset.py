"""
Dataset for the code debugger hint model.

Each sample maps:
  src: problem + code + language + failed_test_input + expected + actual
  tgt: JSON hint string
"""

import json
import sys
import os
import torch
from torch.utils.data import Dataset
from typing import List, Dict

try:
    from .tokenizer import SimpleTokenizer
except ImportError:
    sys.path.insert(0, os.path.dirname(__file__))
    from tokenizer import SimpleTokenizer


def format_debugger_src(item: Dict) -> str:
    return (
        f"LANGUAGE: {item.get('language', '')}\n"
        f"PROBLEM:\n{item.get('problem_statement', '')}\n\n"
        f"CODE:\n{item.get('user_code', '')}\n\n"
        f"FAILED INPUT:\n{item.get('failed_test_input', '')}\n\n"
        f"EXPECTED:\n{item.get('expected_output', '')}\n\n"
        f"ACTUAL:\n{item.get('actual_output', '')}"
    )


def load_debugger_texts(data_path: str) -> List[str]:
    """Load all text fields for vocabulary building."""
    with open(data_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    texts = []
    for item in raw:
        texts.append(format_debugger_src(item))
        texts.append(item.get("hint", ""))
    return texts


class DebuggerDataset(Dataset):
    def __init__(
        self,
        data_path: str,
        tokenizer: SimpleTokenizer,
        max_src_len: int = 512,
        max_tgt_len: int = 128,
    ):
        self.tokenizer = tokenizer
        self.max_src_len = max_src_len
        self.max_tgt_len = max_tgt_len
        self.samples: List[Dict] = []

        with open(data_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        for item in raw:
            src_text = format_debugger_src(item)
            tgt_text = item.get("hint", "")
            self.samples.append({"src": src_text, "tgt": tgt_text})

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        sample = self.samples[idx]
        src_ids = self.tokenizer.encode(sample["src"])[: self.max_src_len]
        tgt_ids = self.tokenizer.encode(sample["tgt"])[: self.max_tgt_len]
        return {
            "src": torch.tensor(src_ids, dtype=torch.long),
            "tgt": torch.tensor(tgt_ids, dtype=torch.long),
        }


def collate_fn(batch):
    src_list = [item["src"] for item in batch]
    tgt_list = [item["tgt"] for item in batch]
    src_padded = torch.nn.utils.rnn.pad_sequence(src_list, batch_first=True, padding_value=0)
    tgt_padded = torch.nn.utils.rnn.pad_sequence(tgt_list, batch_first=True, padding_value=0)
    return {
        "src": src_padded,
        "tgt": tgt_padded,
        "src_key_padding_mask": src_padded == 0,
        "tgt_key_padding_mask": tgt_padded == 0,
    }
