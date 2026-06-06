from __future__ import annotations

import torch
from torch import nn


class DeepLOB(nn.Module):
    """LOBFrame-inspired DeepLOB CNN-Inception-LSTM for [batch, time, 40] windows."""

    def __init__(
        self,
        *,
        input_dim: int = 40,
        conv_channels: int = 32,
        inception_channels: int = 64,
        hidden_dim: int = 64,
        n_classes: int = 3,
    ) -> None:
        super().__init__()
        if input_dim != 40:
            raise ValueError("DeepLOB expects exactly 40 features from 10 LOB levels.")
        self.input_dim = input_dim
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
        _validate_lob_window(x, self.input_dim)
        encoded = self._encode_lob(x)
        output, _ = self.temporal(encoded)
        return self.head(output[:, -1, :])

    def _encode_lob(self, x: torch.Tensor) -> torch.Tensor:
        x = x.unsqueeze(1)
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        x = torch.cat((self.inception_1(x), self.inception_2(x), self.inception_3(x)), dim=1)
        x = x.permute(0, 2, 1, 3)
        return torch.reshape(x, (x.shape[0], x.shape[1], x.shape[2] * x.shape[3]))


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


def _validate_lob_window(x: torch.Tensor, input_dim: int) -> None:
    if x.ndim != 3:
        raise ValueError("LOB temporal models expect input shape [batch, time, features].")
    if x.shape[-1] != input_dim:
        raise ValueError(f"Expected {input_dim} LOB features, got {x.shape[-1]}.")
