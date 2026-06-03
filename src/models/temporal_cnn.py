from __future__ import annotations

import torch
from torch import nn


class TemporalCNN(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int = 64, n_classes: int = 3) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(input_dim, hidden_dim, kernel_size=5, padding=2),
            nn.ReLU(),
            nn.Conv1d(hidden_dim, hidden_dim, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.AdaptiveAvgPool1d(1),
        )
        self.head = nn.Linear(hidden_dim, n_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        encoded = self.net(x.transpose(1, 2)).squeeze(-1)
        return self.head(encoded)

