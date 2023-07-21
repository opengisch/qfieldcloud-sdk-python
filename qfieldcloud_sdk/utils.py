import json
import sys
from typing import Iterable, Tuple
from urllib.parse import parse_qs, urlparse


def print_json(data):
    print(json.dumps(data, sort_keys=True, indent=2))


def log(*msgs):
    print(*msgs, file=sys.stderr)


def get_numeric_params(url: str, params: Iterable[str]) -> Tuple[int]:
    parsed_url = urlparse(url)
    parsed_query = parse_qs(parsed_url.query)
    return tuple(int(parsed_query[k][0]) for k in params)
