import hashlib
from pathlib import Path


def compute_file_hash(path: Path, algo="sha1") -> bytes:
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.digest()
