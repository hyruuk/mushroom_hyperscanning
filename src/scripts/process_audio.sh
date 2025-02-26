#!/bin/bash

# Function to display help message
usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -i, --input-dir       Input directory containing .wav files (default: current directory)"
    echo "  -o, --output-dir      Output directory for the final mp3 files (default: input directory)"
    echo "  -a, --amplification   Volume amplification in dB (default: 14)"
    echo "  -c, --compression     Compression quality for mp3 (0-9, where 0 is highest quality, default: 0)"
    echo "  -h, --help            Display this help message"
    exit 1
}

# Default values
INPUT_DIR="."
OUTPUT_DIR=""
AMPLIFICATION_DB=14
COMPRESSION_QUALITY=0

# Parse command-line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -i|--input-dir)
            INPUT_DIR="$2"
            shift
            ;;
        -o|--output-dir)
            OUTPUT_DIR="$2"
            shift
            ;;
        -a|--amplification)
            AMPLIFICATION_DB="$2"
            shift
            ;;
        -c|--compression)
            COMPRESSION_QUALITY="$2"
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown parameter passed: $1"
            usage
            ;;
    esac
    shift
done

# If OUTPUT_DIR is not specified, use INPUT_DIR
if [ -z "$OUTPUT_DIR" ]; then
    OUTPUT_DIR="$INPUT_DIR"
fi

# Check if ffmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo "ffmpeg is not installed. Please install it using 'sudo apt install ffmpeg'."
    exit 1
fi

# Check if the input directory exists
if [ ! -d "$INPUT_DIR" ]; then
    echo "Input directory '$INPUT_DIR' does not exist."
    exit 1
fi

# Resolve absolute paths
INPUT_DIR=$(realpath "$INPUT_DIR")
OUTPUT_DIR=$(realpath "$OUTPUT_DIR")

echo "Processing .wav files in directory '$INPUT_DIR'..."
echo "Output directory is '$OUTPUT_DIR'"
echo "Volume amplification: ${AMPLIFICATION_DB}dB"
echo "Compression quality: $COMPRESSION_QUALITY"

# Create directories for left and right channel files inside a temp directory
TEMP_DIR=$(mktemp -d)
LEFT_DIR="$TEMP_DIR/main"
RIGHT_DIR="$TEMP_DIR/lavalier"
mkdir -p "$LEFT_DIR" "$RIGHT_DIR"

# Enable nullglob in case there are no .wav files
shopt -s nullglob

# Process each .wav file
found_wav_files=false
for wavfile in "$INPUT_DIR"/*.wav; do
    if [ ! -e "$wavfile" ]; then
        break
    fi
    found_wav_files=true
    base_name="$(basename "${wavfile%.wav}")"
    echo "Processing '$wavfile'..."

    # Extract left channel, amplify volume, save as mono .wav
    ffmpeg -i "$wavfile" -af "pan=mono|c0=FL,volume=${AMPLIFICATION_DB}dB" "$LEFT_DIR/${base_name}_main.wav"

    # Extract right channel, amplify volume, save as mono .wav
    ffmpeg -i "$wavfile" -af "pan=mono|c0=FR,volume=${AMPLIFICATION_DB}dB" "$RIGHT_DIR/${base_name}_lavalier.wav"
done

if [ "$found_wav_files" = false ]; then
    echo "No .wav files found in directory '$INPUT_DIR'."
    rm -rf "$TEMP_DIR"
    exit 1
fi

echo "Converting left channel .wav files to .mp3..."

# Convert left channel .wav files to .mp3
cd "$LEFT_DIR" || exit 1
for wavfile in *.wav; do
    mp3file="${wavfile%.wav}.mp3"
    ffmpeg -i "$wavfile" -q:a "$COMPRESSION_QUALITY" "$mp3file"
done

echo "Converting right channel .wav files to .mp3..."

# Convert right channel .wav files to .mp3
cd "$RIGHT_DIR" || exit 1
for wavfile in *.wav; do
    mp3file="${wavfile%.wav}.mp3"
    ffmpeg -i "$wavfile" -q:a "$COMPRESSION_QUALITY" "$mp3file"
done

echo "Merging left channel .mp3 files into a single file..."

# Merge left channel .mp3 files
cd "$LEFT_DIR" || exit 1
mp3files=(*.mp3)
IFS=$'\n' sorted_mp3files=($(sort <<<"${mp3files[*]}"))
unset IFS
rm -f files_left.txt
for f in "${sorted_mp3files[@]}"; do
    echo "file '$PWD/$f'" >> files_left.txt
done
ffmpeg -f concat -safe 0 -i files_left.txt -c copy "$OUTPUT_DIR/output_main.mp3"
rm files_left.txt

echo "Merging right channel .mp3 files into a single file..."

# Merge right channel .mp3 files
cd "$RIGHT_DIR" || exit 1
mp3files=(*.mp3)
IFS=$'\n' sorted_mp3files=($(sort <<<"${mp3files[*]}"))
unset IFS
rm -f files_right.txt
for f in "${sorted_mp3files[@]}"; do
    echo "file '$PWD/$f'" >> files_right.txt
done
ffmpeg -f concat -safe 0 -i files_right.txt -c copy "$OUTPUT_DIR/output_lavalier.mp3"
rm files_right.txt

echo "Cleaning up temporary files..."
rm -rf "$TEMP_DIR"

echo "Done! The merged files are named 'output_main.mp3' (left channel) and 'output_lavalier.mp3' (right channel) in directory '$OUTPUT_DIR'."
