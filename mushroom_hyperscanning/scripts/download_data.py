import argparse
import os
from pathlib import Path

import gdown


def download_drive_folder(folder_url, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Download using gdown 5.x (browser auth if required)
    gdown.download_folder(url=folder_url, output=str(output_dir), quiet=False)


if __name__ == "__main__":
    default_dir = Path(__file__).resolve().parent.parent.parent / "data" / "bids_dataset"

    parser = argparse.ArgumentParser(description="Download private Google Drive folder.")
    parser.add_argument("--output_dir", type=str, default=default_dir, help="Output directory for downloaded files.")
    args = parser.parse_args()

    # folder_url = input("Copy and paste here the link to the bidsified data folder on Google Drive: ").strip()
    folder_url = "https://drive.google.com/drive/folders/1vp6Iarv9wRsDUBCvG5FjU4cSZVz3VmxG?usp=drive_link"

    print(f"Downloading data to {args.output_dir}")
    download_drive_folder(folder_url, args.output_dir)
