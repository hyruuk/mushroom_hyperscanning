# Preprocessing pipeline
You can run the entire preprocessing pipeline by executing the `derivative_pipeline.py` script. This script will run the following steps:

<!-- DERIVATIVE_STEPS_AUTOGENERATE_START -->

## 001_conversion
1. Convert triggers to annotations for all EEG files.
2. Merge individual EEG recordings of ceremony 1, sub-03 into a single file, aligned to the EEG from sub-01.
## 002_alignment
1. Align the audio to the EEG data. (TODO)
2. Merge ECG and EEG data. (TODO)
## 003_sanitization
1. Clean triggers (TODO: ceremony 2)

<!-- DERIVATIVE_STEPS_AUTOGENERATE_END -->