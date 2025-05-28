"""
1. Convert triggers to annotations for all EEG files.
2. Merge individual EEG recordings of ceremony 1, sub-03 into a single file, aligned to the EEG from sub-01.
"""

from .convert_eeg import convert_eeg
from .merge_ceremony1_eeg_splits import merge_ceremony1_eeg_splits


def main(derivative_dir: str):
    # convert triggers to annotations for all EEG files
    convert_eeg(derivative_dir)
    # merge ceremony 1 EEG data of sub-03
    merge_ceremony1_eeg_splits(derivative_dir)
