"""
1. Merge individual EEG recordings of ceremony 1, sub-03 into a single file, aligned to the EEG from sub-01.
2. Align the audio to the EEG data. (TODO)
3. Merge ECG and EEG data. (TODO)
"""

from .align_audio_to_eeg import align_audio_to_eeg
from .ceremony1_merge_eeg_splits import ceremony1_merge_eeg_splits


def main(derivative_dir: str):
    # align ceremony 1 EEG data
    ceremony1_merge_eeg_splits(derivative_dir)

    # align audio to EEG
    print("TODO")
    align_audio_to_eeg(derivative_dir)

    # merge ECG and EEG data
    print("TODO")
