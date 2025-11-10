import mne
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.ticker import FuncFormatter


def extract_coherent_epochs(
    subj, ceremony, root, window_length, overlap=0.0, include_interpolated=True, max_bad_channels=0
):
    """
    Extract coherent chunks of data from 1-second epochs based on rejection criteria.

    Parameters
    ----------
    subj : int
        Subject number
    ceremony : str
        Ceremony name (e.g., 'ceremony1')
    root : str
        Root path to the data directory
    window_length : float
        Length of the output epochs in seconds
    overlap : float, optional
        Overlap between consecutive windows in seconds (default: 0.0)
    include_interpolated : bool, optional
        If True, include epochs with interpolated channels (reject value 2).
        If False, only include good epochs (reject value 0). Default: True
    max_bad_channels : int, optional
        Maximum number of bad channels allowed per epoch (default: 0)

    Returns
    -------
    new_epochs : mne.Epochs
        New epochs object with specified window length containing only coherent chunks
    """
    # Load data
    basepath = f"{root}/sub-{subj:02d}/ses-{ceremony}/eeg/sub-{subj:02d}_ses-{ceremony}_task-psilo_"
    epochs = mne.read_epochs(basepath + "epochs.fif")
    reject = np.load(basepath + "rejectlog.npy")

    # Get epoch duration (should be 1s based on description)
    epoch_duration = epochs.times[-1] - epochs.times[0] + 1 / epochs.info["sfreq"]

    # Calculate how many 1s epochs we need for the desired window length
    n_epochs_per_window = int(np.round(window_length / epoch_duration))

    # Calculate step size in epochs based on overlap
    step_size = int(np.round((window_length - overlap) / epoch_duration))
    if step_size < 1:
        step_size = 1

    # Determine valid epochs based on rejection criteria
    if include_interpolated:
        # Count bad channels per epoch (reject value 1 = bad)
        bad_channels_per_epoch = np.sum(reject == 1, axis=1)
    else:
        # Count both bad and interpolated channels (reject values 1 and 2)
        bad_channels_per_epoch = np.sum((reject == 1) | (reject == 2), axis=1)

    # Mark epochs as valid if they have <= max_bad_channels
    valid_epochs = bad_channels_per_epoch <= max_bad_channels

    # Find coherent chunks of valid epochs
    coherent_chunks = []
    i = 0
    while i <= len(valid_epochs) - n_epochs_per_window:
        # Check if we have n_epochs_per_window consecutive valid epochs
        if np.all(valid_epochs[i : i + n_epochs_per_window]):
            coherent_chunks.append(list(range(i, i + n_epochs_per_window)))
            i += step_size
        else:
            i += 1

    if len(coherent_chunks) == 0:
        print(f"Warning: No coherent chunks of length {window_length}s found!")
        # Return empty epochs object
        return epochs[0:0]

    print(f"Found {len(coherent_chunks)} coherent chunks of {window_length}s " f"(from {len(epochs)} 1s epochs)")

    # Get all epochs data once (faster than calling get_data in loop)
    all_epochs_data = epochs.get_data(copy=True)  # shape: (n_epochs, n_channels, n_times)

    # Stitch together the epochs for each coherent chunk
    new_epochs_data = []
    new_events = []

    for chunk_idx, chunk_indices in enumerate(coherent_chunks):
        # Get data for this chunk and concatenate along time axis
        chunk_data = all_epochs_data[chunk_indices]  # shape: (n_epochs_in_chunk, n_channels, n_times)
        stitched_data = chunk_data.reshape(chunk_data.shape[1], -1)  # (n_channels, n_epochs*n_times)
        new_epochs_data.append(stitched_data)

        # Create event for this new epoch (use time of first epoch in chunk)
        first_event = epochs.events[chunk_indices[0]]
        new_event = [first_event[0], 0, first_event[2]]  # Keep original event code
        new_events.append(new_event)

    # Stack all epochs
    new_epochs_data = np.array(new_epochs_data)  # (n_new_epochs, n_channels, n_times)
    new_events = np.array(new_events)

    # Create new epochs object
    new_epochs = mne.EpochsArray(
        new_epochs_data, epochs.info, events=new_events, tmin=epochs.times[0], event_id=epochs.event_id, verbose=False
    )

    return new_epochs


