import fnmatch
import json
import logging
import os
import sys
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import urllib3

if sys.version_info >= (3, 8):
    from importlib import metadata
else:
    import importlib_metadata as metadata

import requests
from requests.models import Response

__version__ = metadata.version("qfieldcloud_sdk")


class DownloadStatus(str, Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class UploadStatus(str, Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class DeleteStatus(str, Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class DownloadType(str, Enum):
    FILES = "files"
    PACKAGED_FILES = "qfield-files"


class JobTypes(str, Enum):
    PACKAGE = "package"
    APPLY_DELTAS = "delta_apply"
    PROCESS_PROJECTFILE = "process_projectfile"


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

        self.reason = f'Requested "{response.url}" and got "{response.status_code} {response.reason}":\n{json_content or response.content}'

    def __str__(self):

        return self.reason

    def __repr__(self):
        return self.reason


class Client:
    def __init__(
        self, url: str = None, verify_ssl: bool = None, token: str = None
    ) -> None:
        """Prepares a new client.

        If the `url` is not provided, uses `QFIELDCLOUD_URL` from the environment.
        If the `token` is not provided, uses `QFIELDCLOUD_TOKEN` from the environment."""
        self.url = url or os.environ.get("QFIELDCLOUD_URL", None)
        self.token = token or os.environ.get("QFIELDCLOUD_TOKEN", None)
        self.verify_ssl = verify_ssl

        if not self.verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        if not self.url:
            raise QfcException(
                "Cannot create a new QFieldCloud client without a url passed in the constructor or as environment variable QFIELDCLOUD_URL"
            )

    def _log(self, *output) -> None:
        print(*output, file=sys.stderr)

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

    def list_files(self, project_id: str) -> List[Dict[str, Any]]:
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

    def delete_project(self, project_id: str):
        resp = self._request("DELETE", f"projects/{project_id}")

        return resp

    def upload_files(
        self,
        project_id: str,
        project_path: str,
        filter_glob: str = None,
        continue_on_error: bool = True,
        show_progress: bool = False,
    ) -> List[Dict]:
        """Upload files to a QFieldCloud project"""

        # skip temporary files (suffix ~)
        # skip temporary files (.gpkg-sch and .gpkg-)

        if not filter_glob:
            filter_glob = "*"

        files: List[Dict[str, Any]] = []
        for path in Path(project_path).rglob(filter_glob):
            if not path.is_file():
                continue

            if str(path.relative_to(project_path)).startswith(".qfieldsync"):
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
                upload_file = local_file
                if show_progress:
                    from tqdm import tqdm
                    from tqdm.utils import CallbackIOWrapper

                    progress_bar = tqdm(
                        total=local_path.stat().st_size,
                        unit_scale=True,
                        desc=local_path.stem,
                    )
                    upload_file = CallbackIOWrapper(
                        progress_bar.update, local_file, "read"
                    )

                try:
                    _ = self._request(
                        "POST",
                        f"files/{project_id}/{remote_path}",
                        files={
                            "file": upload_file,
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

        return files

    def download_files(
        self,
        project_id: str,
        local_dir: str,
        filter_glob: str = None,
        continue_on_error: bool = False,
        show_progress: bool = False,
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
            show_progress,
        )

    def list_jobs(self, project_id: str, job_type: JobTypes = None) -> Dict[str, Any]:
        """List project jobs."""

        resp = self._request(
            "GET",
            "jobs/",
            {
                "project_id": project_id,
                "type": job_type.value if job_type else None,
            },
        )

        return resp.json()

    def job_trigger(
        self, project_id: str, job_type: JobTypes, force: bool = False
    ) -> Dict[str, Any]:
        """Initiate a new project job."""

        resp = self._request(
            "POST",
            "jobs/",
            {
                "project_id": project_id,
                "type": job_type.value,
                "force": int(force),
            },
        )

        return resp.json()

    def job_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status."""

        resp = self._request("GET", f"jobs/{job_id}")

        return resp.json()

    def delete_files(
        self,
        project_id: str,
        glob_patterns: List[str],
        continue_on_error: bool = False,
        finished_cb: Callable = None,
    ) -> Dict[str, Dict[str, Any]]:
        project_files = self.list_files(project_id)
        glob_results = {}
        self._log(f"Project '{project_id}' has {len(project_files)} file(s).")

        for glob_pattern in glob_patterns:
            glob_results[glob_pattern] = []

            for file in project_files:
                if not fnmatch.fnmatch(file["name"], glob_pattern):
                    continue

                if "status" in file:
                    # file has already been matched by a previous glob pattern
                    continue

                file["status"] = DeleteStatus.PENDING
                glob_results[glob_pattern].append(file)

        for glob_pattern, files in glob_results.items():
            if not files:
                self._log(f"Glob pattern '{glob_pattern}' did not match any files.")
                continue

            for file in files:
                try:
                    resp = self._request(
                        "DELETE",
                        f'files/{project_id}/{file["name"]}',
                        stream=True,
                    )
                    file["status"] = DeleteStatus.SUCCESS
                except QfcRequestException as err:
                    resp = err.response

                    logging.info(
                        f"{resp.request.method} {resp.url} got HTTP {resp.status_code}"
                    )

                    file["status"] = DeleteStatus.FAILED
                    file["error"] = err

                    self._log(
                        f'File "{file["name"]}" failed to delete:\n{file["error"]}'
                    )

                    if continue_on_error:
                        continue
                    else:
                        raise err
                finally:
                    if callable(finished_cb):
                        finished_cb(file)

        files_deleted = 0
        files_failed = 0
        for files in glob_results.values():
            for file in files:
                self._log(f'{file["status"]}\t{file["name"]}')

                if file["status"] == DeleteStatus.SUCCESS:
                    files_deleted += 1
                elif file["status"] == DeleteStatus.SUCCESS:
                    files_failed += 1

        self._log(
            f"{files_deleted} file(s) deleted, {files_failed} file(s) failed to delete"
        )

        return glob_results

    def package_latest(self, project_id: str) -> Dict[str, Any]:
        """Check project packaging status."""
        resp = self._request("GET", f"packages/{project_id}/latest/")

        return resp.json()

    def package_download(
        self,
        project_id: str,
        local_dir: str,
        filter_glob: str = None,
        continue_on_error: bool = False,
        show_progress: bool = False,
    ) -> List[Dict]:
        """Download the specified project packaged files into the destination dir.

        Args:
            project_id: id of the project to be downloaded
            local_dir: destination directory where the files will be downloaded
            filter_glob: if specified, download only packaged files which match the glob, otherwise download all
        """
        project_status = self.package_latest(project_id)

        if project_status["status"] != "finished":
            raise QfcException(
                "The project has not been successfully packaged yet. Please use `qfieldcloud-cli package-trigger {project_id}` first."
            )

        resp = self._request("GET", f"packages/{project_id}/latest/")

        return self._download_files(
            resp.json()["files"],
            DownloadType.PACKAGED_FILES,
            project_id,
            local_dir,
            filter_glob,
            continue_on_error,
            show_progress,
        )

    def _download_files(
        self,
        files: List[Dict],
        download_type: DownloadType,
        project_id: str,
        local_dir: str,
        filter_glob: str = None,
        continue_on_error: bool = False,
        show_progress: bool = False,
    ) -> List[Dict]:
        if not filter_glob:
            filter_glob = "*"

        files_to_download: List[Dict[str, Any]] = []

        for file in files:
            if fnmatch.fnmatch(file["name"], filter_glob):
                file["status"] = DownloadStatus.PENDING
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
            except QfcRequestException as err:
                resp = err.response

                logging.info(
                    f"{resp.request.method} {resp.url} got HTTP {resp.status_code}"
                )

                file["status"] = DownloadStatus.FAILED
                file["error"] = err

                if continue_on_error:
                    continue
                else:
                    raise err

            if not local_file.parent.exists():
                local_file.parent.mkdir(parents=True)

            with open(local_file, "wb") as f:
                download_file = f
                if show_progress:
                    from tqdm import tqdm
                    from tqdm.utils import CallbackIOWrapper

                    content_length = int(resp.headers.get("content-length", 0))
                    progress_bar = tqdm(
                        total=content_length, unit_scale=True, desc=file["name"]
                    )
                    download_file = CallbackIOWrapper(progress_bar.update, f, "write")

                for chunk in resp.iter_content(chunk_size=8192):
                    # filter out keep-alive new chunks
                    if chunk:
                        download_file.write(chunk)

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
        ] = f"sdk|py|{__version__} python-requests|{metadata.version('requests')}"

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
