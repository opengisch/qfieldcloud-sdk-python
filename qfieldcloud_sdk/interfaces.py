import json
from typing import Any

import requests


class QfcMockItem(dict):
    def __getitem__(self, k: str) -> Any:
        if k == "id":
            return super().__getitem__("id")
        else:
            return k


class QfcMockResponse(requests.Response):
    def __init__(self, **kwargs):
        self.request_kwargs = kwargs
        self.url = kwargs["url"]
        self.limit = kwargs.get("limit", 5)
        self.total = self.limit * 2
        self.headers = {
            "X-Total-Count": self.total,
        }

        limit = kwargs["params"].get("limit")
        offset = kwargs["params"].get("offset", 0)
        prev_url = None
        next_url = None
        if limit:
            if offset == 0:
                prev_url = None
                next_url = f"{self.url}?limit={limit}&offset={limit}"
            else:
                prev_url = f"{self.url}?limit={limit}&offset=0"
                next_url = None

        self.headers["X-Previous-Page"] = prev_url
        self.headers["X-Next-Page"] = next_url

    def json(self):
        if self.request_kwargs["method"] == "GET":
            return [QfcMockItem(id=n) for n in range(self.total)]
        else:
            return QfcMockItem(id="test_id", **self.request_kwargs)


class QfcRequest(requests.Request):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kwargs = kwargs

    def mock_response(self) -> QfcMockResponse:
        return QfcMockResponse(**self.kwargs)


class QfcException(Exception):
    def __init__(self, reason: str, *args):
        super().__init__(reason, *args)


class QfcRequestException(QfcException):
    def __init__(self, response: requests.Response, *args):
        super().__init__(str(response), *args)
        self.response = response

        try:
            json_content = response.json()
            json_content = json.dumps(json_content, sort_keys=True, indent=2)
        except Exception:
            json_content = ""

        self.reason = f'Requested "{response.url}" and got "{response.status_code} {response.reason}":\n{json_content or response.content.decode()}'

    def __str__(self) -> str:
        return self.reason

    def __repr__(self) -> str:
        return self.reason
