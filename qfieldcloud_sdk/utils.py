import hashlib
import json
import sys


def print_json(data):
    """Pretty print as JSON string"""
    print(json.dumps(data, sort_keys=True, indent=2))


def log(*msgs):
    """Print text chunks to stderr"""
    print(*msgs, file=sys.stderr)


def get_md5sum(filename: str) -> str:
    """Calculate sha256sum of a file"""
    BLOCKSIZE = 65536
    hasher = hashlib.md5()
    with open(filename, "rb") as f:
        buf = f.read(BLOCKSIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(BLOCKSIZE)
    return hasher.hexdigest()
