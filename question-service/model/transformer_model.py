import torch
import torch.nn as nn
import math


class PositionalEncoding(nn.Module):
    def __init__(self, d_model, max_len=512, dropout=0.1):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(
            torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model)
        )
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)  # (1, max_len, d_model)
        self.register_buffer("pe", pe)

    def forward(self, x):
        x = x + self.pe[:, : x.size(1), :]
        return self.dropout(x)


class CodingQuestionTransformer(nn.Module):
    """
    Seq2Seq Transformer that maps:
        input  : topic token sequence  (e.g. "arrays sorting")
        output : full problem statement with test cases
    """

    def __init__(
        self,
        vocab_size: int,
        d_model: int = 256,
        nhead: int = 8,
        num_encoder_layers: int = 3,
        num_decoder_layers: int = 3,
        dim_feedforward: int = 512,
        dropout: float = 0.1,
        max_seq_len: int = 512,
    ):
        super().__init__()
        self.d_model = d_model
        self.vocab_size = vocab_size

        self.src_embedding = nn.Embedding(vocab_size, d_model, padding_idx=0)
        self.tgt_embedding = nn.Embedding(vocab_size, d_model, padding_idx=0)
        self.pos_encoding = PositionalEncoding(d_model, max_len=max_seq_len, dropout=dropout)

        self.transformer = nn.Transformer(
            d_model=d_model,
            nhead=nhead,
            num_encoder_layers=num_encoder_layers,
            num_decoder_layers=num_decoder_layers,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
        )

        self.output_projection = nn.Linear(d_model, vocab_size)
        self._init_weights()

    def _init_weights(self):
        for p in self.parameters():
            if p.dim() > 1:
                nn.init.xavier_uniform_(p)

    def encode(self, src, src_key_padding_mask=None):
        src_emb = self.pos_encoding(self.src_embedding(src) * math.sqrt(self.d_model))
        return self.transformer.encoder(src_emb, src_key_padding_mask=src_key_padding_mask)

    def decode(self, tgt, memory, tgt_mask=None, tgt_key_padding_mask=None, memory_key_padding_mask=None):
        tgt_emb = self.pos_encoding(self.tgt_embedding(tgt) * math.sqrt(self.d_model))
        return self.transformer.decoder(
            tgt_emb,
            memory,
            tgt_mask=tgt_mask,
            tgt_key_padding_mask=tgt_key_padding_mask,
            memory_key_padding_mask=memory_key_padding_mask,
        )

    def forward(self, src, tgt, src_key_padding_mask=None, tgt_key_padding_mask=None):
        tgt_seq_len = tgt.size(1)
        tgt_mask = nn.Transformer.generate_square_subsequent_mask(tgt_seq_len, device=src.device)

        memory = self.encode(src, src_key_padding_mask)
        output = self.decode(tgt, memory, tgt_mask=tgt_mask, tgt_key_padding_mask=tgt_key_padding_mask, memory_key_padding_mask=src_key_padding_mask)
        logits = self.output_projection(output)
        return logits

    @torch.no_grad()
    def generate(self, src, tokenizer, max_new_tokens=400, temperature=0.8, top_k=50, top_p=0.9, repetition_penalty=1.1):
        """
        Enhanced generation with multiple sampling techniques for creativity.
        src: (1, src_len) tensor of token ids
        """
        self.eval()
        device = src.device
        bos_id = tokenizer.bos_id
        eos_id = tokenizer.eos_id

        # Respect the model's positional encoding limit
        max_pos = self.pos_encoding.pe.size(1)
        max_new_tokens = min(max_new_tokens, max_pos - src.size(1) - 2)

        memory = self.encode(src)
        generated = torch.tensor([[bos_id]], dtype=torch.long, device=device)
        past_tokens = set()

        for _ in range(max_new_tokens):
            tgt_mask = nn.Transformer.generate_square_subsequent_mask(generated.size(1), device=device)
            out = self.decode(generated, memory, tgt_mask=tgt_mask)
            logits = self.output_projection(out[:, -1, :])  # (1, vocab)

            # Apply repetition penalty to encourage diversity
            for token_id in past_tokens:
                logits[0, token_id] /= repetition_penalty

            # Temperature scaling
            logits = logits / temperature

            # Top-k filtering
            if top_k > 0:
                values, _ = torch.topk(logits, top_k)
                min_val = values[:, -1].unsqueeze(-1)
                logits = logits.masked_fill(logits < min_val, float("-inf"))

            # Top-p (nucleus) sampling for additional creativity
            if top_p < 1.0:
                sorted_logits, sorted_indices = torch.sort(logits, descending=True)
                sorted_probs = torch.softmax(sorted_logits, dim=-1)
                cumulative_probs = torch.cumsum(sorted_probs, dim=-1)
                
                # Remove tokens with cumulative probability above top_p
                sorted_logits = sorted_logits.masked_fill(cumulative_probs > top_p, float("-inf"))
                
                # Reconstruct original order
                logits = torch.full_like(logits, float("-inf"))
                logits.scatter_(1, sorted_indices, sorted_logits)

            # Replace invalid logits with very low values before softmax
            logits = torch.nan_to_num(logits, neginf=-1e9, nan=-1e9, posinf=1e9)
            probs = torch.softmax(logits, dim=-1)

            # If softmax failed or probabilities are invalid, use a safe fallback
            if torch.isnan(probs).any() or torch.sum(probs) == 0:
                probs = torch.ones_like(probs, device=device) / probs.size(-1)

            next_token = torch.multinomial(probs, num_samples=1)

            if next_token.item() == eos_id:
                break

            generated = torch.cat([generated, next_token], dim=1)
            
            # Track recent tokens for repetition penalty (last 20 tokens)
            current_token = next_token.item()
            past_tokens.add(current_token)
            if len(past_tokens) > 20:
                # Remove oldest token (simple FIFO)
                past_tokens_list = list(past_tokens)
                past_tokens.remove(past_tokens_list[0])

        token_ids = generated[0, 1:].tolist()  # strip BOS
        return tokenizer.decode(token_ids)
