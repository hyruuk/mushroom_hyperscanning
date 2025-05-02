import argparse
import os
import gdown

def download_drive_folder(folder_url, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Download using gdown 5.x (browser auth if required)
    gdown.download_folder(url=folder_url, output=output_dir, quiet=False)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download private Google Drive folder.')
    parser.add_argument('--output_dir', type=str, default='../data/', help='Output directory for downloaded files.')
    args = parser.parse_args()

    folder_url = input("Copy and paste here the link to the bidsified data folder on Google Drive: ").strip()

    download_drive_folder(folder_url, args.output_dir)

