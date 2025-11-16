import os
from os.path import dirname, join
import mne
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from autoreject import AutoReject
from mne import make_fixed_length_epochs
from mne.preprocessing import ICA, create_ecg_epochs, create_eog_epochs
from mne import Report
import io
import sys
from contextlib import redirect_stdout, redirect_stderr

from mushroom_hyperscanning.data import load_eeg, save_eeg
import pickle


def detect_zero_epochs(epochs):
    """
    Detect epochs with zeros on multiple channels.

    Parameters:
    epochs : mne.Epochs
        The epochs object to analyze

    Returns:
    numpy.ndarray
        Array of epoch indices that contain zeros on multiple channels
    """
    zero_epochs = []
    data = epochs.get_data()  # shape: (n_epochs, n_channels, n_times)

    for epoch_idx in range(data.shape[0]):
        epoch_data = data[epoch_idx]

        # Check each time point for zeros across channels
        for time_idx in range(epoch_data.shape[1]):
            time_point = epoch_data[:, time_idx]
            zero_channels = np.sum(time_point == 0)

            # If multiple channels have zeros at the same time point
            if zero_channels > 1:
                zero_epochs.append(epoch_idx)
                break  # Found zeros in this epoch, move to next epoch
    return np.array(zero_epochs)


def plot_rejection_proportions(data, ch_names):
    """
    Create a stacked bar plot showing the proportion of rejection status per channel.

    Parameters:
    data : numpy.ndarray
        2D array where rows are epochs and columns are channels.
        Values should be 0 (good), 1 (bad), or 2 (interpolated).
    """
    # Convert to DataFrame with channel names
    data_df = pd.DataFrame(data, columns=ch_names)

    # Melt the dataframe to long format
    data_melted = data_df.melt(var_name="Channel", value_name="Rejection Status")

    # Calculate proportions for each channel and rejection status
    proportions = (
        data_melted.groupby(["Channel", "Rejection Status"])
        .size()
        .unstack(fill_value=0)
    )
    proportions = proportions.div(proportions.sum(axis=1), axis=0)

    # Reorder columns to 0, 2, 1 and rename them
    proportions = proportions[[0.0, 2.0, 1.0]]
    proportions.columns = ["Good", "Interpolated", "Bad"]

    # Create stacked bar plot without showing
    plt.figure(figsize=(20, 5))
    proportions.plot(
        kind="bar", stacked=True, ax=plt.gca(), color=["green", "orange", "red"]
    )
    plt.xticks(rotation=90)
    plt.title("Proportion of Rejection Status per Channel")
    plt.ylabel("Proportion")
    plt.legend(title="Rejection Status")
    # Don't show the plot

    return proportions


