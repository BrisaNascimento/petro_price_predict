import torch
import torch.nn as nn
from typing import Callable


class PetroModel(nn.Module):
    def __init__(
        self, 
        input_size: int, 
        hidden_size: int, 
        num_stacked_layers: int, 
        device: str, 
        dropout: float, 
        activation: Callable
    ) -> None:
        super().__init__()
        ## Model Params
        self.hidden_size = hidden_size
        self.num_stacked_layers = num_stacked_layers
        self.device = device

        ##Model Architecture
        self.lstm = nn.LSTM(
            input_size, hidden_size, num_stacked_layers, batch_first=True, dropout=dropout
        )
        self.fc = nn.Linear(hidden_size, 1)
        self.activation = activation

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch_size = x.size(0)
        h0 = torch.zeros(self.num_stacked_layers, batch_size, self.hidden_size).to(
            self.device
        )
        c0 = torch.zeros(self.num_stacked_layers, batch_size, self.hidden_size).to(
            self.device
        )
        out, _ = self.lstm(x, (h0, c0))
        out = self.fc(out[:, -1, :])
        out = self.activation(out)
        return out
