from __future__ import annotations

import torch
from torch import nn


class TransformerLite(nn.Module):
    def __init__(self, input_dim: int, embed_dim: int = 64, n_heads: int = 4, n_layers: int = 2, n_classes: int = 3) -> None:
        super().__init__()
        self.proj = nn.Linear(input_dim, embed_dim)
        encoder_layer = nn.TransformerEncoderLayer(d_model=embed_dim, nhead=n_heads, batch_first=True)
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)
        self.head = nn.Linear(embed_dim, n_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        encoded = self.encoder(self.proj(x))
        return self.head(encoded[:, -1, :])

