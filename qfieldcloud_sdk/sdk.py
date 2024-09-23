import datetime
import fnmatch
import logging
import os
import sys
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypedDict, Union, cast
from urllib import parse as urlparse

import requests
import urllib3
from requests.adapters import HTTPAdapter, Retry

from .interfaces import QfcException, QfcRequest, QfcRequestException
from .utils import calc_etag, log
from pathvalidate import is_valid_filename, is_valid_filepath, ValidationError


logger = logging.getLogger(__file__)

if sys.version_info >= (3, 8):
    from importlib import metadata
else:
    import importlib_metadata as metadata


try:
    __version__ = metadata.version("qfieldcloud_sdk")
except metadata.PackageNotFoundError:
    __version__ = "dev"


DEFAULT_PAGINATION_LIMIT = 20
"""int: Defines the default limit for pagination, set to `20`."""


class FileTransferStatus(str, Enum):
    """Represents the status of a file transfer.

    Attributes:
        PENDING: The transfer is pending.
        SUCCESS: The transfer was successful.
        FAILED: The transfer failed.
    """

    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class FileTransferType(str, Enum):
    """Represents the type of file transfer.

    The PACKAGE transfer type is used only internally in QFieldCloud workers, so it should never be used by other API clients.

    Attributes:
        PROJECT: Refers to a project file.
        PACKAGE: Refers to a package Type.
    """

    PROJECT = "project"
    PACKAGE = "package"


class JobTypes(str, Enum):
    """Represents the types of jobs that can be processed on QFieldCloud.

    Attributes:
        PACKAGE: Refers to a packaging job.
        APPLY_DELTAS: Refers to applying deltas (differences).
        PROCESS_PROJECTFILE: Refers to processing a project file.
    """

    PACKAGE = "package"
    APPLY_DELTAS = "delta_apply"
    PROCESS_PROJECTFILE = "process_projectfile"


class ProjectCollaboratorRole(str, Enum):
    """Defines roles for project collaborators.

    See project collaborator roles documentation: https://docs.qfield.org/reference/qfieldcloud/permissions/#roles_1

    Attributes:
        ADMIN: Administrator role.
        MANAGER: Manager role.
        EDITOR: Editor role.
        REPORTER: Reporter role.
        READER: Reader role.
    """

    ADMIN = "admin"
    MANAGER = "manager"
    EDITOR = "editor"
    REPORTER = "reporter"
    READER = "reader"


class OrganizationMemberRole(str, Enum):
    """Defines roles for organization members.

    See organization member roles documentation: https://docs.qfield.org/reference/qfieldcloud/permissions/#roles_2

    Attributes:
        ADMIN: Administrator role.
        MEMBER: Member role.
    """

    ADMIN = "admin"
    MEMBER = "member"


class CollaboratorModel(TypedDict):
    """Represents the structure of a project collaborator in the QFieldCloud system.

    Attributes:
        collaborator: The collaborator's identifier.
        role: The role of the collaborator.
        project_id: The associated project identifier.
        created_by: The user who created the collaborator entry.
        updated_by: The user who last updated the collaborator entry.
        created_at: The timestamp when the collaborator entry was created.
        updated_at: The timestamp when the collaborator entry was last updated.
    """

    collaborator: str
    role: ProjectCollaboratorRole
    project_id: str
    created_by: str
    updated_by: str
    created_at: datetime.datetime
    updated_at: datetime.datetime


class OrganizationMemberModel(TypedDict):
    """Represents the structure of an organization member in the QFieldCloud system.

    Attributes:
        member: The member's identifier.
        role: The role of the member.
        organization: The associated organization identifier.
        is_public: A boolean indicating if the membership is public.
    """

    member: str
    role: OrganizationMemberRole
    organization: str
    is_public: bool
    # TODO future work that can be surely expected, check QF-4535
    # created_by: str
    # updated_by: str
    # created_at: datetime.datetime
    # updated_at: datetime.datetime


