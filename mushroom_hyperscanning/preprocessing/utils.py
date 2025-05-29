import os
import shutil
from os.path import dirname, exists, join
from shutil import copytree
from typing import Optional, Tuple

import mne
import numpy as np
from mne import io
from mne_bids import BIDSPath
from pydub import AudioSegment


def create_derivative_directory(
    derivative_name: str, bids_root: str, previous_derivative: Optional[str] = None, overwrite: bool = False
) -> str:
    """
    Copy the BIDS dataset at `source_bids_root` over to the `<bids_root>/../<derivative_name>` folder.
    If `source_bids_root` is None, the base BIDS dataset at `bids_root` will be copied.

    Args:
        derivative_name (str): Name of the derivative directory to create.
        bids_root (str): Root directory of the BIDS dataset.
        previous_derivative (Optional[str]): Path to the previous derivative to copy from. If None, uses `bids_root`.
        overwrite (bool): Whether to overwrite the existing derivative directory if it exists.
    Returns:
        str: Path to the created derivative directory.
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
    """
    A context manager that prints a block of text with a title, indicating the start and end of a process.
    It also handles exceptions by printing an error message if an exception occurs.
    """

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


def load_eeg(sub: str, ceremony: str, root: str, preload: bool = False) -> mne.io.Raw:
    """
    Load EEG data for a given subject and ceremony from the BIDS dataset.

    Args:
        sub (str): Subject identifier.
        ceremony (str): Ceremony identifier.
        root (str): Root directory of the BIDS dataset.
        preload (bool): Whether to preload the data into memory.
    Returns:
        mne.io.Raw: The loaded EEG data.
    """
    paths = BIDSPath(
        subject=sub,
        session=ceremony,
        task="psilo",
        datatype="eeg",
        root=root,
    ).match()

    if len(paths) == 0:
        raise FileNotFoundError(f"No EEG data found for subject {sub} in ceremony {ceremony}.")
    return io.read_raw(paths[0], preload=preload)


def save_eeg(raw: mne.io.Raw, sub: str, ceremony: str, root: str) -> None:
    """
    Save EEG data to the BIDS format.

    Args:
        raw (mne.io.Raw): The EEG data to save.
        sub (str): Subject identifier.
        ceremony (str): Ceremony identifier.
        root (str): Root directory of the BIDS dataset.
    """
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
    if "_eeg" not in bids_path:
        bids_path = bids_path + "_eeg"
    if not bids_path.endswith(".edf"):
        bids_path = bids_path + ".edf"
    mne.export.export_raw(bids_path, raw, physical_range="channelwise", overwrite=True)


def load_audio(ceremony: str, root: str) -> Tuple[np.ndarray, int]:
    """
    Load audio data for a given ceremony from the BIDS dataset.

    Args:
        ceremony (str): Ceremony identifier.
        root (str): Root directory of the BIDS dataset.
    Returns:
        tuple: A tuple containing the audio data as a NumPy array and the sample rate.
    """
    path = join(root, "audio", f"ses-{ceremony}", f"audio_ses-{ceremony}_task-psilo_audio.mp3")

    audio = AudioSegment.from_mp3(path)
    srate = audio.frame_rate
    audio = np.array(audio.get_array_of_samples())
    return audio, srate
