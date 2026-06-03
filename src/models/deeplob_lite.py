from __future__ import annotations

import torch
from torch import nn


class DeepLOBLite(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int = 64, n_classes: int = 3) -> None:
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv1d(input_dim, hidden_dim, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv1d(hidden_dim, hidden_dim, kernel_size=5, padding=2),
            nn.ReLU(),
        )
        self.temporal = nn.GRU(hidden_dim, hidden_dim, batch_first=True)
        self.head = nn.Linear(hidden_dim, n_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        encoded = self.conv(x.transpose(1, 2)).transpose(1, 2)
        output, _ = self.temporal(encoded)
        return self.head(output[:, -1, :])


class DeepLOBFaithfulLite(nn.Module):
    """A compact DeepLOB-style CNN+LSTM for 100x40 LOB windows."""

    def __init__(self, conv_channels: int = 16, inception_channels: int = 32, hidden_dim: int = 64, n_classes: int = 3) -> None:
        super().__init__()
        self.conv1 = _conv_block(1, conv_channels, width_kernel=2, width_stride=2)
        self.conv2 = _conv_block(conv_channels, conv_channels, width_kernel=2, width_stride=2)
        self.conv3 = _conv_block(conv_channels, conv_channels, width_kernel=10, width_stride=1)
        self.inception_1 = nn.Sequential(
            nn.Conv2d(conv_channels, inception_channels, kernel_size=(1, 1), padding="same"),
            nn.LeakyReLU(negative_slope=0.01),
            nn.BatchNorm2d(inception_channels),
            nn.Conv2d(inception_channels, inception_channels, kernel_size=(3, 1), padding="same"),
            nn.LeakyReLU(negative_slope=0.01),
            nn.BatchNorm2d(inception_channels),
        )
        self.inception_2 = nn.Sequential(
            nn.Conv2d(conv_channels, inception_channels, kernel_size=(1, 1), padding="same"),
            nn.LeakyReLU(negative_slope=0.01),
            nn.BatchNorm2d(inception_channels),
            nn.Conv2d(inception_channels, inception_channels, kernel_size=(5, 1), padding="same"),
            nn.LeakyReLU(negative_slope=0.01),
            nn.BatchNorm2d(inception_channels),
        )
        self.inception_3 = nn.Sequential(
            nn.MaxPool2d((3, 1), stride=(1, 1), padding=(1, 0)),
            nn.Conv2d(conv_channels, inception_channels, kernel_size=(1, 1), padding="same"),
            nn.LeakyReLU(negative_slope=0.01),
            nn.BatchNorm2d(inception_channels),
        )
        self.temporal = nn.LSTM(input_size=inception_channels * 3, hidden_size=hidden_dim, num_layers=1, batch_first=True)
        self.head = nn.Linear(hidden_dim, n_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [batch, time, 40] -> [batch, channels=1, time, lob_features]
        x = x.unsqueeze(1)
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        x = torch.cat((self.inception_1(x), self.inception_2(x), self.inception_3(x)), dim=1)
        x = x.permute(0, 2, 1, 3)
        x = torch.reshape(x, (x.shape[0], x.shape[1], x.shape[2] * x.shape[3]))
        output, _ = self.temporal(x)
        return self.head(output[:, -1, :])


def _conv_block(in_channels: int, out_channels: int, *, width_kernel: int, width_stride: int) -> nn.Sequential:
    return nn.Sequential(
        nn.Conv2d(in_channels, out_channels, kernel_size=(1, width_kernel), stride=(1, width_stride)),
        nn.LeakyReLU(negative_slope=0.01),
        nn.BatchNorm2d(out_channels),
        nn.Conv2d(out_channels, out_channels, kernel_size=(4, 1)),
        nn.LeakyReLU(negative_slope=0.01),
        nn.BatchNorm2d(out_channels),
        nn.Conv2d(out_channels, out_channels, kernel_size=(4, 1)),
        nn.LeakyReLU(negative_slope=0.01),
        nn.BatchNorm2d(out_channels),
    )