class Pagination:
    """The Pagination class allows for controlling and managing pagination of results within the QFieldCloud SDK.

    Args:
        limit: The maximum number of items to return. Defaults to None.
        offset: The starting point from which to return items. Defaults to None.

    Attributes:
        limit: The maximum number of items to return.
        offset: The starting point from which to return items.
    """

    limit: Optional[int] = None
    offset: Optional[int] = None

    def __init__(
        self, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> None:
        self.limit = limit
        self.offset = offset

    @property
    def is_empty(self) -> bool:
        """Whether both limit and offset are None, indicating no pagination settings.

        Returns:
            True if both limit and offset are None, False otherwise.
        """
        return self.limit is None and self.offset is None


class Client:
    """The core component of the QFieldCloud SDK, providing methods for interacting with the QFieldCloud platform.

    The client provides methods for authentication, project management, file management, and more.

    It is configured with retries for GET requests on specific 5xx HTTP status codes.

    Args:
        url: The base URL for the QFieldCloud API. Defaults to `QFIELDCLOUD_URL` environment variable if empty.
        verify_ssl: Whether to verify SSL certificates. Defaults to True.
        token: The authentication token for API access. Defaults to `QFIELDCLOUD_TOKEN` environment variable if empty.

    Raises:
        QfcException: If the `url` is not provided either directly or through the environment variable.

    Attributes:
        session: The session object to maintain connections.
        url: The base URL for the QFieldCloud API.
        token: The authentication token for API access.
        verify_ssl: Whether to verify SSL certificates.
    """

    session: requests.Session

    url: str

    token: str

    verify_ssl: bool

    def __init__(
        self,
        url: str = "",
        verify_ssl: bool = True,
        token: str = "",
    ) -> None:
        self.session = requests.Session()
        # retries should be only on GET and only if error 5xx
        retries = Retry(
            total=5,
            backoff_factor=0.1,
            allowed_methods=["GET"],
            # skip 501, as it is "Not Implemented", no point to retry
            status_forcelist=[500, 502, 503, 504],
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

        self.url = url or os.environ.get("QFIELDCLOUD_URL", "")
        self.token = token or os.environ.get("QFIELDCLOUD_TOKEN", "")
        self.verify_ssl = verify_ssl

        if not self.verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        if not self.url:
            raise QfcException(
                "Cannot create a new QFieldCloud client without a url passed in the constructor or as environment variable QFIELDCLOUD_URL"
            )

    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Logs in with the provided username and password.

        Args:
            username: The username or email used to register.
            password: The password associated with the username.

        Returns:
            Authentication token and additional metadata.

        Example:
            client = sdk.Client(url="https://app.qfield.cloud/api/v1/")
            client.login("ninjamaster", "secret_password123")
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
        """Logs out from the current session, invalidating the authentication token.

        Example:
            client.logout()
        """
        resp = self._request("POST", "auth/logout")

        return resp.json()

    def list_projects(
        self,
        include_public: bool = False,
        pagination: Pagination = Pagination(),
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """List projects accessible by the current user. Optionally include all public projects.

        Args:
            include_public: Whether to include public projects in the list. Defaults to False.
            pagination: Pagination settings for the request. Defaults to an empty Pagination instance.

        Returns:
            A list of dictionaries containing project details.
        """
        params = {
            "include-public": str(int(include_public)),  # type: ignore
        }

        payload = self._request_json(
            "GET", "projects", params=params, pagination=pagination
        )
        return cast(List, payload)

    def list_remote_files(
        self, project_id: str, skip_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """List project files.

        Args:
            project_id: Project ID.
            skip_metadata: Whether to skip fetching metadata for the files. Defaults to True.

        Returns:
            A list of file details.

        Example:
            client.list_remote_files("project_id", True)
        """
        params = {}

        if skip_metadata:
            params["skip_metadata"] = "1"

        resp = self._request("GET", f"files/{project_id}", params=params)
        remote_files = resp.json()
        # TODO remove this temporary decoration with `etag` key
        remote_files = list(map(lambda f: {"etag": f["md5sum"], **f}, remote_files))

        return remote_files

    def create_project(
        self,
        name: str,
        owner: Optional[str] = None,
        description: str = "",
        is_public: bool = False,
    ) -> Dict[str, Any]:
        """Create a new project.

        Args:
            name: The name of the new project.
            owner: The owner of the project. When None, the project will be owned by the currently logged-in user. Defaults to None.
            description: A description of the project. Defaults to an empty string.
            is_public: Whether the project should be public. Defaults to False.

        Returns:
            A dictionary containing the details of the created project.
        """
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

    def delete_project(self, project_id: str) -> requests.Response:
        """Delete a project.

        Args:
            project_id: Project ID.

        Returns:
            The response object from the file delete request.
        """
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
        """Upload files to a QFieldCloud project.

        Args:
            project_id: Project ID.
            upload_type: The type of file transfer (PROJECT or PACKAGE).
            project_path: The local directory containing the files to upload.
            filter_glob: A glob pattern to filter which files to upload.
            throw_on_error: Whether to raise an error if a file fails to upload. Defaults to False.
            show_progress: Whether to display a progress bar during upload. Defaults to False.
            force: Whether to force upload all files, even if they exist remotely. Defaults to False.
            job_id: The job ID, required if `upload_type` is PACKAGE. Defaults to an empty string.

        Returns:
            A list of dictionaries with information about the uploaded files.
        """
        if not filter_glob:
            filter_glob = "*"

        local_files = self.list_local_files(project_path, filter_glob)

        for file in local_files:
            is_valid_filepath(file["name"])
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

                    etag = calc_etag(local_file["absolute_filename"])
                    if remote_file and remote_file.get("etag", None) == etag:
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
        """Upload a single file to a project.

        Args:
            project_id: Project ID.
            upload_type: The type of file transfer.
            local_filename: The path to the local file to upload.
            remote_filename: The path where the file should be stored remotely.
            show_progress: Whether to display a progress bar during upload.
            job_id: The job ID, required if `upload_type` is PACKAGE. Defaults to an empty string.

        Returns:
            The response object from the upload request.
        """
        is_valid_filepath(str(local_filename))

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
                logger.info(f'Uploading file "{remote_filename}"…')

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
        filter_glob: str = "*",
        throw_on_error: bool = False,
        show_progress: bool = False,
        force_download: bool = False,
    ) -> List[Dict]:
        """Download the specified project files into the destination dir.

        Args:
            project_id: Project ID.
            local_dir: destination directory where the files will be downloaded
            filter_glob: if specified, download only project files which match the glob, otherwise download all
            throw_on_error: Throw if download error occurres. Defaults to False.
            show_progress: Show progress bar in the console. Defaults to False.
            force_download: Download file even if it already exists locally. Defaults to False.

        Returns:
            A list of dictionaries with information about the downloaded files.
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

    def list_jobs(
        self,
        project_id: str,
        job_type: Optional[JobTypes] = None,
        pagination: Pagination = Pagination(),
    ) -> List[Dict[str, Any]]:
        """List project jobs.

        Args:
            project_id: Project ID.
            job_type: The type of job to filter by. If set to None, list all jobs. Defaults to None.
            pagination: Pagination settings. Defaults to a new Pagination object.

        Returns:
            A list of dictionaries representing the jobs.
        """
        payload = self._request_json(
            "GET",
            "jobs/",
            {
                "project_id": project_id,
                "type": job_type.value if job_type else None,
            },
            pagination=pagination,
        )
        return cast(List, payload)

    def job_trigger(
        self, project_id: str, job_type: JobTypes, force: bool = False
    ) -> Dict[str, Any]:
        """Trigger a new job for given project.

        Args:
            project_id: Project ID.
            job_type (JobTypes): The type of job to trigger.
            force: Whether to force the job execution. Defaults to False.

        Returns:
            A dictionary containing the job information.
        """
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
        """Get the status of a job.

        Args:
            job_id: The ID of the job.

        Returns:
            A dictionary containing the job status.
        """
        resp = self._request("GET", f"jobs/{job_id}")

        return resp.json()

    def delete_files(
        self,
        project_id: str,
        glob_patterns: List[str],
        throw_on_error: bool = False,
        finished_cb: Optional[Callable] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Delete project files.

        Args:
            project_id: Project ID.
            glob_patterns (list[str]): Delete only files matching one the glob patterns.
            throw_on_error: Throw if delete error occurres. Defaults to False.
            finished_cb (Callable, optional): Deprecated. Defaults to None.

        Raises:
            QFieldCloudException: if throw_on_error is True, throw an error if a download request fails.

        Returns:
            Deleted files by glob pattern.
        """
        project_files = self.list_remote_files(project_id)
        glob_results: Dict[str, List[Dict[str, Any]]] = {}

        log(f"Project '{project_id}' has {len(project_files)} file(s).")

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
                log(f"Glob pattern '{glob_pattern}' did not match any files.")
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

                    logger.info(
                        f"{resp.request.method} {resp.url} got HTTP {resp.status_code}"
                    )

                    file["status"] = FileTransferStatus.FAILED
                    file["error"] = err

                    log(f'File "{file["name"]}" failed to delete:\n{file["error"]}')

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
                log(f'{file["status"]}\t{file["name"]}')

                if file["status"] == FileTransferStatus.SUCCESS:
                    files_deleted += 1
                elif file["status"] == FileTransferStatus.SUCCESS:
                    files_failed += 1

        log(f"{files_deleted} file(s) deleted, {files_failed} file(s) failed to delete")

        return glob_results

    def package_latest(self, project_id: str) -> Dict[str, Any]:
        """Check the latest packaging status of a project.

        Args:
            project_id: Project ID.

        Returns:
            A dictionary containing the latest packaging status.
        """
        resp = self._request("GET", f"packages/{project_id}/latest/")

        return resp.json()

    def package_download(
        self,
        project_id: str,
        local_dir: str,
        filter_glob: str = "*",
        throw_on_error: bool = False,
        show_progress: bool = False,
        force_download: bool = False,
    ) -> List[Dict]:
        """Download the specified project packaged files into the destination dir.

        Args:
            project_id: Project ID.
            local_dir: destination directory where the files will be downloaded
            filter_glob: if specified, download only packaged files which match the glob, otherwise download all
            throw_on_error: Throw if download error occurres. Defaults to False.
            show_progress: Show progress bar in the console. Defaults to False.
            force_download: Download file even if it already exists locally. Defaults to False.

        Returns:
            A list of dictionaries with information about the downloaded files.
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
        filter_glob: str = "*",
        throw_on_error: bool = False,
        show_progress: bool = False,
        force_download: bool = False,
    ) -> List[Dict]:
        """Download project files.

        Args:
            files : A list of file dicts, specifying which files to download.
            project_id: Project ID.
            download_type: File transfer type which specifies what should be the download url.
            local_dir: Local destination directory
            filter_glob: Download only files matching the glob pattern. If None download all. Defaults to None.
            throw_on_error: Throw if download error occurres. Defaults to False.
            show_progress: Show progress bar in the console. Defaults to False.
            force_download: Download file even if it already exists locally. Defaults to False.

        Raises:
            QFieldCloudException: if throw_on_error is True, throw an error if a download request fails.

        Returns:
            A list of file dicts.
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
            etag = None
            if not force_download:
                etag = file.get("etag", None)

            try:
                self.download_file(
                    project_id,
                    download_type,
                    local_filename,
                    file["name"],
                    show_progress,
                    etag,
                )
                file["status"] = FileTransferStatus.SUCCESS
            except QfcRequestException as err:
                resp = err.response

                logger.info(
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
        remote_etag: Optional[str] = None,
    ) -> Optional[requests.Response]:
        """Download a single project file.

        Args:
            project_id: Project ID.
            download_type: File transfer type which specifies what should be the download URL
            local_filename: Local filename
            remote_filename: Remote filename
            show_progress: Show progressbar in the console
            remote_etag: The ETag of the remote file. If is None, the download of the file happens even if it already exists locally. Defaults to `None`.

        Raises:
            NotImplementedError: Raised if unknown `download_type` is passed

        Returns:
            The response object.
        """

        if remote_etag and local_filename.exists():
            if calc_etag(str(local_filename)) == remote_etag:
                if show_progress:
                    print(
                        f"{remote_filename}: Already present locally. Download skipped."
                    )
                else:
                    logger.info(
                        f'Skipping download of "{remote_filename}" because it is already present locally'
                    )
                return None

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
                logger.info(f'Downloading file "{remote_filename}"…')

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

    def get_project_collaborators(self, project_id: str) -> List[CollaboratorModel]:
        """Gets a list of project collaborators.

        Args:
            project_id: Project ID.

        Returns:
            The list of project collaborators.
        """
        collaborators = cast(
            List[CollaboratorModel],
            self._request_json("GET", f"/collaborators/{project_id}"),
        )

        return collaborators

    def add_project_collaborator(
        self, project_id: str, username: str, role: ProjectCollaboratorRole
    ) -> CollaboratorModel:
        """Adds a project collaborator.

        Args:
            project_id: Project ID.
            username: username of the collaborator to be added
            role: the role of the collaborator. One of: `reader`, `reporter`, `editor`, `manager` or `admin`

        Returns:
            The added project collaborator.
        """
        collaborator = cast(
            CollaboratorModel,
            self._request_json(
                "POST",
                f"/collaborators/{project_id}",
                {
                    "collaborator": username,
                    "role": role,
                },
            ),
        )

        return collaborator

    def remove_project_collaborator(self, project_id: str, username: str) -> None:
        """Removes a project collaborator.

        Args:
            project_id: Project ID.
            username: the username of the collaborator to be removed
        """
        self._request("DELETE", f"/collaborators/{project_id}/{username}")

    def patch_project_collaborators(
        self, project_id: str, username: str, role: ProjectCollaboratorRole
    ) -> CollaboratorModel:
        """Change an already existing project collaborator.

        Args:
            project_id: Project ID.
            username: the username of the collaborator to be patched
            role: the new role of the collaborator

        Returns:
            The updated project collaborator.
        """
        collaborator = cast(
            CollaboratorModel,
            self._request_json(
                "PATCH",
                f"/collaborators/{project_id}/{username}",
                {
                    "role": role,
                },
            ),
        )

        return collaborator

    def get_organization_members(
        self, organization: str
    ) -> List[OrganizationMemberModel]:
        """Gets a list of organization members.

        Args:
            organization: organization username

        Returns:
            The list of organization members.
        """
        members = cast(
            List[OrganizationMemberModel],
            self._request_json("GET", f"/members/{organization}"),
        )

        return members

    def add_organization_member(
        self,
        organization: str,
        username: str,
        role: OrganizationMemberRole,
        is_public: bool,
    ) -> OrganizationMemberModel:
        """Adds an organization member.

        Args:
            organization: organization username
            username: username of the member to be added
            role: the role of the member. One of: `admin` or `member`.
            is_public: whether the membership should be public.

        Returns:
            The added organization member.
        """
        member = cast(
            OrganizationMemberModel,
            self._request_json(
                "POST",
                f"/members/{organization}",
                {
                    "member": username,
                    "role": role,
                    "is_public": is_public,
                },
            ),
        )

        return member

    def remove_organization_members(self, project_id: str, username: str) -> None:
        """Removes an organization member.

        Args:
            project_id: Project ID.
            username: the username of the member to be removed
        """
        self._request("DELETE", f"/members/{project_id}/{username}")

    def patch_organization_members(
        self, project_id: str, username: str, role: OrganizationMemberRole
    ) -> OrganizationMemberModel:
        """Change an already existing organization member.

        Args:
            project_id: Project ID.
            username: the username of the member to be patched
            role: the new role of the member

        Returns:
            The updated organization member.
        """
        member = cast(
            OrganizationMemberModel,
            self._request_json(
                "PATCH",
                f"/members/{project_id}/{username}",
                {
                    "role": role,
                },
            ),
        )

        return member

    def _request_json(
        self,
        method: str,
        path: str,
        data: Any = None,
        params: Dict[str, str] = {},
        headers: Dict[str, str] = {},
        files: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        skip_token: bool = False,
        allow_redirects=None,
        pagination: Pagination = Pagination(),
    ) -> Union[List, Dict]:
        result: Optional[Union[List, Dict]] = None
        is_empty_pagination = pagination.is_empty

        while True:
            resp = self._request(
                method,
                path,
                data,
                params,
                headers,
                files,
                stream,
                skip_token,
                allow_redirects,
                pagination,
            )

            payload = resp.json()

            if isinstance(payload, list):
                result = cast(List, result)

                if result:
                    result += payload
                else:
                    result = payload
            elif isinstance(payload, dict):
                result = cast(Dict, result)

                if result:
                    result = {**result, **payload}
                else:
                    result = payload
            else:
                raise NotImplementedError(
                    "Unsupported data type for paginated response."
                )

            if not is_empty_pagination:
                break

            next_url = resp.headers.get("X-Next-Page")
            if not next_url:
                break

            query_params = urlparse.parse_qs(urlparse.urlparse(next_url).query)
            pagination = Pagination(
                limit=cast(int, query_params["limit"]),
                offset=cast(int, query_params["offset"]),
            )

        return result

    def _request(
        self,
        method: str,
        path: str,
        data: Any = None,
        params: Dict[str, str] = {},
        headers: Dict[str, str] = {},
        files: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        skip_token: bool = False,
        allow_redirects=None,
        pagination: Optional[Pagination] = None,
    ) -> requests.Response:
        method = method.upper()
        headers_copy = {**headers}

        assert self.url

        allow_redirects = method != "POST"

        if not skip_token and self.token:
            headers_copy["Authorization"] = f"token {self.token}"

        headers_copy["User-Agent"] = (
            f"sdk|py|{__version__} python-requests|{metadata.version('requests')}"
        )

        if not path.startswith("http"):
            if path.startswith("/"):
                path = path[1:]

            if not path.endswith("/"):
                path += "/"

            path = self.url + path

        if pagination:
            limit = pagination.limit or DEFAULT_PAGINATION_LIMIT
            offset = pagination.offset or 0
            params = {
                **params,
                "limit": str(limit),
                "offset": str(offset),
            }

        request_params = {
            "method": method,
            "url": path,
            "data": data,
            "params": params,
            "headers": headers_copy,
            "files": files,
        }

        request = QfcRequest(**request_params)

        session_params = {
            "stream": stream,
            "verify": self.verify_ssl,
            # redirects from POST requests automagically turn into GET requests, so better forbid redirects
            "allow_redirects": allow_redirects,
        }

        if os.environ.get("ENVIRONMENT") == "test":
            return request.mock_response()
        else:
            response = self.session.send(request.prepare(), **session_params)

        try:
            response.raise_for_status()
        except Exception as err:
            raise QfcRequestException(response) from err

        return response
