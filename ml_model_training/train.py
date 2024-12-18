import os
import sys
import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
import neptune

from dotenv import load_dotenv
from neptune.types import File
from torch.utils.data import DataLoader
from petro_model import PetroModel
from sklearn.model_selection import train_test_split
from neptune.metadata_containers.run import Run

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_engineering.data_utils import add_lags, download_data
from model_utils import train_one_epoch, validate_one_epoch, generate_loader

load_dotenv()


def main(
    num_epochs: int,
    train_loader: DataLoader,
    test_loader: DataLoader,
    model: PetroModel,
    loss_function: nn.MSELoss,
    optimizer: optim.Adam,
    device: str,
    neptune_run: Run,
) -> None:
    # Log hyperparameters
    neptune_run["hyperparameters"] = {
        "num_epochs": num_epochs,
        "batch_size": train_loader.batch_size,
        "learning_rate": optimizer.param_groups[0]["lr"],
        "device": device,
    }

    # Log model architecture
    neptune_run["model/summary"] = str(model)

    for epoch in range(num_epochs):
        train_one_epoch(
            epoch, train_loader, model, loss_function, optimizer, device, neptune_run
        )
        validate_one_epoch(
            epoch, model, test_loader, device, loss_function, neptune_run
        )

    # Save the final model
    torch.save(model.state_dict(), os.path.join("ml_model_training", "final_model.pth"))
    neptune_run["model/final"].upload(
        File(os.path.join("ml_model_training", "final_model.pth"))
    )

    # Stop the Neptune run
    neptune_run.stop()


if __name__ == "__main__":
    # Initialize Neptune run
    neptune_run = neptune.init_run(
        project=os.getenv("NEPTUNE_PROJECT"),
        api_token=os.getenv("NEPTUNE_API_TOKEN"),
    )

    data = download_data().sort_index() ## TODO Adjust environment variable for Lake consumption
    data = add_lags(data, 7, columns=["pbr"])
    pipeline_params = {"num_features": 7}
    device = "cuda" if torch.cuda.is_available() else "cpu"
    train, test = train_test_split(data, shuffle=False, test_size=0.2)
    batch_size = 64
    train_loader = generate_loader(train, pipeline_params, batch_size)
    test_loader = generate_loader(test, pipeline_params, batch_size, shuffle=False)
    model = PetroModel(1, 7, num_stacked_layers=1, dropout=0.0, activation=nn.Tanh(), device=device).to(device)
    learning_rate = 0.055471079560288315
    num_epochs = 75
    loss_function = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)

    # Log dataset information
    neptune_run["data/train_size"] = len(train)
    neptune_run["data/test_size"] = len(test)

    main(
        num_epochs,
        train_loader,
        test_loader,
        model,
        loss_function,
        optimizer,
        device,
        neptune_run,
    )
