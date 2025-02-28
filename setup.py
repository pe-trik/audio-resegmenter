from setuptools import setup, find_packages

setup(
    name='audio_resegmenter',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'biopython',
        'whisperx',
        'torchaudio',
    ],
    entry_points={
        'console_scripts': [
            'audio_resegmenter=audio_resegmenter.resegment:main',
        ],
    },
)
