from os.path import dirname, join

import mne
import pandas as pd

from mushroom_hyperscanning.data import load_eeg, save_eeg


def clean_triggers(derivative_dir: str) -> None:
    """
    Clean triggers (TODO: ceremony 2)

    Parameters
    ----------
    derivative_dir : str
        Path to the derivative directory
    """
    ceremonies = {
        "ceremony1": ["01", "03"],
        # "ceremony2": ["01", "04"],  # TODO: add ceremony 2
    }

    cdir = dirname(__file__)
    for ceremony, subs in ceremonies.items():
        annot = pd.read_csv(join(cdir, f"triggers-{ceremony}.csv"))

        for sub in subs:
            eeg = load_eeg(sub, ceremony, derivative_dir, preload=True)
            new_annot = mne.Annotations(annot["onset"].values / 1000, annot["duration"].values, annot["description"].values)
            eeg = eeg.set_annotations(new_annot)
            save_eeg(eeg, sub, ceremony, derivative_dir)
