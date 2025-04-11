"""
1. Merge individual EEG recordings of ceremony 1, sub-03 into a single file, aligned to the EEG from sub-01.
2. Align the audio to the EEG data. (TODO)
3. Merge ECG and EEG data. (TODO)
"""

from .align_audio_to_eeg import align_audio_to_eeg
from .align_ecg_to_eeg import align_ecg_to_eeg
from .merge_ceremony1_eeg_splits import merge_ceremony1_eeg_splits


def main(derivative_dir: str):
    # align ceremony 1 EEG data
    merge_ceremony1_eeg_splits(derivative_dir)
    # align audio to EEG
    align_audio_to_eeg(derivative_dir)
    # align ECG and EEG data
    align_ecg_to_eeg(derivative_dir)
