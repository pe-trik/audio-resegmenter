# Audio Resegmenter

The **Audio Resegmenter** is designed to align a specific "golden" transcript (text pre-segmented into desired lines) with its corresponding audio file. 

The goal is to calculate precise start and end timestamps for every line in the text file, effectively forcing the audio to match the specific segmentation.

## Workflow
The tool operates using a **coarse-to-fine** alignment strategy. It first performs a rough text-to-text alignment to estimate where each line of the golden transcript occurs in the audio. Then, it refines these estimates using a forced-alignment step that considers both the audio and the expanded text context.

### Prerequisites (Input Loading)

The tool requires three inputs:
- **Raw Audio**: source recording (.wav)  
- **Golden Transcript**: target text pre-segmented into lines (.txt)  
- **ASR Output**: WhisperX JSON with initial word-level timestamps (.json)

### Pass 1: Coarse Alignment (Text-to-Text)

- Use a global sequence alignment (Needleman–Wunsch via pairwise2) to align the golden transcript to the ASR transcript.  
- Matching is based on character overlap/similarity between words.  
- Transfer timestamps from matched ASR words to the corresponding words in the golden transcript.  
- Result: approximate start/end times for each golden line derived from the ASR run.

### Context Expansion

- For each golden line, form an extended segment by padding the approximate time window with nearby context words (controlled by `--extra_context` with a default value of 3 words).  
- This yields an audio slice and an expanded text snippet including preceding and succeeding words.  
- *Purpose*: ASR transcriptions may not perfectly match the golden text, so the extra context helps ensure that the forced-alignment step has enough information to find the correct alignment.

### Pass 2: Forced Alignment (Audio-to-Text)

- Feed each extended segment (audio slice + expanded text) to the forced-alignment module (WhisperX using a Wav2Vec2/HuBERT-style model).  
- The model produces high-precision word timings within the extended segment.

### Final Refinement

- Remove timings for the added context words, keeping only timings that correspond to the original golden line.  
- Output: precise start and end timestamps for each golden line, suitable for the final YAML export.

### Output Format
The tool outputs a YAML file in the same format as the MuST-C dataset's YAML files, for example:

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
