#!/usr/bin/env zsh

# Function to record audio and transcribe with Whisper
record_and_transcribe() {
  # Defaults
  local DEFAULT_INPUT="alsa_input.pci-0000_00_1f.3.analog-stereo"
  local DEFAULT_OUTPUT="alsa_input.pci-0000_00_1f.3.analog-stereo.monitor"
  local DEFAULT_FILENAME="$(date +%Y%m%d_%H%M%S).wav"

  # Initialize variables
  local FILENAME="$DEFAULT_FILENAME"
  local INPUT_DEVICE="$DEFAULT_INPUT"
  local OUTPUT_DEVICE="$DEFAULT_OUTPUT"

  # Parse arguments
  while [[ $# -gt 0 ]]; do
    case $1 in
      -filename)
        FILENAME="$2"
        shift 2
        ;;
      -input-device)
        INPUT_DEVICE="$2"
        shift 2
        ;;
      -output-device)
        OUTPUT_DEVICE="$2"
        shift 2
        ;;
      *)
        echo "❌ Unknown option: $1"
        echo "Usage: record_whisper [-filename <output.wav>] [-input-device <input>] [-output-device <output.monitor>]"
        return 1
        ;;
    esac
  done

  echo "🎤 Recording to: $FILENAME"
  echo "🎧 Input device: $INPUT_DEVICE"
  echo "🔊 Output device: $OUTPUT_DEVICE"

  # Load PulseAudio modules
  pactl load-module module-null-sink sink_name=CombinedOutput
  pactl load-module module-loopback source="$OUTPUT_DEVICE" sink=CombinedOutput
  pactl load-module module-loopback source="$INPUT_DEVICE" sink=CombinedOutput

  # Cleanup function
  local cleanup() {
    echo "🔄 Unloading PulseAudio modules..."
    pactl unload-module module-null-sink
    pactl unload-module module-loopback || true
    echo "📝 Transcribing with Whisper..."
    whisper "$FILENAME" --model small --language English --output_dir "$(dirname "$FILENAME")" --device cpu
  }

  # Register cleanup on exit
  TRAPEXIT() {
    cleanup
  }

  # Start recording# ZSH Plugin: record-whisper.zsh
  # Place this file in ~/.oh-my-zsh/custom/plugins/record-whisper/record-whisper.plugin.zsh
  echo "🎬 Recording started. Press CTRL+C to stop..."
  parec --format=s16le --rate=44100 --channels=2 --device=CombinedOutput.monitor | ffmpeg -f s16le -ar 44100 -ac 2 -i - "$FILENAME"
}
