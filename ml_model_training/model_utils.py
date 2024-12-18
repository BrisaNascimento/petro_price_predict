import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd

from dotenv import load_dotenv
from torch.utils.data import DataLoader
from petro_dataset import PetroDataset
from petro_model import PetroModel
from neptune.metadata_containers.run import Run

load_dotenv()


def train_one_epoch(
    epoch: int,
    train_loader: DataLoader,
    model: PetroModel,
    loss_function: nn.MSELoss,
    optimizer: optim.Adam,
    device: str,
    neptune_run: Run,
) -> None:
    print(f"Training Epoch: {epoch+1}")
    model.train(True)
    running_loss = 0.0
    avg_loss = 0.0

    for batch_index, batch in enumerate(train_loader):
        x_batch, y_batch = batch[0].to(device), batch[1].to(device)

        outputs = model(x_batch)
        loss = loss_function(outputs, y_batch)
        running_loss += loss.item()
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if batch_index % 100 == 99:
            avg_loss = running_loss / 100
            print(f"Batch {batch_index + 1}, Loss: {avg_loss}")
            neptune_run["train/batch_loss"].log(avg_loss)
            running_loss = 0.0

    neptune_run["train/epoch"].log(epoch + 1)
    print()
    return avg_loss


def validate_one_epoch(
    epoch: int,
    model: PetroModel,
    test_loader: DataLoader,
    device: str,
    loss_function: nn.MSELoss,
    neptune_run: Run,
) -> None:
    print(f"Validation Epoch: {epoch+1}")
    model.train(False)
    running_loss = 0.0

    for batch_index, batch in enumerate(test_loader):
        x_batch, y_batch = batch[0].to(device), batch[1].to(device)
        with torch.no_grad():
            output = model(x_batch)
            loss = loss_function(output, y_batch)
            running_loss += loss.item()

    avg_loss_across_batches = running_loss / len(test_loader)
    #yield avg_loss_across_batches
    print(f"Validation Loss: {avg_loss_across_batches}")
    neptune_run["validation/loss"].log(avg_loss_across_batches)
    print("*********************************************")
    print()
    return avg_loss_across_batches


def generate_loader(
    data: pd.DataFrame, pipeline_params: dict, batch_size: int, shuffle: bool = True
) -> DataLoader:
    dataset = PetroDataset(data, pipeline_params)
    dataset()
    return DataLoader(dataset, batch_size, shuffle)

def add_lags(data:pd.DataFrame, num_lags:int, columns:list) -> pd.DataFrame:
    """
    This function will generate the lags for the columns I chose.
    This means that I can interate each every column I want and set a number or lags that I may use in my model later.
    """
    df = data.copy()
    for column in columns:
        for i in range(1, num_lags + 1):
            df[f"{column}_(t-{i})"] = df[column].shift(i)
    df.dropna(inplace=True)
    return df