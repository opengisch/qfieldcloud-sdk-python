import fnmatch
import json
import logging
import os
import sys
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

if sys.version_info >= (3, 8):
    from importlib import metadata
else:
    import importlib_metadata as metadata

import requests
from requests.models import Response


class DownloadStatus(Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class UploadStatus(Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class DownloadType(Enum):
    FILES = "files"
    PACKAGED_FILES = "qfield-files"


class QfcException(Exception):
    def __init__(self, reason: str, *args: object) -> None:
        super().__init__(reason, *args)


class QfcRequestException(QfcException):
    def __init__(self, response: Response, *args: object) -> None:
        super().__init__(str(response), *args)
        self.response = response

        try:
            json_content = response.json()
            json_content = json.dumps(json_content, sort_keys=True, indent=2)
        except Exception:
            json_content = ""

        self.reason = f'Requested "{response.url}" and got "{response.status_code} {response.reason}":\n{json_content or response.raw}'

    def __str__(self):

        return self.reason

    def __repr__(self):
        return self.reason


class Client:
    def __init__(
        self, url: str = None, verify_ssl: bool = True, token: str = None
    ) -> None:
        """Prepares a new client.

        If the `url` is not provided, uses `QFIELDCLOUD_URL` from the environment.
        If the `token` is not provided, uses `QFIELDCLOUD_TOKEN` from the environment."""
        self.url = url or os.environ.get("QFIELDCLOUD_URL", None)
        self.token = token or os.environ.get("QFIELDCLOUD_TOKEN", None)
        self.verify_ssl = verify_ssl

        if not self.url:
            raise QfcException(
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
            skip_token=True,
        )

        payload = resp.json()

        self.token = payload["token"]

        return payload

    def logout(self) -> None:
        """Logout from the current session."""
        resp = self._request("POST", "auth/logout")

        return resp.json()

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

    def create_project(
        self,
        name: str,
        owner: str = None,
        description: str = "",
        is_public: bool = False,
    ) -> Dict:
        resp = self._request(
            "POST",
            "projects",
            data={
                "name": name,
                "owner": owner,
                "description": description,
                "is_public": int(is_public),
            },
        )

        return resp.json()

    def upload_files(
        self,
        project_id: str,
        project_path: str,
        filter_glob: str = None,
        continue_on_error: bool = True,
        cb: Callable = None,
    ) -> List[Dict]:
        """Upload files to a QFieldCloud project"""

        if not filter_glob:
            filter_glob = "**/*"

        # PurePath(filter_glob).match(pattern)
        files: List[Dict[str, Any]] = []
        for path in Path(project_path).rglob(filter_glob):
            if not path.is_file():
                continue

            files.append(
                {
                    "name": str(path),
                    "status": UploadStatus.PENDING,
                    "error": None,
                }
            )

        if not files:
            return files

        # upload the QGIS project file at the end
        files.sort(key=lambda f: Path(f["name"]).suffix.lower() in (".qgs", ".qgz"))

        for file in files:
            local_path = Path(file["name"])

            remote_path = local_path.relative_to(project_path)

            with open(file["name"], "rb") as local_file:
                try:
                    _ = self._request(
                        "POST",
                        f"files/{project_id}/{remote_path}",
                        files={
                            "file": local_file,
                        },
                    )
                    file["status"] = UploadStatus.SUCCESS
                except Exception as err:
                    file["status"] = UploadStatus.FAILED
                    file["error"] = err

                    if continue_on_error:
                        continue
                    else:
                        raise err
                finally:
                    if cb:
                        cb(file)

        return files

    def download_files(
        self,
        project_id: str,
        local_dir: str,
        filter_glob: str = None,
        continue_on_error: bool = False,
        finished_cb: Callable = None,
    ) -> List[Dict]:
        """Download the specified project files into the destination dir.

        Args:
            project_id: id of the project to be downloaded
            local_dir: destination directory where the files will be downloaded
            filter_glob: if specified, download only the files which match the glob, otherwise download all
        """

        files = self.list_files(project_id)

        return self._download_files(
            files,
            DownloadType.FILES,
            project_id,
            local_dir,
            filter_glob,
            continue_on_error,
            finished_cb,
        )

    def package_trigger(self, project_id: str) -> Dict[str, Any]:
        """Initiate project packaging for QField."""

        resp = self._request("POST", f"qfield-files/export/{project_id}")

        return resp.json()

    def package_status(self, project_id: str) -> Dict[str, Any]:
        """Check project packaging status."""
        resp = self._request("GET", f"qfield-files/export/{project_id}")

        return resp.json()

    def package_download(
        self,
        project_id: str,
        local_dir: str,
        filter_glob: str = None,
        continue_on_error: bool = False,
        finished_cb: Callable = None,
    ) -> List[Dict]:
        """Download the specified project packaged files into the destination dir.

        Args:
            project_id: id of the project to be downloaded
            local_dir: destination directory where the files will be downloaded
            filter_glob: if specified, download only packaged files which match the glob, otherwise download all
        """
        project_status = self.package_status(project_id)

        if project_status["status"] != "STATUS_EXPORTED":
            raise QfcException(
                "The project has not been successfully packaged yet. Please use `qfieldcloud-cli package-trigger {project_id}` first."
            )

        resp = self._request("GET", f"qfield-files/{project_id}")

        return self._download_files(
            resp.json()["files"],
            DownloadType.PACKAGED_FILES,
            project_id,
            local_dir,
            filter_glob,
            continue_on_error,
            finished_cb,
        )

    def _download_files(
        self,
        files: List[Dict],
        download_type: DownloadType,
        project_id: str,
        local_dir: str,
        filter_glob: str = None,
        continue_on_error: bool = False,
        finished_cb: Callable = None,
    ) -> List[Dict]:
        if not filter_glob:
            filter_glob = "**/*"

        files_to_download: List[Dict[str, Any]] = []

        for file in files:
            if fnmatch.fnmatch(file["name"], filter_glob):
                file["status"] = DownloadStatus.PENDING
                file["status_reason"] = ""
                files_to_download.append(file)

        for file in files_to_download:
            local_file = Path(f'{local_dir}/{file["name"]}')
            resp = None

            try:
                resp = self._request(
                    "GET",
                    f'{download_type.value}/{project_id}/{file["name"]}',
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
            finally:
                if callable(finished_cb):
                    finished_cb(file)

            if not local_file.parent.exists():
                local_file.parent.mkdir(parents=True)

            with open(local_file, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:  # filter out keep-alive new chunks
                        f.write(chunk)

        return files_to_download

    def _request(
        self,
        method: str,
        path: str,
        data: Any = None,
        params: Dict[str, str] = {},
        headers: Dict[str, str] = {},
        files: Dict[str, Any] = None,
        stream: bool = False,
        skip_token: bool = False,
        allow_redirects=None,
    ) -> requests.Response:
        method = method.upper()
        headers_copy = {**headers}

        assert self.url

        allow_redirects = method != "POST"

        if not skip_token and self.token:
            headers_copy["Authorization"] = f"token {self.token}"

        headers_copy[
            "User-Agent"
        ] = f"sdk|py|{metadata.version('qfieldcloud_sdk')} python-requests|{metadata.version('requests')}"

        if not path.startswith("http"):
            if path.startswith("/"):
                path = path[1:]

            if not path.endswith("/"):
                path += "/"

            path = self.url + path

        response = requests.request(
            method=method,
            url=path,
            data=data,
            params=params,
            headers=headers_copy,
            files=files,
            stream=stream,
            verify=self.verify_ssl,
            # redirects from POST requests automagically turn into GET requests, so better forbid redirects
            allow_redirects=allow_redirects,
        )

        try:
            response.raise_for_status()
        except Exception as err:
            raise QfcRequestException(response) from err

        return response
