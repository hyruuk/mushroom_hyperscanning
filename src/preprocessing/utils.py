import os
import shutil
from os.path import dirname, exists, join
from shutil import copytree
from typing import Optional

import mne
import pandas as pd
from mne import io
from mne_bids import BIDSPath


def create_derivative_directory(
    derivative_name: str, bids_root: str, previous_derivative: Optional[str] = None, overwrite: bool = False
) -> str:
    """
    Copy the BIDS dataset at `source_bids_root` over to the `<bids_root>/../<derivative_name>` folder.
    If `source_bids_root` is None, the base BIDS dataset at `bids_root` will be copied.

    Parameters
    ----------
    derivative_name : str
        Name of the derivative dataset.
    bids_root : str
        Path to the root of the BIDS dataset.
    previous_derivative : str, optional
        Path to the previous derivative dataset, by default None
    overwrite : bool, optional
        Whether to overwrite the derivative dataset if it already exists, by default False

    Returns
    -------
    str
        Path to the derivative dataset.
    """
    target_dir = join(dirname(bids_root), derivative_name)
    if exists(target_dir):
        if not overwrite:
            raise FileExistsError(f"Derivative {target_dir} already exists.")
        else:
            # remove the existing directory
            shutil.rmtree(target_dir)

    if previous_derivative is None:
        previous_derivative = bids_root

    print(
        f"{'Overwriting' if overwrite else 'Creating'} derivative {derivative_name} at "
        f"{join(bids_root, 'derivatives', derivative_name)}...",
        end="",
        flush=True,
    )
    copytree(
        previous_derivative,
        target_dir,
        ignore=lambda _, n: ["derivatives"] if "derivatives" in n else [],
        dirs_exist_ok=overwrite,
    )
    print("done")
    return target_dir


class PrintBlock:
    def __init__(self, title: str):
        self.title = title

    def __enter__(self):
        title = "Starting " + self.title
        width = len(title) + 4
        print("╒" + "═" * width + "╕")
        print(f"│ {title.center(width - 2)} │")
        print("╘" + "═" * width + "╛")

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            title = "Error in " + self.title + f" ({exc_type.__name__})"
            width = len(title) + 4
            print("╒" + "═" * width + "╕")
            print(f"│ {title.center(width - 2)} │")
            print("╘" + "═" * width + "╛")
        else:
            title = "Finished " + self.title
            width = len(title) + 4
            print("╒" + "═" * width + "╕")
            print(f"│ {title.center(width - 2)} │")
            print("╘" + "═" * width + "╛")


def load_eeg(sub, ceremony, root, preload=False):
    paths = BIDSPath(
        subject=sub,
        session=ceremony,
        task="psilo",
        datatype="eeg",
        root=root,
    ).match()

    assert len(paths) == 1, f"Expected 1 path, got {len(paths)} paths: {paths}"
    return io.read_raw(paths[0], preload=preload)


def save_eeg(raw, sub, ceremony, root):
    bids_path = str(
        BIDSPath(
            subject=sub,
            session=ceremony,
            task="psilo",
            datatype="eeg",
            root=root,
        )
    )

    os.makedirs(dirname(bids_path), exist_ok=True)

    if not bids_path.endswith(".edf"):
        bids_path = bids_path + ".edf"

    mne.export.export_raw(bids_path, raw, overwrite=True)
