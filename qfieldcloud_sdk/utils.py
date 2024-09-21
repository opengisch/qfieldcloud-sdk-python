import hashlib
import json
import os
import sys
import re
from typing import Tuple


def print_json(data):
    """Pretty print as JSON string"""
    print(json.dumps(data, sort_keys=True, indent=2))


def log(*msgs):
    """Print text chunks to stderr"""
    print(*msgs, file=sys.stderr)


def get_md5sum(filename: str) -> str:
    """Calculate md5sum of a file.

    Currently unused but will be revived in the upcoming versions.
    """
    BLOCKSIZE = 65536
    hasher = hashlib.md5()
    with open(filename, "rb") as f:
        buf = f.read(BLOCKSIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(BLOCKSIZE)
    return hasher.hexdigest()


def calc_etag(filename: str, part_size: int = 8 * 1024 * 1024) -> str:
    """Calculate ETag as in Object Storage (S3) of a local file.

    ETag is a MD5. But for the multipart uploaded files, the MD5 is computed from the concatenation of the MD5s of each uploaded part.

    See the inspiration of this implementation here: https://stackoverflow.com/a/58239738/1226137

    Args:
        filename (str): the local filename
        part_size (int): the size of the Object Storage part. Most Object Storages use 8MB. Defaults to 8*1024*1024.

    Returns:
        str: the calculated ETag value
    """
    with open(filename, "rb") as f:
        file_size = os.fstat(f.fileno()).st_size

        if file_size <= part_size:
            BLOCKSIZE = 65536
            hasher = hashlib.md5()

            buf = f.read(BLOCKSIZE)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(BLOCKSIZE)

            return hasher.hexdigest()
        else:
            # Say you uploaded a 14MB file and your part size is 5MB.
            # Calculate 3 MD5 checksums corresponding to each part, i.e. the checksum of the first 5MB, the second 5MB, and the last 4MB.
            # Then take the checksum of their concatenation.
            # Since MD5 checksums are hex representations of binary data, just make sure you take the MD5 of the decoded binary concatenation, not of the ASCII or UTF-8 encoded concatenation.
            # When that's done, add a hyphen and the number of parts to get the ETag.
            md5sums = []
            for data in iter(lambda: f.read(part_size), b""):
                md5sums.append(hashlib.md5(data).digest())

            final_md5sum = hashlib.md5(b"".join(md5sums))

            return "{}-{}".format(final_md5sum.hexdigest(), len(md5sums))


def is_valid_windows_filename(filename: str) -> Tuple[bool, str]:
    """Check if the filename contains forbidden characters for Windows and return them."""
    # Forbidden characters in Windows
    # https://stackoverflow.com/questions/1976007/what-characters-are-forbidden-in-windows-and-linux-directory-names
    invalid_chars = r'[<>:"/\\|?*]'
    matches = re.findall(invalid_chars, filename)
    if matches:
        return False, "".join(set(matches))
    return True, ""
