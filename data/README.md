# Dataset

This project uses the public CHB-MIT Scalp EEG Database distributed through PhysioNet.

Raw EDF recordings and patient annotation files are intentionally not committed to this repository. Download the dataset from the official source and keep it in a local data directory outside Git version control.

The canonical notebook expects the CHB-MIT patient-folder structure and parses the associated seizure summary files.

Do not commit raw EEG recordings, generated patient caches, trained model binaries, or local absolute paths.