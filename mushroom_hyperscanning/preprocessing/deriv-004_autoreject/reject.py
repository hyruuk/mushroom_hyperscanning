import os
from os.path import dirname, join

import mne
import numpy as np
import pandas as pd
from autoreject import AutoReject
from mne import make_fixed_length_epochs
from mne.preprocessing import ICA, create_ecg_epochs, create_eog_epochs

from mushroom_hyperscanning.data import load_eeg, save_eeg


def reject(derivative_dir: str) -> None:
    ceremonies = {
        "ceremony1": ["01", "03"],
        # "ceremony2": ["01", "04"],
    }

    for ceremony, subs in ceremonies.items():
        for sub in subs:
            eeg = load_eeg(sub, ceremony, derivative_dir, preload=True)
            eeg.crop(tmin=60 * 30, tmax=60 * 90)  # TODO: REMOVE

            # Filter raw data
            raw_filtered = eeg.copy().filter(1, 90)
            raw_filtered = raw_filtered.copy().notch_filter(np.arange(60, raw_filtered.info["sfreq"] / 2, 60))

            # Segment signals in 1s epochs
            epochs = make_fixed_length_epochs(raw_filtered, duration=1.0, preload=True)

            # Run a first autoreject before ICA
            ar = AutoReject(n_jobs=-1)
            ar.fit(epochs)
            arlog = ar.get_reject_log(epochs)

            # Fit ICA without bad epochs
            ica = ICA(n_components=15, random_state=69, max_iter="auto")
            ica.fit(epochs[~arlog.bad_epochs])

            # # Find ECG components
            # ecg_threshold = 0.50
            # ecg_epochs = create_ecg_epochs(raw_filtered, ch_name="ECG")
            # ecg_inds, ecg_scores = ica.find_bads_ecg(ecg_epochs, ch_name="ECG", method="ctps", threshold=ecg_threshold)
            # if ecg_inds == []:
            #     ecg_inds = [list(abs(ecg_scores)).index(max(abs(ecg_scores)))]

            # # Find EOG components
            # eog_threshold = 2
            # eog_epochs = create_eog_epochs(raw_filtered, ch_name=["Fp1", "Fp2"])
            # eog_inds, eog_scores = ica.find_bads_eog(eog_epochs, ch_name=["Fp1", "Fp2"], threshold=eog_threshold)
            # if eog_inds == []:
            #     eog_inds = [list(abs(eog_scores)).index(max(abs(eog_scores)))]

            # Reconstruct raw without artifact components
            ica.exclude = []  # ecg_inds + eog_inds
            raw_clean = raw_filtered.copy()
            ica.apply(raw_clean)

            # Resegment and run autoreject on cleaned data
            epochs_clean = make_fixed_length_epochs(raw_clean, duration=1.0, preload=True)
            ar_clean = AutoReject(n_jobs=-1)
            ar_clean.fit(epochs_clean)
            arlog_clean = ar_clean.get_reject_log(epochs_clean)

            # Save results
            eeg_dir = join(derivative_dir, f"sub-{sub}", f"ses-{ceremony}", "eeg")
            os.makedirs(eeg_dir, exist_ok=True)
            raw_clean.save(join(eeg_dir, f"sub-{sub}_ses-{ceremony}_task-psilo_eeg.fif"), overwrite=True)
            epochs_clean.save(join(eeg_dir, f"sub-{sub}_ses-{ceremony}_task-psilo_epochs.fif"), overwrite=True)
            np.save(join(eeg_dir, f"sub-{sub}_ses-{ceremony}_task-psilo_rejectlog.npy"), arlog_clean.labels)

            for fname in eeg.filenames:
                os.remove(fname)
