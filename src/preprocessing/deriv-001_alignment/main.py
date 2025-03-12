"""
Merge individual EEG recordings of ceremony 1, sub-03 into a single file, aligned to the EEG from sub-01.
"""

import sys
from os.path import abspath, dirname

sys.path.append(dirname(dirname(abspath(__file__))))

from bids_utils import PrintBlock, create_derivative_directory

BIDS_ROOT = "data/bids_dataset"
print(abspath(__file__))

# create derivative directory for alignment
derivative_dir = create_derivative_directory("001_alignment", BIDS_ROOT, overwrite=True)

# align ceremony 1 EEG data
with PrintBlock("Aligning ceremony 1 EEG data"):
    from ceremony1_merge_eeg_splits import ceremony1_merge_eeg_splits

    ceremony1_merge_eeg_splits(derivative_dir)

# align audio to EEG
with PrintBlock("Aligning audio to EEG"):
    from align_audio_to_eeg import align_audio_to_eeg

    print("TODO")
    align_audio_to_eeg(derivative_dir)

# merge ECG and EEG data
with PrintBlock("Merging ECG and EEG"):
    print("TODO")
