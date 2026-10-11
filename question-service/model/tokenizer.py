import json
import re
import os
from collections import Counter
from typing import List, Optional


class SimpleTokenizer:
    """
    Character-level / word-level tokenizer built from scratch.
    Special tokens:
        <PAD> = 0
        <UNK> = 1
        <BOS> = 2
        <EOS> = 3
    """

    PAD_TOKEN = "<PAD>"
    UNK_TOKEN = "<UNK>"
    BOS_TOKEN = "<BOS>"
    EOS_TOKEN = "<EOS>"

    SPECIAL_TOKENS = [PAD_TOKEN, UNK_TOKEN, BOS_TOKEN, EOS_TOKEN]

    def __init__(self):
        self.word2id = {}
        self.id2word = {}
        self.vocab_size = 0

        self.pad_id = 0
        self.unk_id = 1
        self.bos_id = 2
        self.eos_id = 3

    # ------------------------------------------------------------------
    # Build vocabulary from a list of texts
    # ------------------------------------------------------------------
    def build_vocab(self, texts: List[str], min_freq: int = 1):
        counter = Counter()
        for text in texts:
            tokens = self._tokenize(text)
            counter.update(tokens)

        self.word2id = {}
        self.id2word = {}

        for idx, token in enumerate(self.SPECIAL_TOKENS):
            self.word2id[token] = idx
            self.id2word[idx] = token

        current_id = len(self.SPECIAL_TOKENS)
        for word, freq in counter.most_common():
            if freq >= min_freq:
                self.word2id[word] = current_id
                self.id2word[current_id] = word
                current_id += 1

        self.vocab_size = current_id
        print(f"[Tokenizer] Vocabulary built: {self.vocab_size} tokens")

    # ------------------------------------------------------------------
    # Tokenization helpers
    # ------------------------------------------------------------------
    def _tokenize(self, text: str) -> List[str]:
        """Simple whitespace + punctuation tokenizer."""
        text = text.lower()
        # keep newlines as tokens
        text = text.replace("\n", " <NEWLINE> ")
        tokens = re.findall(r"<[A-Z]+>|[a-z0-9]+|[^\w\s]", text)
        return tokens

    def encode(self, text: str, add_special_tokens: bool = True) -> List[int]:
        tokens = self._tokenize(text)
        ids = [self.word2id.get(t, self.unk_id) for t in tokens]
        if add_special_tokens:
            ids = [self.bos_id] + ids + [self.eos_id]
        return ids

    def decode(self, ids: List[int], skip_special_tokens: bool = True) -> str:
        tokens = []
        for i in ids:
            word = self.id2word.get(i, self.UNK_TOKEN)
            if skip_special_tokens and word in self.SPECIAL_TOKENS:
                continue
            tokens.append(word)

        text = " ".join(tokens)
        text = text.replace(" <newline> ", "\n")
        text = text.replace("<newline>", "\n")
        text = text.replace(" <NEWLINE> ", "\n")
        text = text.replace("<NEWLINE>", "\n")
        return text

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def save(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = {
            "word2id": self.word2id,
            "id2word": {str(k): v for k, v in self.id2word.items()},
            "vocab_size": self.vocab_size,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"[Tokenizer] Saved to {path}")

    def load(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.word2id = data["word2id"]
        self.id2word = {int(k): v for k, v in data["id2word"].items()}
        self.vocab_size = data["vocab_size"]
        print(f"[Tokenizer] Loaded from {path} — vocab size: {self.vocab_size}")
