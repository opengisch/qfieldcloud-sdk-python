import hashlib
import json
import sys
from typing import Iterable, Tuple
from urllib.parse import parse_qs, urlparse


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


def get_numeric_params(url: str, params: Iterable[str]) -> Tuple[int]:
    """Extract numeric parameters from url GET query"""
    parsed_url = urlparse(url)
    parsed_query = parse_qs(parsed_url.query)
    return tuple(int(parsed_query[k][0]) for k in params)
