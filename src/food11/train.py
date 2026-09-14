from __future__ import annotations

import argparse
from pathlib import Path

import mlflow
import mlflow.pytorch
import torch
from torch import nn, optim
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms
from torchvision.models import ResNet18_Weights


CLASS_COUNT = 11


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train ResNet18 on Food-11 with MLflow tracking.")
    parser.add_argument("--dataset", choices=("mini", "processed"), default="mini")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--lr", type=float, default=0.001)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument("--num-workers", type=int, default=0)
    return parser.parse_args()


def dataset_root(data_root: Path, dataset_name: str) -> Path:
    folder_name = "food11_processed_mini" if dataset_name == "mini" else "food11_processed"
    root = data_root / folder_name
    if not root.exists():
        raise FileNotFoundError(f"Dataset directory does not exist: {root}")
    return root


def make_loaders(root: Path, batch_size: int, num_workers: int) -> tuple[DataLoader, DataLoader, DataLoader]:
    weights = ResNet18_Weights.DEFAULT
    transform = weights.transforms()
    datasets_by_split = {
        split: datasets.ImageFolder(root / split, transform=transform)
        for split in ("training", "validation", "evaluation")
    }
    if any(len(dataset.classes) != CLASS_COUNT for dataset in datasets_by_split.values()):
        raise ValueError(f"Expected {CLASS_COUNT} classes, found {datasets_by_split['training'].classes}")
    loaders = {
        split: DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=split == "training",
            num_workers=num_workers,
        )
        for split, dataset in datasets_by_split.items()
    }
    return loaders["training"], loaders["validation"], loaders["evaluation"]


def evaluate(model: nn.Module, loader: DataLoader, device: torch.device) -> tuple[float, float]:
    model.eval()
    loss_function = nn.CrossEntropyLoss()
    total_loss = 0.0
    correct = 0
    total = 0
    with torch.no_grad():
        for images, labels in loader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            total_loss += loss_function(outputs, labels).item() * labels.size(0)
            correct += (outputs.argmax(dim=1) == labels).sum().item()
            total += labels.size(0)
    return total_loss / total, correct / total


def main() -> None:
    args = parse_args()
    root = dataset_root(args.data_root, args.dataset)
    train_loader, validation_loader, test_loader = make_loaders(root, args.batch_size, args.num_workers)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    mlflow.set_tracking_uri("http://127.0.0.1:5000")
    mlflow.set_experiment("food11")

    with mlflow.start_run():
        mlflow.log_params(
            {
                "dataset": args.dataset,
                "epochs": args.epochs,
                "lr": args.lr,
                "batch_size": args.batch_size,
                "device": str(device),
            }
        )

        model = models.resnet18(weights=ResNet18_Weights.DEFAULT)
        model.fc = nn.Linear(model.fc.in_features, CLASS_COUNT)
        model.to(device)
        optimizer = optim.Adam(model.parameters(), lr=args.lr)
        loss_function = nn.CrossEntropyLoss()

        for epoch in range(args.epochs):
            model.train()
            running_loss = 0.0
            sample_count = 0
            for images, labels in train_loader:
                images, labels = images.to(device), labels.to(device)
                optimizer.zero_grad()
                outputs = model(images)
                loss = loss_function(outputs, labels)
                loss.backward()
                optimizer.step()
                running_loss += loss.item() * labels.size(0)
                sample_count += labels.size(0)

            train_loss = running_loss / sample_count
            validation_loss, validation_accuracy = evaluate(model, validation_loader, device)
            mlflow.log_metrics(
                {
                    "train_loss": train_loss,
                    "val_loss": validation_loss,
                    "val_accuracy": validation_accuracy,
                },
                step=epoch,
            )
            print(
                f"epoch={epoch + 1}/{args.epochs} "
                f"train_loss={train_loss:.4f} "
                f"val_loss={validation_loss:.4f} "
                f"val_accuracy={validation_accuracy:.4f}"
            )

        test_loss, test_accuracy = evaluate(model, test_loader, device)
        mlflow.log_metric("test_accuracy", test_accuracy)
        mlflow.log_metric("test_loss", test_loss)
        input_example = torch.zeros(1, 3, 224, 224, device=device)
        mlflow.pytorch.log_model(
            model,
            "model",
            input_example=input_example,
            serialization_format="pickle",
        )
        print(f"test_loss={test_loss:.4f} test_accuracy={test_accuracy:.4f}")


if __name__ == "__main__":
    main()
