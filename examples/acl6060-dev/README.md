# Resegment ACL 60/60 Dev Set

Download and unzip the ACL 60/60 Dev Set:
```
wget https://aclanthology.org/attachments/2023.iwslt-1.2.dataset.zip
unzip 2023.iwslt-1.2.dataset.zip
```

Run WhisperX on each WAV file:
```
for wav in ./2/acl_6060/dev/full_wavs/2022.acl-long.*.wav; do
    whisperx --language en "$wav"
done
```

Generate ground-truth transcripts for each WAV file:
```
python preprocess-xml.py ./2/acl_6060/dev/text/xml/ACL.6060.dev.en-xx.en.xml ./2/acl_6060/dev/full_wavs
```

Run the Audio Resegmenter:
```
audio_resegmenter ./2/acl_6060/dev/full_wavs/2022.acl-long.*.wav acl6060.yaml
```
