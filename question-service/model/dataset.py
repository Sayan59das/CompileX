import json
import sys
import os
import re
import torch
from torch.utils.data import Dataset
from typing import List, Dict

# Support both package import and direct script execution
try:
    from .tokenizer import SimpleTokenizer
except ImportError:
    sys.path.insert(0, os.path.dirname(__file__))
    from tokenizer import SimpleTokenizer


def _clean_text(text: str) -> str:
    """Remove Codeforces-style noise: large numbers, LaTeX, backslash commands."""
    text = re.sub(r'\b\d{6,}\b', '', text)          # large numbers
    text = re.sub(r'\$[^$]*\$', '', text)            # LaTeX math
    text = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', text) # \cmd{...}
    text = re.sub(r'\\[a-zA-Z]+', '', text)          # \cmd
    text = re.sub(r'\s+', ' ', text).strip()
    return text


class CodingQuestionDataset(Dataset):
    """
    Expects a JSON file with a list of records:
    [
      {
        "topic": "arrays",
        "difficulty": "medium",
        "title": "Two Sum",
        "problem_statement": "...",
        "input_format": "...",
        "output_format": "...",
        "sample_input": "...",
        "sample_output": "...",
        "test_cases": [
          {"input": "...", "output": "..."},
          ...
        ]
      },
      ...
    ]
    """

    TEMPLATE = (
        "TITLE: {title}\n"
        "PROBLEM STATEMENT:\n{problem_statement}\n\n"
        "INPUT FORMAT:\n{input_format}\n\n"
        "OUTPUT FORMAT:\n{output_format}\n\n"
        "SAMPLE INPUT:\n{sample_input}\n\n"
        "SAMPLE OUTPUT:\n{sample_output}\n\n"
        "TEST CASES:\n{test_cases}"
    )

    def __init__(
        self,
        data_path: str,
        tokenizer: SimpleTokenizer,
        max_src_len: int = 32,
        max_tgt_len: int = 512,
    ):
        self.tokenizer = tokenizer
        self.max_src_len = max_src_len
        self.max_tgt_len = max_tgt_len
        self.samples: List[Dict] = []

        with open(data_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        for item in raw:
            src_text = f"{item.get('topic', '')} {item.get('difficulty', '')}".strip()
            tgt_text = self._format_output(item)
            # Clean both source and target
            src_text = _clean_text(src_text)
            tgt_text = _clean_text(tgt_text)
            self.samples.append({"src": src_text, "tgt": tgt_text})

    def _format_test_cases(self, test_cases):
        lines = []
        for i, tc in enumerate(test_cases, 1):
            lines.append(f"Case {i}:\n  Input: {tc.get('input', '')}\n  Output: {tc.get('output', '')}")
        return "\n".join(lines)

    def _format_output(self, item: Dict) -> str:
        return self.TEMPLATE.format(
            title=item.get("title", ""),
            problem_statement=item.get("problem_statement", ""),
            input_format=item.get("input_format", ""),
            output_format=item.get("output_format", ""),
            sample_input=item.get("sample_input", ""),
            sample_output=item.get("sample_output", ""),
            test_cases=self._format_test_cases(item.get("test_cases", [])),
        )

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        sample = self.samples[idx]
        src_ids = self.tokenizer.encode(sample["src"])
        tgt_ids = self.tokenizer.encode(sample["tgt"])

        # truncate
        src_ids = src_ids[: self.max_src_len]
        tgt_ids = tgt_ids[: self.max_tgt_len]

        return {
            "src": torch.tensor(src_ids, dtype=torch.long),
            "tgt": torch.tensor(tgt_ids, dtype=torch.long),
        }


def collate_fn(batch):
    """Pad sequences in a batch to the same length."""
    src_list = [item["src"] for item in batch]
    tgt_list = [item["tgt"] for item in batch]

    src_padded = torch.nn.utils.rnn.pad_sequence(src_list, batch_first=True, padding_value=0)
    tgt_padded = torch.nn.utils.rnn.pad_sequence(tgt_list, batch_first=True, padding_value=0)

    src_key_padding_mask = src_padded == 0
    tgt_key_padding_mask = tgt_padded == 0

    return {
        "src": src_padded,
        "tgt": tgt_padded,
        "src_key_padding_mask": src_key_padding_mask,
        "tgt_key_padding_mask": tgt_key_padding_mask,
    }
