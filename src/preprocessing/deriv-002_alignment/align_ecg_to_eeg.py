import os
import shutil
from os.path import join

import mne
import numpy as np
import pandas as pd
from utils import load_eeg, save_eeg


def load_custom_ecg(subject, session, bids_root, offset=0):
    # Construct the file path manually
    file_path = f"{bids_root}/sub-{subject}/ses-{session}/ecg/sub-{subject}_ses-{session}_task-psilo_ecg.csv"
    file_path_trigger = f"{bids_root}/sub-{subject}/ses-{session}/ecg/sub-{subject}_ses-{session}_task-psilo_ecg-trigger.csv"
    file_path_info = f"{bids_root}/sub-{subject}/ses-{session}/ecg/sub-{subject}_ses-{session}_task-psilo_info.csv"
    # Load the data
    ecg_data = pd.read_csv(file_path)
    ecg_trigger = pd.read_csv(file_path_trigger)

    ecg_data = ecg_data[ecg_data.index > offset]
    ecg_data.index = ecg_data.index - offset  # Adjust the index to start from 0
    ecg_trigger = ecg_trigger[ecg_trigger.index > offset]
    ecg_trigger.index = ecg_trigger.index - offset  # Adjust the index to start from 0

    ecg_info = pd.read_csv(file_path_info)
    sfreq = ecg_info.loc[1, "samplingrate"]
    return ecg_data, ecg_trigger, sfreq


def align_ecg_to_eeg(root: str):
    ceremonies = {
        "ceremony1": {"subjs": ["02", "03"], "offset": 2100},
        "ceremony2": {"subjs": ["02", "04"], "offset": 0},
    }

    for ceremony, info in ceremonies.items():
        curandero_eeg = load_eeg("01", ceremony, root)
        curandero_annot = curandero_eeg.annotations.to_data_frame(time_format="ms")
        curandero_annot["onset"] = curandero_annot["onset"] / 1000  # Convert to seconds
        curandero_ecg_triggers = curandero_annot[curandero_annot["description"] == "9"]
        curandero_onset = curandero_ecg_triggers["onset"].values.mean()

        for subj in info["subjs"]:
            if subj != "02":
                # load subject EEG data if available
                subject_eeg = load_eeg(subj, ceremony, root, preload=True)

            ecg_data, ecg_trigger, sfreq = load_custom_ecg(subj, ceremony, root, offset=info["offset"])
            ecg_trigger.index /= sfreq  # Convert to seconds

            # find triggers
            x = (ecg_trigger["ExG [2]-ch1"] < -350000).astype(float)
            ecg_onset = x[(x.shift(fill_value=0) == 0) & (x == 1)].index.values.mean()

            # align ECG data to EEG data
            ecg_data = ecg_data[ecg_data.index > (ecg_onset - curandero_onset)]

            # interpolate ECG to match EEG sampling rate
            new_times = curandero_eeg.times if subj == "02" else subject_eeg.times
            ecg_data = np.interp(new_times, ecg_data.index, ecg_data["ExG [1]-ch1"].values)

            ecg_raw = mne.io.RawArray(
                ecg_data.reshape(1, -1) / 1e9,
                mne.create_info(ch_names=["ECG"], ch_types=["ecg"], sfreq=curandero_eeg.info["sfreq"]),
            )

            if subj == "02":
                # save just ECG data for subject 02
                save_eeg(ecg_raw, subj, ceremony, root)
            else:
                # load subject EEG data
                subject_eeg.add_channels([ecg_raw])

                save_eeg(subject_eeg, subj, ceremony, root)

            # delete old ECG data
            shutil.rmtree(join(root, f"sub-{subj}", f"ses-{ceremony}", "ecg"))
