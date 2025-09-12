import os
from os.path import dirname, join
from typing import Tuple

import mne
import numpy as np
from mne_bids import BIDSPath
from pydub import AudioSegment

CH_TYPE_MAPPING = {"CM": "misc", "ECG": "ecg"}


def load_eeg(sub: str, ceremony: str, root: str, preload: bool = False) -> mne.io.BaseRaw:
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
    raw = mne.io.read_raw(paths[0], preload=preload)
    raw.info.set_channel_types({ch: CH_TYPE_MAPPING[ch] if ch in CH_TYPE_MAPPING else "eeg" for ch in raw.ch_names})
    raw.set_montage(mne.channels.make_standard_montage("standard_1020"))
    return raw


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
