import mne
from mne_bids import BIDSPath


def convert_eeg(root: str):
    """
    Convert triggers to annotations for all EEG files.
    """
    paths = BIDSPath(subject=".*", session=".*", task="psilo", datatype="eeg", root=root).match()
    for path in paths:
        raw = mne.io.read_raw(path)

        events = mne.find_events(raw, "Trigger")
        raw.set_annotations(mne.annotations_from_events(events, raw.info["sfreq"]))

        mne.export.export_raw(path, raw, overwrite=True)
