import fnmatch
import hashlib
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


class FileTransferStatus(str, Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class FileTransferType(Enum):
    PROJECT = "project"
    PACKAGE = "package"


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

    def list_remote_files(self, project_id: str) -> List[Dict[str, Any]]:
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
        upload_type: FileTransferType,
        project_path: str,
        filter_glob: str,
        throw_on_error: bool = False,
        show_progress: bool = False,
        force: bool = False,
        job_id: str = "",
    ) -> List[Dict]:
        """Upload files to a QFieldCloud project"""
        if not filter_glob:
            filter_glob = "*"

        local_files = self.list_local_files(project_path, filter_glob)

        # we should always upload all package files
        if upload_type == FileTransferType.PACKAGE:
            force = True

        files_to_upload = []
        if force:
            files_to_upload = local_files
        else:
            remote_files = self.list_remote_files(project_id)

            if len(remote_files) == 0:
                files_to_upload = local_files
            else:
                for local_file in local_files:
                    remote_file = None
                    for f in remote_files:
                        if f["name"] == local_file["name"]:
                            remote_file = f
                            break

                    md5sum = self._get_md5sum(local_file["absolute_filename"])
                    if remote_file and remote_file.get("md5sum", None) == md5sum:
                        continue

                    files_to_upload.append(local_file)

        if not files_to_upload:
            return files_to_upload

        for file in files_to_upload:
            try:
                local_filename = Path(file["absolute_filename"])
                self.upload_file(
                    project_id,
                    upload_type,
                    local_filename,
                    file["name"],
                    show_progress,
                    job_id,
                )
                file["status"] = FileTransferStatus.SUCCESS
            except Exception as err:
                file["status"] = FileTransferStatus.FAILED
                file["error"] = err

                if throw_on_error:
                    raise err
                else:
                    continue

        return local_files

    def upload_file(
        self,
        project_id: str,
        upload_type: FileTransferType,
        local_filename: Path,
        remote_filename: Path,
        show_progress: bool,
        job_id: str = "",
    ) -> requests.Response:
        with open(local_filename, "rb") as local_file:
            upload_file = local_file
            if show_progress:
                from tqdm import tqdm
                from tqdm.utils import CallbackIOWrapper

                progress_bar = tqdm(
                    total=local_filename.stat().st_size,
                    unit_scale=True,
                    desc=local_filename.stem,
                )
                upload_file = CallbackIOWrapper(progress_bar.update, local_file, "read")
            else:
                logging.info(f'Uploading file "{remote_filename}"…')

            if upload_type == FileTransferType.PROJECT:
                url = f"files/{project_id}/{remote_filename}"
            elif upload_type == FileTransferType.PACKAGE:
                if not job_id:
                    raise QfcException(
                        'When the upload type is "package", you must pass the "job_id" parameter.'
                    )

                url = f"packages/{project_id}/{job_id}/files/{remote_filename}"
            else:
                raise NotImplementedError()

            return self._request(
                "POST",
                url,
                files={
                    "file": upload_file,
                },
            )

    def download_project(
        self,
        project_id: str,
        local_dir: str,
        filter_glob: str = None,
        throw_on_error: bool = False,
        show_progress: bool = False,
        force_download: bool = False,
    ) -> List[Dict]:
        """Download the specified project files into the destination dir.

        Args:
            project_id: id of the project to be downloaded
            local_dir: destination directory where the files will be downloaded
            filter_glob: if specified, download only the files which match the glob, otherwise download all
            force_download (bool, optional): Download file even if it already exists locally. Defaults to False.
        """

        files = self.list_remote_files(project_id)

        return self.download_files(
            files,
            project_id,
            FileTransferType.PROJECT,
            local_dir,
            filter_glob,
            throw_on_error,
            show_progress,
            force_download,
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
        throw_on_error: bool = False,
        finished_cb: Callable = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Delete project files.

        Args:
            project_id (str): Project id
            glob_patterns (List[str]): Delete only files matching one the glob patterns.
            throw_on_error (bool, optional): Throw if delete error occurres. Defaults to False.
            finished_cb (Callable, optional): Deprecated. Defaults to None.

        Raises:
            QFieldCloudException: if throw_on_error is True, throw an error if a download request fails.

        Returns:
            Dict[str, Dict[str, Any]]: Deleted files by glob pattern.
        """
        project_files = self.list_remote_files(project_id)
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

                file["status"] = FileTransferStatus.PENDING
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
                    file["status"] = FileTransferStatus.SUCCESS
                except QfcRequestException as err:
                    resp = err.response

                    logging.info(
                        f"{resp.request.method} {resp.url} got HTTP {resp.status_code}"
                    )

                    file["status"] = FileTransferStatus.FAILED
                    file["error"] = err

                    self._log(
                        f'File "{file["name"]}" failed to delete:\n{file["error"]}'
                    )

                    if throw_on_error:
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

                if file["status"] == FileTransferStatus.SUCCESS:
                    files_deleted += 1
                elif file["status"] == FileTransferStatus.SUCCESS:
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
        throw_on_error: bool = False,
        show_progress: bool = False,
        force_download: bool = False,
    ) -> List[Dict]:
        """Download the specified project packaged files into the destination dir.

        Args:
            project_id: id of the project to be downloaded
            local_dir: destination directory where the files will be downloaded
            filter_glob: if specified, download only packaged files which match the glob, otherwise download all
            force_download (bool, optional): Download file even if it already exists locally. Defaults to False.
        """
        project_status = self.package_latest(project_id)

        if project_status["status"] != "finished":
            raise QfcException(
                "The project has not been successfully packaged yet. Please use `qfieldcloud-cli package-trigger {project_id}` first."
            )

        resp = self._request("GET", f"packages/{project_id}/latest/")

        return self.download_files(
            resp.json()["files"],
            project_id,
            FileTransferType.PACKAGE,
            local_dir,
            filter_glob,
            throw_on_error,
            show_progress,
            force_download,
        )

    def download_files(
        self,
        files: List[Dict],
        project_id: str,
        download_type: FileTransferType,
        local_dir: str,
        filter_glob: str = None,
        throw_on_error: bool = False,
        show_progress: bool = False,
        force_download: bool = False,
    ) -> List[Dict]:
        """Download project files.

        Args:
            files (List[Dict]): A list of file dicts, specifying which files to download.
            project_id (str): Project id
            download_type (FileTransferType): File transfer type which specifies what should be the download url.
            local_dir (str): Local destination directory
            filter_glob (str, optional): Download only files matching the glob pattern. If None download all. Defaults to None.
            throw_on_error (bool, optional): Throw if download error occurres. Defaults to False.
            show_progress (bool, optional): Show progress bar in the console. Defaults to False.
            force_download (bool, optional): Download file even if it already exists locally. Defaults to False.
        Raises:
            QFieldCloudException: if throw_on_error is True, throw an error if a download request fails.

        Returns:
            List[Dict]: A list of file dicts.
        """
        if not filter_glob:
            filter_glob = "*"

        files_to_download: List[Dict[str, Any]] = []

        for file in files:
            if fnmatch.fnmatch(file["name"], filter_glob):
                file["status"] = FileTransferStatus.PENDING
                files_to_download.append(file)

        for file in files_to_download:
            local_filename = Path(f'{local_dir}/{file["name"]}')
            md5sum = None
            if not force_download:
                md5sum = file.get("md5sum", None)

            try:
                self.download_file(
                    project_id,
                    download_type,
                    local_filename,
                    file["name"],
                    show_progress,
                    md5sum,
                )
                file["status"] = FileTransferStatus.SUCCESS
            except QfcRequestException as err:
                resp = err.response

                logging.info(
                    f"{resp.request.method} {resp.url} got HTTP {resp.status_code}"
                )

                file["status"] = FileTransferStatus.FAILED
                file["error"] = err

                if throw_on_error:
                    raise err
                else:
                    continue

        return files_to_download

    def download_file(
        self,
        project_id: str,
        download_type: FileTransferType,
        local_filename: Path,
        remote_filename: Path,
        show_progress: bool,
        remote_md5sum: str = None,
    ) -> requests.Response:
        """Download a single project file.

        Args:
            project_id (str): Project id
            download_type (FileTransferType): File transfer type which specifies what should be the download URL
            local_filename (Path): Local filename
            remote_filename (Path): Remote filename
            show_progress (bool): Show progressbar in the console
            remote_md5sum (str, optional): The md5sum of the remote file. If is None, the download of the file happens even if it already exists locally. Defaults to None.

        Raises:
            NotImplementedError: Raised if unknown `download_type` is passed

        Returns:
            requests.Response: the response object
        """

        if remote_md5sum and local_filename.exists():
            if self._get_md5sum(str(local_filename)) == remote_md5sum:
                if show_progress:
                    print(
                        f"{remote_filename}: Already present locally. Download skipped."
                    )
                else:
                    logging.info(
                        f'Skipping download of "{remote_filename}" because it is already present locally'
                    )
                return

        if download_type == FileTransferType.PROJECT:
            url = f"files/{project_id}/{remote_filename}"
        elif download_type == FileTransferType.PACKAGE:
            url = f"packages/{project_id}/latest/files/{remote_filename}"
        else:
            raise NotImplementedError()

        resp = self._request("GET", url, stream=True)

        if not local_filename.parent.exists():
            local_filename.parent.mkdir(parents=True)

        with open(local_filename, "wb") as f:
            download_file = f
            if show_progress:
                from tqdm import tqdm
                from tqdm.utils import CallbackIOWrapper

                content_length = int(resp.headers.get("content-length", 0))
                progress_bar = tqdm(
                    total=content_length,
                    unit_scale=True,
                    desc=remote_filename,
                )
                download_file = CallbackIOWrapper(progress_bar.update, f, "write")
            else:
                logging.info(f'Downloading file "{remote_filename}"…')

            for chunk in resp.iter_content(chunk_size=8192):
                # filter out keep-alive new chunks
                if chunk:
                    download_file.write(chunk)

        return resp

    def list_local_files(
        self, root_path: str, filter_glob: str
    ) -> List[Dict[str, Any]]:
        """
        Returns a list of dicts with information about local files. Usually used before uploading files.
        NOTE: files and dirs starting with leading dot (.) or ending in tilde (~) will be ignored.
        """
        if not filter_glob:
            filter_glob = "*"

        files: List[Dict[str, Any]] = []
        for path in Path(root_path).rglob(filter_glob):
            if not path.is_file():
                continue

            basename = path.relative_to(root_path).name
            if basename.startswith(".") or basename.endswith("~"):
                continue

            relative_name = path.relative_to(root_path)
            files.append(
                {
                    "name": str(relative_name),
                    "absolute_filename": str(path),
                    "status": FileTransferStatus.PENDING,
                    "error": None,
                }
            )

        # upload the QGIS project file at the end
        files.sort(key=lambda f: Path(f["name"]).suffix.lower() in (".qgs", ".qgz"))

        return files

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

    def _get_md5sum(self, filename: str) -> str:
        """Calculate sha256sum of a file"""
        BLOCKSIZE = 65536
        hasher = hashlib.md5()
        with open(filename, "rb") as f:
            buf = f.read(BLOCKSIZE)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(BLOCKSIZE)
        return hasher.hexdigest()
