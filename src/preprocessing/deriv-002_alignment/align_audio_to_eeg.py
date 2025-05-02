import os

import numpy as np
from pydub import AudioSegment
from utils import load_audio, load_eeg


def align_audio_to_eeg(root: str):
    # audio offsets hardcoded based on manual inspection currently contains a random offset
    # TODO: reconstruct exact audio timings
    ceremonies = {"ceremony1": 1724, "ceremony2": 96}

    for ceremony, audio_trigger_offset in ceremonies.items():
        # load EEG
        curandero_eeg = load_eeg("01", ceremony, root)
        curandero_annot = curandero_eeg.annotations.to_data_frame(time_format="ms")
        curandero_annot["onset"] = curandero_annot["onset"] / 1000  # Convert to seconds
        curandero_audio_triggers = curandero_annot[curandero_annot["description"] == "8"]
        curandero_trigger_onset = curandero_audio_triggers["onset"].values[-1]

        # load audio
        audio_path = os.path.join(root, "audio", f"ses-{ceremony}", f"audio_ses-{ceremony}_task-psilo_audio.mp3")

        # Load the MP3 file
        print("Loading audio file...", end="", flush=True)
        audio, audio_rate = load_audio(ceremony, root)
        print("done")

        print(f"Audio duration: {audio.shape[0] / audio_rate:.2f} seconds")

        # cut audio to start at the same time as EEG
        audio_start = audio_trigger_offset - curandero_trigger_onset
        audio_start = int(audio_start * audio_rate)
        if audio_start < 0:
            # pad the beginning of the audio with silence
            silence = np.zeros(-audio_start, dtype=audio.dtype)
            audio = np.concatenate([silence, audio])
            audio_start = 0

        audio_end = audio_start + int(curandero_eeg.times[-1] * audio_rate)
        if audio_end > audio.shape[0]:
            # pad the end of the audio with silence
            silence = np.zeros(audio_end - audio.shape[0], dtype=audio.dtype)
            audio = np.concatenate([audio, silence])

        # cut audio to the same length as EEG
        audio = audio[audio_start : audio_start + int(curandero_eeg.times[-1] * audio_rate)]

        print(f"Audio duration after cutting/padding: {audio.shape[0] / audio_rate:.2f} seconds")
        print(f"EEG duration: {curandero_eeg.times[-1]:.2f} seconds")

        # save audio
        audio = AudioSegment(audio.tobytes(), frame_rate=audio_rate, sample_width=audio.dtype.itemsize, channels=1)
        audio.export(audio_path, format="mp3")
