
from pathlib import Path

import pandas as pd
from ucimlrepo import fetch_ucirepo


def download_uci_concrete():
    """Download and save the UCI concrete strength dataset."""

    dataset = fetch_ucirepo(id=165)

    X = dataset.data.features
    y = dataset.data.targets

    df = pd.concat([X, y], axis=1)

    output_dir = Path("data/raw")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "uci_concrete.csv"

    df.to_csv(output_path, index=False)

    print("Dataset downloaded successfully!")
    print(f"Shape: {df.shape}")
    print(f"Saved to: {output_path}")

    print("\nFirst five observations:")
    print(df.head())

    print("\nMissing values:")
    print(df.isnull().sum())

    return df


if __name__ == "__main__":
    download_uci_concrete()
