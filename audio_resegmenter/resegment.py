import json
import argparse
import os
from typing import List

from Bio import pairwise2
import yaml

from whisperx.types import SingleSegment, SingleWordSegment
from whisperx.alignment import align, load_align_model, load_audio


class SingleSegmentExtended(SingleSegment):
    words: List[SingleWordSegment] = []
    orig_text: str = ""
    l_extend: int = 0
    r_extend: int = 0


def load_words_from_json(json_file):
    with open(json_file, 'r', encoding='utf-8') as f:
        file_content = f.read().strip()
        data = json.loads(file_content)

    words = []
    for segment in data['segments']:
        words.extend(segment['words'])

    for i, word in enumerate(words):
        if "start" not in word:
            if i == 0:
                word['start'] = 0
            else:
                word['start'] = words[i - 1]['end']
        if "end" not in word:
            if i == len(words) - 1:
                word['end'] = words[i - 1]['end'] + 3
            else:
                word['end'] = words[i + 1]['start']

    return words


def word_score(word1, word2):
    word1 = set(word1.lower())
    word2 = set(word2.lower())
    return len(word1.intersection(word2)) / len(word1.union(word2))


def align_words_to_segments(transcribed_words, original_segments, extra_context):
    original_words = []
    num_words_in_segments = []
    for segment in original_segments:
        words = segment.split()
        num_words_in_segments.append(len(words))
        original_words.extend(words)

    def score_fn(orig_idx, asr_idx):
        return word_score(original_words[orig_idx], transcribed_words[asr_idx]['word'])

    alignment = pairwise2.align.globalcx(
        list(range(len(original_words))),
        list(range(len(transcribed_words))),
        score_fn,
        gap_char=[-1],
        one_alignment_only=True,
    )[0]

    original_with_time = [SingleWordSegment(word=word, start=float(
        'inf'), end=-float('inf')) for word in original_words]
    last_asr_id = -1
    last_seg_id = -1
    for seg_id, asr_id in zip(alignment.seqA, alignment.seqB):
        if asr_id != -1:
            last_asr_id = asr_id
        if seg_id != -1:
            last_seg_id = seg_id
        if last_asr_id != -1 and last_seg_id != -1:
            try:
                original_with_time[last_seg_id]['start'] = min(
                    original_with_time[last_seg_id]['start'], transcribed_words[last_asr_id]['start'])
                original_with_time[last_seg_id]['end'] = max(
                    original_with_time[last_seg_id]['end'], transcribed_words[last_asr_id]['end'])
            except:
                print(last_seg_id, last_asr_id)
                print(original_with_time[last_seg_id],
                      transcribed_words[last_asr_id])
                raise

    for i, (word, start, end) in enumerate(original_with_time):
        assert start != float('inf') and end != - \
            float('inf'), "Word %s not aligned" % word

    segment_word_counts_acc = [0]
    for n in num_words_in_segments:
        segment_word_counts_acc.append(segment_word_counts_acc[-1] + n)

    segment_times = []
    for seg_start, seg_end, orig_text in zip(segment_word_counts_acc[:-1], segment_word_counts_acc[1:], original_segments):
        l_extend = seg_start - max(0, seg_start - extra_context)
        r_extend = min(len(original_with_time),
                       seg_end + extra_context) - seg_end

        words = original_with_time[seg_start - l_extend:seg_end + r_extend]
        start = min([w['start'] for w in words])
        start = max(0, start - 0.2)
        end = max([w['end'] for w in words]) + 0.2

        text = " ".join([w['word'] for w in words])

        segment = SingleSegmentExtended(
            start=start,
            end=end,
            words=words,
            orig_text=orig_text,
            l_extend=l_extend,
            r_extend=r_extend,
            text=text,
        )
        segment_times.append(segment)

    return segment_times


def align_precise(first_pass_segments, audio_file, align_model, align_model_metadata, device):
    audio = load_audio(audio_file)

    second_pass_segments = align(
        first_pass_segments,
        align_model,
        align_model_metadata,
        audio,
        device,
        print_progress=True,
    )
    return second_pass_segments


