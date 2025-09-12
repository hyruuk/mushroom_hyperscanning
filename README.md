# mushroom_hyperscanning
Preprocessing code for the hyperscanning data acquired in Mexico during mushroom ceremonies

## Installation
1. **Clone the repository and cd into it:**
    ```
    git clone git@github.com:hyruuk/mushroom_hyperscanning.git
    cd mushroom_hyperscanning
    ```
2. **Install the mushroom hyperscanning package:**
    ```
    pip install -e .
    ```
3. **Install ffmpeg for audio file manipulation:**\
    Windows:
    ```
    winget install ffmpeg
    ```
    Linux:
    ```
    sudo apt-get install ffmpeg
    ```


## Run preprocessing pipeline
To run the preprocessing pipeline, and create the `deriv-00x-*` directories with derivative data, run this command:
```python
python mushroom_hyperscanning/scripts/preprocess.py
```
Use the `--overwrite` flag to overwrite existing derivatives.

## Loading EEG data
Load raw EEG data using the `load_eeg` function and specifying 
```python
from mushroom_hyperscanning.data import load_eeg

raw = load_eeg(subject="01", ceremony="ceremony1", root="path/to/derivative-directory")
```