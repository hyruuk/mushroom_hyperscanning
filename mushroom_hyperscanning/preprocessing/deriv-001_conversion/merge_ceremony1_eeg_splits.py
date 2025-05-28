import os

import mne
import numpy as np
import pandas as pd
from mne import io
from mne_bids import BIDSPath


def load_eeg(sub, ceremony, root):
    paths = BIDSPath(
        subject=sub,
        session=ceremony,
        task="psilo",
        datatype="eeg",
        root=root,
    ).match()

    raws = [io.read_raw(path, preload=True) for path in paths]
    return paths, raws


def concatenate_raws_with_offsets(raws, gap_durations, trigger_offsets) -> mne.io.Raw:
    raws_with_gaps = []
    n_annotations = []
    for i, raw in enumerate(raws):
        raws_with_gaps.append(mne.io.RawArray(raw.get_data(), raw.info.copy()))

        annot = raw.annotations.copy()
        n_annotations.append(len(annot))
        raws_with_gaps[-1].set_annotations(annot)

        if i < len(raws) - 1:
            gap_samples = int(np.round(gap_durations[i] * raw.info["sfreq"])) - 1
            gap_data = np.full((raw.info["nchan"], gap_samples), 0)
            gap_info = raw.info.copy()
            gap_raw = mne.io.RawArray(gap_data, gap_info)
            raws_with_gaps.append(gap_raw)

    out = mne.concatenate_raws(raws_with_gaps)

    cumulative_offset = 0
    for i, n in enumerate(n_annotations):
        if i == 0:
            cumulative_offset += n + 4
            continue
        out.annotations.onset[cumulative_offset : cumulative_offset + n] -= np.cumsum(trigger_offsets[1:])[i - 1]
        cumulative_offset += n + 4

    return out


def merge_ceremony1_eeg_splits(root: str):
    """
    Merges individudal EEG recordings of the ceremony1 task for subjects 3 and aligns them to the recording of subject 1.
    The recording of subject 3 cut out several times during the ceremony, so we need to align the recordings to the
    alignment triggers of subject 1. This function will merge and align the data and store the aligned data for subject 3
    in a single edf file. It also removes the original data chunks for subject 3.

    Parameters
    ----------
    root : str
        Path to the root of the derivative BIDS dataset.
    """
    sub1_paths, sub1_raw = load_eeg("01", "ceremony1", root)
    sub3_paths, sub3_raw = load_eeg("03", "ceremony1", root)

    # print measurement data and duration for each file from sub1
    print("subject 1")
    for p, r in zip(sub1_paths, sub1_raw):
        duration = r.times[-1] - r.times[0]
        print(
            str(p).split("/")[-1],  # filename
            r.info["meas_date"],  # measurement date
            f"{int(duration//3600):02d}:{int((duration%3600)//60):02d}:{int(duration%60):02d}",  # duration in HH:MM:SS
            sep="\t",
        )

    # print measurement data and duration for each file from sub3
    print("\nsubject 3")
    for p, r in zip(sub3_paths, sub3_raw):
        duration = r.times[-1] - r.times[0]
        print(
            str(p).split("/")[-1],  # filename
            r.info["meas_date"],  # measurement date
            f"{int(duration//3600):02d}:{int((duration%3600)//60):02d}:{int(duration%60):02d}",  # duration in HH:MM:SS
            sep="\t",
        )

    # Display aligned timestamps of triggers for both subjects

    r = sub1_raw[0]
    onset_times = (r.annotations.onset[r.annotations.description == "1"] / 60).tolist()
    meas_date = r.info["meas_date"]

    # Offset by the measurement date
    offset_times = [meas_date + pd.to_timedelta(time, unit="m") for time in onset_times]

    formatted_times = [f"{time.strftime('%Y-%m-%d %H:%M:%S')}" for time in offset_times]
    {i: t for i, t in enumerate(formatted_times)}

    for r in sub3_raw:
        onset_times = (r.annotations.onset[r.annotations.description == "1"] / 60).tolist()
        meas_date = r.info["meas_date"]

        # Offset by the measurement date
        offset_times = [meas_date + pd.to_timedelta(time, unit="m") for time in onset_times]

        formatted_times = [f"{time.strftime('%Y-%m-%d %H:%M:%S')}" for time in offset_times]
        print(formatted_times)

    # Select the synchronization triggers to keep for alignment

    # sub1_indices = [[0, 3, 8, 12, 13, 14, 15, 16, 17]] # keep
    sub1_indices = [[1, 2, 4, 5, 6, 7, 9, 10, 11]]  # discard
    # sub3_indices = [[0], [0], [0], [0], [0], [0], [0], [0], [0]] # keep
    sub3_indices = [[1, 2, 3, 4, 5, 6, 7, 8], [], [], [], [], [], [], [], []]  # discard

    # discard unused synchronization triggers from sub1
    sub1_raw_aligned = sub1_raw[0].copy()
    annot1 = sub1_raw_aligned.annotations
    keep_idxs = np.where(annot1.description == "1")[0][sub1_indices[0]]
    mask = np.zeros(len(annot1), dtype=bool)
    mask[keep_idxs] = True
    sub1_raw_aligned.set_annotations(annot1[~mask])

    print("trigger times:")
    print(sub1_raw_aligned.annotations.onset[sub1_raw_aligned.annotations.description == "1"].tolist())

    # discard unused synchronization triggers for sub3
    sub3_raw_aligned = sub3_raw[0].copy()
    annot1 = sub3_raw_aligned.annotations
    keep_idxs = np.where(annot1.description == "1")[0][sub3_indices[0]]
    mask = np.zeros(len(annot1), dtype=bool)
    mask[keep_idxs] = True
    sub3_raw_aligned.set_annotations(annot1[~mask])
    sub3_raw_aligned = [sub3_raw_aligned] + sub3_raw[1:]

    print("trigger times:")
    for r in sub3_raw_aligned:
        print(r.annotations.onset[r.annotations.description == "1"].tolist())

    # Calculate the duration of missing data (gap) between sub3 recordings

    annot1 = sub1_raw_aligned.annotations
    times1 = annot1.onset[annot1.description == "1"]
    diffs = times1[1:] - times1[:-1]

    duration_after_trigger3 = []
    trigger_offsets = []
    for i, r in enumerate(sub3_raw_aligned):
        annot3 = r.annotations
        time3 = annot3.onset[annot3.description == "1"]
        duration3 = r.times[-1] - r.times[0]
        duration_after_trigger3.append(duration3 - time3)
        trigger_offsets.append(time3.item())

    gap_durations = (np.array(diffs) - np.array(duration_after_trigger3).squeeze()[:-1]).tolist()

    print("gap durations and trigger offsets:")
    list(zip(gap_durations, trigger_offsets))

    # Align individual recordings of sub3 to sub1 recording

    sub3_concatenated = concatenate_raws_with_offsets(sub3_raw_aligned, gap_durations, trigger_offsets)

    # make sure the trigger timings are aligned between the two subjects
    assert np.allclose(
        np.array(sub3_concatenated.annotations.onset[sub3_concatenated.annotations.description == "1"]),
        np.array(sub1_raw_aligned.annotations.onset[sub1_raw_aligned.annotations.description == "1"]),
    )

    # save the aligned data for sub3
    path: BIDSPath = sub3_paths[0].copy()
    path.split = None
    mne.export.export_raw(path.fpath, sub3_concatenated)

    # remove the original data for sub3
    for path in sub3_paths:
        os.remove(path.fpath)
