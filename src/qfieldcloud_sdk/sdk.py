import logging
import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


class DownloadStatus(Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class Client:
    def __init__(self, url: Optional[str], verify_ssl: bool = True) -> None:
        """Prepares a new client. If the `url` is not provided, uses `QFIELDCLOUD_URL` from the environment."""
        self.url = url or os.environ.get("QFIELDCLOUD_URL", "")
        self.token = None
        self.verify_ssl = verify_ssl

        if not self.url:
            raise Exception(
                "Cannot create a new QFieldCloud client without a url passed in the constructor or as environment variable QFIELDCLOUD_URL"
            )

    def login(self, username: str, password: str) -> Dict:
        """Logins with the provided credentials.

        Args:
            username: the username or the email used to register
            password: the password associated with that username
        """
        resp = self._request(
            "POST",
            "auth/login",
            data={
                "username": username,
                "password": password,
            },
        )

        payload = resp.json()

        self.token = payload["token"]

        return payload

    def list_projects(
        self, username: Optional[str] = None, include_public: Optional[bool] = False
    ) -> Dict:
        """Lists the project of a given user. If the user is omitted, it fallbacks to the currently logged in user"""
        resp = self._request(
            "GET",
            "projects",
            params={
                "include-public": "1" if include_public else "0",
            },
        )

        return resp.json()

    def list_files(self, project_id: str) -> List[Dict]:
        resp = self._request("GET", f"files/{project_id}")
        return resp.json()

    def download_files(
        self,
        project_id: str,
        local_dir: str,
        path_starts_with: str = None,
        continue_on_error: bool = False,
    ) -> List[Dict]:
        """Download the specified project files into the destination dir.

        Args:
            project_id: id of the project to be downloaded
            local_dir: destination directory where the files will be downloaded
            path_starts_with: if specified, download only files that are within that path starts with, otherwise download all
        """

        files = self.list_files(project_id)
        files_count = 0

        for file in files:
            file["status"] = DownloadStatus.PENDING
            file["status_reason"] = ""

        files_to_download = []

        for file in files:
            local_file = Path(f'{local_dir}/{file["name"]}')
            resp = None

            if path_starts_with and not file["name"].startswith(path_starts_with):
                continue

            files_to_download.append(file)

            try:
                resp = self._request(
                    "GET",
                    f'files/{project_id}/{file["name"]}',
                    stream=True,
                )
                file["status"] = DownloadStatus.SUCCESS
            except Exception as err:
                assert resp

                logging.info(
                    f"{resp.request.method} {resp.url} got HTTP {resp.status_code}"
                )

                file["status"] = DownloadStatus.FAILED
                file["status_reason"] = {"status_code": resp.status_code}

                if continue_on_error:
                    continue
                else:
                    raise err

            if not local_file.parent.exists():
                local_file.parent.mkdir(parents=True)

            with open(local_file, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:  # filter out keep-alive new chunks
                        f.write(chunk)
            files_count += 1

        return files_to_download

    def _request(
        self,
        method: str,
        path: str,
        data: Any = None,
        params: Dict[str, str] = {},
        headers: Dict[str, str] = {},
        files: Dict[str, str] = None,
        stream: bool = False,
    ) -> requests.Response:
        method = method.upper()
        headers_copy = {**headers}

        if self.token:
            headers_copy["Authorization"] = f"token {self.token}"

        if path.startswith("/"):
            path = path[1:]

        if not path.endswith("/"):
            path += "/"

        response = requests.request(
            method=method,
            url=self.url + path,
            data=data,
            params=params,
            headers=headers_copy,
            files=files,
            stream=stream,
            verify=self.verify_ssl,
            # redirects from POST requests automagically turn into GET requests, so better forbid redirects
            allow_redirects=(method != "POST"),
        )

        response.raise_for_status()

        return response