def find_epoch_intersection(epochs1, epochs2):
    """
    Find the intersection of two epochs objects based on onset times and durations.

    Parameters
    ----------
    epochs1 : mne.Epochs
        First epochs object
    epochs2 : mne.Epochs
        Second epochs object

    Returns
    -------
    epochs1_filtered : mne.Epochs
        Filtered version of epochs1 containing only epochs with matching onset and duration in epochs2
    epochs2_filtered : mne.Epochs
        Filtered version of epochs2 containing only epochs with matching onset and duration in epochs1
    """
    # Get onset times and durations for epochs1
    onset1 = epochs1.events[:, 0] / epochs1.info["sfreq"]  # Convert to seconds
    duration1 = epochs1.times[-1] - epochs1.times[0]

    # Get onset times and durations for epochs2
    onset2 = epochs2.events[:, 0] / epochs2.info["sfreq"]  # Convert to seconds
    duration2 = epochs2.times[-1] - epochs2.times[0]

    # Check if durations match (they should for intersection to make sense)
    if not np.isclose(duration1, duration2, rtol=1e-10):
        raise ValueError(f"Epoch durations don't match: {duration1:.3f}s vs {duration2:.3f}s")

    # Find matching epochs
    # An epoch matches if its onset time exists in the other epochs object
    matches1 = np.isin(onset1, onset2)
    matches2 = np.isin(onset2, onset1)

    # Filter epochs
    epochs1_filtered = epochs1[matches1]
    epochs2_filtered = epochs2[matches2]

    print(f"Epochs1: {len(epochs1)} -> {len(epochs1_filtered)} epochs kept")
    print(f"Epochs2: {len(epochs2)} -> {len(epochs2_filtered)} epochs kept")

    return epochs1_filtered, epochs2_filtered


def plot_epoch_distribution(chunks, figsize=(15, 4), color="steelblue", alpha=0.3):
    """
    Plot the temporal distribution of extracted coherent epochs.

    Parameters
    ----------
    chunks : mne.Epochs
        Epochs object containing the coherent chunks
    figsize : tuple, optional
        Figure size (width, height) in inches. Default: (15, 4)
    color : str, optional
        Color for the epoch shaded areas. Default: 'steelblue'
    alpha : float, optional
        Transparency of the shaded areas. Default: 0.3
    """
    # Create a plot showing the temporal distribution of extracted epochs
    fig, ax = plt.subplots(figsize=figsize)

    # Get the events and timing information from the new epochs
    for idx, event in enumerate(chunks.events):
        # Calculate start and end times
        start_time = event[0] / chunks.info["sfreq"]  # Convert samples to seconds
        end_time = start_time + (chunks.times[-1] - chunks.times[0])

        # Plot shaded area for this epoch (all same color)
        ax.axvspan(start_time, end_time, alpha=alpha, color=color)

    # Set labels and title
    ax.set_xlabel("Time (HH:MM:SS)", fontsize=12)
    ax.set_ylabel("Epochs", fontsize=12)
    ax.set_title(f"Temporal Distribution of Coherent Epochs (n={len(chunks)})", fontsize=14)
    ax.set_ylim(0, 1)
    ax.set_yticks([])

    # Format x-axis to show time in HH:MM:SS
    def format_time(x, pos):
        """Convert seconds to HH:MM:SS format"""
        hours = int(x // 3600)
        minutes = int((x % 3600) // 60)
        seconds = int(x % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    ax.xaxis.set_major_formatter(FuncFormatter(format_time))

    # Format x-axis to show time nicely
    ax.grid(True, alpha=0.3, axis="x")

    plt.tight_layout()
    plt.show()
