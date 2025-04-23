import mne
from mne_bids import BIDSPath


def convert_eeg(root: str):
    """
    Convert triggers to annotations for all EEG files.
    """
    paths = BIDSPath(subject=".*", session=".*", task="psilo", datatype="eeg", root=root).match()
    for path in paths:
        raw = mne.io.read_raw(path)

        # find events and save as annotations
        events = mne.find_events(raw, "Trigger")
        raw.set_annotations(mne.annotations_from_events(events, raw.info["sfreq"]))

        # rename channels to standard names
        raw.rename_channels(lambda x: x.replace("EEG ", "").replace("-Pz", "").replace("X1:", ""))
        raw.set_channel_types({"ECG": "ecg"})

        # remove unused channels
        raw.drop_channels(["Trigger", "Event", "X2:", "X3:"])
        if path.subject != "01":
            # only subject 01 has the ECG channel in the EEG file
            raw.drop_channels(["ECG"])

        mne.export.export_raw(path, raw, overwrite=True)
