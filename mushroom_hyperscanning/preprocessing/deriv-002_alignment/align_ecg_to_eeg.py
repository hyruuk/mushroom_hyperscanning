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
    ecg_info = pd.read_csv(file_path_info)
    sfreq = ecg_info.loc[1, "samplingrate"]

    ecg_data = pd.read_csv(file_path)
    ecg_data.index /= sfreq  # Convert to seconds
    ecg_trigger = pd.read_csv(file_path_trigger)
    ecg_trigger.index /= sfreq  # Convert to seconds

    # remove offset from the data
    ecg_data = ecg_data[ecg_data.index > offset]
    ecg_trigger = ecg_trigger[ecg_trigger.index > offset]

    return ecg_data, ecg_trigger, sfreq


def align_ecg_to_eeg(root: str):
    ceremonies = {
        "ceremony1": {"subjs": ["02", "03"], "offset": 1000},
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

            # find triggers
            x = (ecg_trigger["ExG [2]-ch1"] < -350000).astype(float)
            # onset mean of first 5 triggers after offset
            ecg_onset = x[(x.shift(fill_value=0) == 0) & (x == 1)].index.values[:5].mean()

            if ecg_onset - curandero_onset < 0:
                # if ECG trigger is before curandero trigger, pad the data
                pad_duration = abs(ecg_onset - curandero_onset)
                pad_samples = int(np.ceil(pad_duration * sfreq))

                # Create padding dataframes
                pad_index = np.arange(0, pad_samples) / sfreq

                # Padding for ECG data
                ecg_data_pad = pd.DataFrame(data=np.zeros(pad_samples), columns=["ExG [1]-ch1"], index=pad_index)
                # Padding for ECG trigger
                ecg_trigger_pad = pd.DataFrame(data=np.zeros(pad_samples), columns=["ExG [2]-ch1"], index=pad_index)

                # Shift original ECG indexes forward by pad_duration
                ecg_data.index += pad_duration
                ecg_trigger.index += pad_duration

                # Concatenate padding and original data
                ecg_data = pd.concat([ecg_data_pad, ecg_data])
                ecg_trigger = pd.concat([ecg_trigger_pad, ecg_trigger])
            else:
                # if ECG trigger is after curandero trigger, align the data to start at the same time
                ecg_data = ecg_data[ecg_data.index > (ecg_onset - curandero_onset)]
                ecg_data.index -= ecg_data.index[0]
                ecg_trigger = ecg_trigger[ecg_trigger.index > (ecg_onset - curandero_onset)]
                ecg_trigger.index -= ecg_trigger.index[0]

            # interpolate ECG to match EEG sampling rate
            new_times = curandero_eeg.times if subj == "02" else subject_eeg.times
            ecg_data = np.interp(new_times, ecg_data.index, ecg_data["ExG [1]-ch1"].values)
            ecg_trigger = np.interp(new_times, ecg_trigger.index, ecg_trigger["ExG [2]-ch1"].values)

            if subj not in ["01", "02"]:
                # invert ECG data for subjects 03 and 04
                ecg_data *= -1

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