def compute_final_segments(first_pass_segments, second_pass_segments):
    word_counts = [len(seg['words']) for seg in first_pass_segments]
    word_counts_acc = [0]
    for n in word_counts:
        word_counts_acc.append(word_counts_acc[-1] + n)

    final_segments = []
    for seg_id, (start, end, first_pass_segment) in enumerate(zip(word_counts_acc[:-1], word_counts_acc[1:], first_pass_segments)):
        words = second_pass_segments[start:end]
        l_extend = first_pass_segment['l_extend']
        if l_extend > 0:
            start = words[l_extend]['start']
        else:
            start = words[0]['start']
        r_extend = first_pass_segment['r_extend']
        if r_extend > 0:
            end = words[-r_extend - 1]['end']
        else:
            end = words[-1]['end']

        final_segments.append(
            SingleSegment(
                start=start,
                end=end,
                text=first_pass_segment['orig_text'],
            )
        )
    return final_segments


def dump_audio_segments(segments, audio_file, dump_audio_dir):
    if dump_audio_dir is None:
        return
    import torchaudio
    os.makedirs(dump_audio_dir, exist_ok=True)
    audio, sr = torchaudio.load(audio_file)
    name = os.path.basename(audio_file).replace('.wav', '')
    for seg_id, segment in enumerate(segments):
        start = int(segment['start'] * sr)
        end = int(segment['end'] * sr)
        torchaudio.save(os.path.join(
            dump_audio_dir, f"{name}_{seg_id:04d}_{start:03.2f}_{end:03.2f}.wav"), audio[:, start:end], sr)


def dump_yaml(segments, output_yaml_file):
    yaml_str = yaml.dump_all(
        segments, default_flow_style=True, width=99999999999, sort_keys=False)
    yaml_str = yaml_str.replace("--- ", "")
    yaml_str = "".join(f"- {line}" for line in yaml_str.splitlines(True))
    with open(output_yaml_file, 'w') as file:
        file.write(yaml_str)


def main():
    parser = argparse.ArgumentParser(
        description='Segmentation of WhisperX data')
    parser.add_argument('input_wavs', type=str,
                        nargs='+', help='Input wav files')
    parser.add_argument('output_yaml', type=str, help='Output yaml file')
    parser.add_argument('--language', type=str,
                        help='Language of the input audio', default='en')
    parser.add_argument('--device', type=str,
                        help='Device to use for alignment', default='cuda:0')
    parser.add_argument('--dump_audio_dir', type=str,
                        help='Directory to dump audio segments', default=None)
    parser.add_argument('--extra_context', type=int,
                        help='Extra context to consider for alignment (number of words)', default=3)
    args = parser.parse_args()

    final_segments = []

    align_model, align_model_metadata = load_align_model(args.language, args.device)

    for wav_file in args.input_wavs:
        assert os.path.exists(wav_file), "Input wav file does not exist"

        json_file = wav_file.replace('.wav', '.json')
        assert os.path.exists(
            json_file), "Input json file does not exist: %s" % json_file

        txt_file = wav_file.replace('.wav', '.txt')
        assert os.path.exists(
            txt_file), "Input txt file does not exist: %s" % txt_file

        original_segments = [line.strip()
                             for line in open(txt_file, 'r', encoding='utf-8')]
        transcribed_words = load_words_from_json(json_file)

        first_pass_segments = align_words_to_segments(
            transcribed_words, original_segments, args.extra_context)
        second_pass_segments = align_precise(
            first_pass_segments, wav_file, align_model, align_model_metadata, args.device)
        final_doc_segments = compute_final_segments(
            first_pass_segments, second_pass_segments['word_segments'])

        base_name = os.path.basename(wav_file)
        for segment in final_doc_segments:
            final_segments.append({
                "duration": float(segment['end'] - segment['start']),
                "offset": float(segment['start']),
                "speaker_id": base_name.replace('.wav', ''),
                "wav": base_name,
            })

        dump_audio_segments(final_doc_segments, wav_file, args.dump_audio_dir)

    dump_yaml(final_segments, args.output_yaml)

if __name__ == "__main__":
    main()
