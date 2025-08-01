"""
1. Align the audio to the EEG data. (TODO: crude timings for now due to missing audio triggers)
2. Merge ECG and EEG data.
"""

from .align_audio_to_eeg import align_audio_to_eeg
from .align_ecg_to_eeg import align_ecg_to_eeg


def main(derivative_dir: str):
    # align audio to EEG
    align_audio_to_eeg(derivative_dir)
    # align ECG and EEG data
    align_ecg_to_eeg(derivative_dir)
