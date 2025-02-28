# Audio Resegmenter

Audio Resegmenter segments long audio files based on a provided transcription file. Each line of the transcription is force-aligned to the input audio. The tool outputs a YAML file in the same format as the MuST-C dataset's YAML files, for example:

```
- {duration: 2.818, offset: 0.59, speaker_id: rec1, wav: rec1.wav}
- {duration: 6.122, offset: 3.959, speaker_id: rec1, wav: rec1.wav}
```

## Installation

```
python setup.py install
```

## Usage

First, run WhisperX to obtain transcriptions with timestamps:

```
whisperx --language $LANG $WAV_FILE
```

This will produce a JSON file `${WAV_FILE%.*}.json` containing transcriptions and timestamps.
Next, run the resegmenter tool. It expects a list of WAV files. Each WAV file should have an accompanying JSON file produced in the previous step (`${WAV_FILE%.*}.json`) and a TXT file containing the transcript to be forced-aligned (`${WAV_FILE%.*}.txt`). The tool will automatically locate the JSON and TXT files.

```
audio_resegmenter $WAV_FILE ${WAV_FILE%.*}.segments.yaml
```

Arguments:
- `input_wavs`: A list of WAV files to be resegmented; each file must have an accompanying JSON file with the same name.
- `output_yaml`: The YAML file to output the alignments.
- `--language`: [default = en] The language of the audio (see WhisperX for supported languages).
- `--device`: The device on which to run the audio model.
- `--dump_audio_dir`: [Optional] The path where the audio segments will be saved.
- `--extra_context`: [default = 3] The number of extra words to use during the final alignment.
