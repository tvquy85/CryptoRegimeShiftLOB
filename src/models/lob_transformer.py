from __future__ import annotations

import torch
from torch import nn

from models.deeplob import _conv_block, _validate_lob_window


class LOBTransformerLite(nn.Module):
    """LOBFrame-inspired convolutional LOB stem plus lightweight Transformer encoder."""

    def __init__(
        self,
        *,
        input_dim: int = 40,
        conv_channels: int = 16,
        inception_channels: int = 32,
        n_heads: int = 4,
        n_layers: int = 1,
        dropout: float = 0.1,
        n_classes: int = 3,
    ) -> None:
        super().__init__()
        if input_dim != 40:
            raise ValueError("LOBTransformerLite expects exactly 40 features from 10 LOB levels.")
        d_model = inception_channels * 3
        if d_model % n_heads != 0:
            raise ValueError(f"Transformer d_model={d_model} must be divisible by n_heads={n_heads}.")
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
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=n_heads,
            dim_feedforward=d_model * 2,
            dropout=dropout,
            batch_first=True,
            activation="gelu",
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)
        self.head = nn.Linear(d_model, n_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        _validate_lob_window(x, self.input_dim)
        encoded = self._encode_lob(x)
        output = self.encoder(encoded)
        return self.head(output.mean(dim=1))

    def _encode_lob(self, x: torch.Tensor) -> torch.Tensor:
        x = x.unsqueeze(1)
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        x = torch.cat((self.inception_1(x), self.inception_2(x), self.inception_3(x)), dim=1)
        x = x.permute(0, 2, 1, 3)
        return torch.reshape(x, (x.shape[0], x.shape[1], x.shape[2] * x.shape[3]))
