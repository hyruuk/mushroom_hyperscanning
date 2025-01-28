import warnings
from os.path import expanduser, join
from typing import Literal, Optional, Tuple

import mne
import numpy as np

DATA_BASE = "~/projects/mexico/"


def load_eeg(
    ceremony: Literal["first", "second"],
    participant: Literal["patient", "curandero"],
    bandpass: Optional[Tuple[int, int]] = None,
    notch: Optional[int] = None,
) -> mne.io.Raw:
    paths = []
    if ceremony == "first" and participant == "patient":
        paths = [
            "ceremony1/Hortensia/EEG/session1_01_raw.edf",
            "ceremony1/Hortensia/EEG/session1_02_raw.edf",
            "ceremony1/Hortensia/EEG/session1_03_raw.edf",
            "ceremony1/Hortensia/EEG/session1_04_raw.edf",
            "ceremony1/Hortensia/EEG/session1_05_raw.edf",
            "ceremony1/Hortensia/EEG/session1_06_raw.edf",
            "ceremony1/Hortensia/EEG/session1_07_raw.edf",
            "ceremony1/Hortensia/EEG/session1_08_raw.edf",
        ]
        warnings.warn(
            "EEG data from Hortensia (first ceremony, patient) is not continuous and still needs to be aligned."
        )
    elif ceremony == "first" and participant == "curandero":
        paths = ["ceremony1/Hugo/session1_raw.edf"]
    elif ceremony == "second" and participant == "patient":
        paths = ["ceremony2/Gabi/EEG/session2_raw.edf"]
    elif ceremony == "second" and participant == "curandero":
        paths = ["ceremony2/Hugo/session2_raw.edf"]
    else:
        raise ValueError("Invalid ceremony or participant.")

    # load data
    raw: mne.io.Raw = mne.concatenate_raws(
        [mne.io.read_raw_edf(join(expanduser(DATA_BASE), path)) for path in paths]
    )
    raw.load_data()

    # configure montage
    raw.drop_channels([ch for ch in raw.ch_names if ch.startswith("EEG X")])
    raw.set_channel_types(
        {ch: "eeg" if ch.startswith("EEG ") else "misc" for ch in raw.ch_names},
        on_unit_change="ignore",
    )
    raw.rename_channels(lambda x: x.replace("EEG ", "").replace("-Pz", ""))
    raw.drop_channels(["A1", "A2", "Pz", "CM", "Event"])
    raw.set_montage("standard_1020", on_missing="warn")

    # set reference
    raw.set_eeg_reference("average")

    # set annotations
    events = mne.find_events(raw, "Trigger")
    raw.set_annotations(mne.annotations_from_events(events, raw.info["sfreq"]))

    # apply filters
    if bandpass is not None:
        raw.filter(*bandpass, n_jobs=-1)
    if notch is not None:
        raw.notch_filter(np.arange(notch, raw.info["sfreq"] / 2, notch), n_jobs=-1)

    return raw


if __name__ == "__main__":
    load_eeg("second", "curandero")