def reject(derivative_dir: str) -> None:
    ceremonies = {
        # "ceremony1": ["01", "03"],
        "ceremony2": ["04"],  # ["01", "04"],
    }

    for ceremony, subs in ceremonies.items():
        for sub in subs:
            # Capture terminal output while still displaying it
            output_capture = io.StringIO()

            class TeeOutput:
                def __init__(self, *files):
                    self.files = files

                def write(self, text):
                    for f in self.files:
                        f.write(text)
                        f.flush()

                def flush(self):
                    for f in self.files:
                        f.flush()

            # Create MNE Report
            report = Report(
                verbose=True, title=f"Preprocessing Report - Sub-{sub} Ses-{ceremony}"
            )

            # Redirect output to both terminal and capture
            tee_stdout = TeeOutput(sys.stdout, output_capture)
            tee_stderr = TeeOutput(sys.stderr, output_capture)

            with redirect_stdout(tee_stdout), redirect_stderr(tee_stderr):
                eeg = load_eeg(sub, ceremony, derivative_dir, preload=True)
                # Crop to first 20 minutes for faster processing (remove in production)
                # eeg.crop(tmin=60 * 5, tmax=60 * 10)

                # Add raw data plots to report
                fig_raw_ts = eeg.plot(duration=30, n_channels=30, show=False)
                fig_raw_psd = eeg.compute_psd().plot(show=False)
                report.add_figure(
                    fig_raw_ts, title="Raw Time Series", section="Raw Data"
                )
                report.add_figure(
                    fig_raw_psd, title="Raw Power Spectral Density", section="Raw Data"
                )
                plt.close(fig_raw_ts)
                plt.close(fig_raw_psd)

                # Filter raw data
                raw_filtered = eeg.copy().filter(1, 90)
                raw_filtered = raw_filtered.copy().notch_filter(
                    np.arange(60, raw_filtered.info["sfreq"] / 2, 60)
                )

                # Add filtered data plots to report
                fig_filt_ts = raw_filtered.plot(duration=30, n_channels=30, show=False)
                fig_filt_psd = raw_filtered.compute_psd().plot(show=False)
                report.add_figure(
                    fig_filt_ts, title="Filtered Time Series", section="Filtered Data"
                )
                report.add_figure(
                    fig_filt_psd,
                    title="Filtered Power Spectral Density",
                    section="Filtered Data",
                )
                plt.close(fig_filt_ts)
                plt.close(fig_filt_psd)

                # Segment signals in 1s epochs
                epochs = make_fixed_length_epochs(
                    raw_filtered, duration=1.0, preload=True
                )
                print("==================================")
                print(
                    f"Sub-{sub} Ses-{ceremony} - Total epochs before rejection: {len(epochs)}"
                )
                zero_epochs = detect_zero_epochs(epochs)
                print(
                    f"Detected {len(zero_epochs)} epochs with zeros on multiple channels."
                )
                epochs = epochs[~np.isin(np.arange(len(epochs)), zero_epochs)]

                # Run a first autoreject before ICA
                ar = AutoReject(
                    n_jobs=-1,
                    n_interpolate=[4],
                    consensus=[0.8],
                    verbose=True,
                )
                ar.fit(epochs)
                arlog = ar.get_reject_log(epochs)

                # Add first autoreject results to report
                fig, ax = plt.subplots(figsize=(20, 15))
                arlog.plot("horizontal", ax=ax, show=False)
                report.add_figure(
                    fig, title="First AutoReject Log", section="First AutoReject"
                )
                plt.close(fig)

                # Fit ICA without bad epochs
                ica = ICA(
                    n_components=15, random_state=69, max_iter="auto", verbose=True
                )
                ica.fit(epochs[~arlog.bad_epochs])

                # Add ICA components to report
                fig_ica_comp = ica.plot_components(show=False)
                fig_ica_sources = ica.plot_sources(epochs, show=False)
                report.add_figure(
                    fig_ica_comp,
                    title="ICA Components Spatial Distribution",
                    section="ICA",
                )
                report.add_figure(
                    fig_ica_sources, title="ICA Components Time Series", section="ICA"
                )
                plt.close(fig_ica_comp)
                plt.close(fig_ica_sources)

                # Find ECG components
                ecg_threshold = 0.50
                ecg_epochs = create_ecg_epochs(raw_filtered, ch_name="ECG")
                ecg_inds, ecg_scores = ica.find_bads_ecg(
                    ecg_epochs, ch_name="ECG", method="ctps", threshold=ecg_threshold
                )
                if ecg_inds == []:
                    ecg_inds = [list(abs(ecg_scores)).index(max(abs(ecg_scores)))]

                # Find EOG components
                eog_threshold = 2
                eog_epochs = create_eog_epochs(raw_filtered, ch_name=["Fp1", "Fp2"])
                eog_inds, eog_scores = ica.find_bads_eog(
                    eog_epochs, ch_name=["Fp1", "Fp2"], threshold=eog_threshold
                )
                eog_scores = np.mean(np.abs(eog_scores), axis=0)
                if eog_inds == []:
                    # Average EOG scores across channels
                    eog_inds = [list(abs(eog_scores)).index(max(abs(eog_scores)))]

                # Add ECG/EOG component properties to report
                ecg_props_text = f"ECG Components: {ecg_inds}\nECG Scores: {ecg_scores[ecg_inds] if len(ecg_inds) > 0 else 'N/A'}\nThreshold: {ecg_threshold}"
                eog_props_text = f"EOG Components: {eog_inds}\nEOG Scores: {eog_scores[eog_inds] if len(eog_inds) > 0 else 'N/A'}\nThreshold: {eog_threshold}"

                if ecg_inds:
                    fig_ecg = ica.plot_properties(
                        ecg_epochs, picks=ecg_inds, show=False
                    )
                    report.add_figure(
                        fig_ecg,
                        title="ECG Component Properties",
                        section="Artifact Components",
                    )
                    # Close all figures in the list
                    if isinstance(fig_ecg, list):
                        for fig in fig_ecg:
                            plt.close(fig)
                    else:
                        plt.close(fig_ecg)

                if eog_inds:
                    fig_eog = ica.plot_properties(
                        eog_epochs, picks=eog_inds, show=False
                    )
                    report.add_figure(
                        fig_eog,
                        title="EOG Component Properties",
                        section="Artifact Components",
                    )
                    # Close all figures in the list
                    if isinstance(fig_eog, list):
                        for fig in fig_eog:
                            plt.close(fig)
                    else:
                        plt.close(fig_eog)

                report.add_html(
                    f"<h3>ECG Component Information</h3><pre>{ecg_props_text}</pre>",
                    title="ECG Info",
                    section="Artifact Components",
                )
                report.add_html(
                    f"<h3>EOG Component Information</h3><pre>{eog_props_text}</pre>",
                    title="EOG Info",
                    section="Artifact Components",
                )

                # Reconstruct raw without artifact components
                print(
                    f"Sub-{sub} Ses-{ceremony} - ECG components: {ecg_inds}, EOG components: {eog_inds}"
                )
                ica.exclude = ecg_inds + eog_inds
                raw_clean = raw_filtered.copy()
                ica.apply(raw_clean)

                # Resegment and run autoreject on cleaned data
                epochs_clean = make_fixed_length_epochs(
                    raw_clean, duration=1.0, preload=True
                )
                epochs_clean = epochs_clean[
                    ~np.isin(np.arange(len(epochs_clean)), zero_epochs)
                ]

                ar_clean = AutoReject(
                    n_jobs=-1, n_interpolate=[4], consensus=[0.8], verbose=True
                )
                epochs_clean = ar_clean.fit_transform(epochs_clean)

                arlog_clean = ar_clean.get_reject_log(epochs_clean)

                # Add second autoreject results to report
                fig, ax = plt.subplots(figsize=(20, 15))
                arlog_clean.plot("horizontal", ax=ax, show=False)
                report.add_figure(
                    fig, title="Second AutoReject Log", section="Final AutoReject"
                )
                plt.close(fig)

                # Add rejection proportions plot
                proportions = plot_rejection_proportions(
                    arlog_clean.labels, epochs_clean.ch_names
                )
                fig_prop = plt.gcf()
                report.add_figure(
                    fig_prop,
                    title="Rejection Proportions by Channel",
                    section="Final AutoReject",
                )
                plt.close(fig_prop)

                print("==================================")
                print(
                    f"Sub-{sub} Ses-{ceremony} - Total epochs after rejection: {len(epochs_clean)}/{len(epochs)}"
                )

            # Add terminal output to report
            terminal_output = output_capture.getvalue()
            report.add_html(
                f"<h2>Terminal Output</h2><pre>{terminal_output}</pre>",
                title="Terminal Output",
                section="Processing Log",
            )

            # Save results
            eeg_dir = join(derivative_dir, f"sub-{sub}", f"ses-{ceremony}", "eeg")
            os.makedirs(eeg_dir, exist_ok=True)

            # Save report as HTML without opening
            report_path = join(
                eeg_dir,
                f"sub-{sub}_ses-{ceremony}_task-psilo_preprocessing-report.html",
            )
            report.save(report_path, overwrite=True, open_browser=False)

            raw_clean.save(
                join(eeg_dir, f"sub-{sub}_ses-{ceremony}_task-psilo_eeg.fif"),
                overwrite=True,
            )
            epochs_clean.save(
                join(eeg_dir, f"sub-{sub}_ses-{ceremony}_task-psilo_epochs.fif"),
                overwrite=True,
            )
            with open(
                join(eeg_dir, f"sub-{sub}_ses-{ceremony}_task-psilo_rejectlog.pkl"),
                "wb",
            ) as f:
                pickle.dump(arlog_clean, f)

            for fname in eeg.filenames:
                os.remove(fname)
