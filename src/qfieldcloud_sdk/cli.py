#!/bin/env python3

import collections
import json
import platform
import sys
from enum import Enum

import click

from qfieldcloud_sdk import sdk

QFIELDCLOUD_DEFAULT_URL = "https://app.qfield.cloud/api/v1/"


class OutputFormat(Enum):
    HUMAN = "HUMAN"
    JSON = "JSON"


def print_json(data):
    print(json.dumps(data, sort_keys=True, indent=2))


def log(*msgs):
    print(*msgs, file=sys.stderr)


class OrderedGroup(click.Group):
    def __init__(self, name=None, commands=None, **attrs):
        super(OrderedGroup, self).__init__(name, commands, **attrs)
        self.commands = commands or collections.OrderedDict()

    def __call__(self, *args, **kwargs):
        try:
            return self.main(*args, **kwargs)
        except sdk.QfcRequestException as err:
            click.echo(str(err))
        except sdk.QfcException as err:
            click.echo(str(err))

    def list_commands(self, ctx):
        return self.commands


@click.group(cls=OrderedGroup)
@click.option(
    "-U",
    "--url",
    envvar="QFIELDCLOUD_URL",
    default=QFIELDCLOUD_DEFAULT_URL,
    type=str,
    help=f"URL to the QFieldCloud API endpoint. If not passed, gets the value from QFIELDCLOUD_URL environment variable. Default: {QFIELDCLOUD_DEFAULT_URL}",
)
@click.option(
    "-u",
    "--username",
    envvar="QFIELDCLOUD_USERNAME",
    type=str,
    help="Username or email.",
)
@click.option("-p", "--password", envvar="QFIELDCLOUD_PASSWORD", type=str)
@click.option(
    "-t", "--token", envvar="QFIELDCLOUD_TOKEN", type=str, help="Session token."
)
@click.option(
    "--json/--human",
    "format_json",
    help="Output the result as newline formatted json. Default: False",
)
@click.option(
    "--verify-ssl/--no-verify-ssl",
    "verify_ssl",
    default=True,
    envvar="QFIELDCLOUD_VERIFY_SSL",
    help="Verify SSL. Default: True",
)
@click.version_option(sdk.__version__)
@click.pass_context
def cli(
    ctx: click.Context,
    url: str,
    username: str,
    password: str,
    token: str,
    format_json: bool,
    verify_ssl: bool,
):
    """The official QFieldCloud CLI tool. Allows interaction with the QFieldCloud server API.

    Environment:

        Environment variables can be used instead of passing some common global options.

        QFIELDCLOUD_API - QFieldCloud API endpoint URL

        QFIELDCLOUD_USERNAME - QFieldCloud username or email. Requires `QFIELDCLOUD_PASSWORD` to be set.

        QFIELDCLOUD_PASSWORD - Password. Requires `QFIELDCLOUD_USERNAME` to be set.

        QFIELDCLOUD_TOKEN - Token that can be used instead of passing username and password. It can be obtained by running `qfieldcloud-cli login`.

        QFIELDCLOUD_VERIFY_SSL - When set to `0` has the same effect as passing `--no-verify-ssl`.


    Examples:

        qfieldcloud-cli login user pass

        qfieldcloud-cli -u user -p pass -U https://localhost/api/v1/ list-projects
    """
    ctx.ensure_object(dict)
    ctx.obj["client"] = sdk.Client(url, verify_ssl, token=token)
    ctx.obj["format_json"] = format_json

    if username or password:
        ctx.obj["client"].login(username, password)


@cli.command()
@click.argument("username", envvar="QFIELDCLOUD_USERNAME", required=True)
@click.argument("password", envvar="QFIELDCLOUD_PASSWORD", required=True)
@click.pass_context
def login(ctx, username, password) -> None:
    """Login to QFieldCloud."""

    log(f"Log in {username}…")

    user_data = ctx.obj["client"].login(username, password)

    if ctx.obj["format_json"]:
        print_json(user_data)
    else:
        log(f'Welcome to QFieldCloud, {user_data["username"]}.')
        log(
            "QFieldCloud has generated a secret token to identify you. "
            "Put the token in your in the environment using the following code, "
            "so you do not need to write your username and password again:"
        )
        if platform.system() == "Windows":
            log(f'set QFIELDCLOUD_TOKEN={user_data["token"]}')
        else:
            log(f'export QFIELDCLOUD_TOKEN="{user_data["token"]}"')


@cli.command()
@click.pass_context
def logout(ctx):
    """Logout and expire the token."""

    log("Log out…")

    payload = ctx.obj["client"].logout()

    if ctx.obj["format_json"]:
        print_json(payload)
    else:
        log(payload["detail"])


@cli.command()
@click.option(
    "--include-public/--no-public",
    default=False,
    help="Includes the public project in the list. Default: False",
)
@click.pass_context
def list_projects(ctx, include_public):
    """List QFieldCloud projects."""

    log("Listing projects…")

    projects = ctx.obj["client"].list_projects(
        include_public=include_public,
    )

    if ctx.obj["format_json"]:
        print_json(projects)
    else:
        if projects:
            log("Projects:")
            for project in projects:
                log(f'{project["id"]}\t{project["owner"]}/{project["name"]}')
        else:
            log("User does not have any projects yet.")


@cli.command()
@click.argument("project_id")
@click.pass_context
def list_files(ctx, project_id):
    """List QFieldCloud project files."""

    log(f'Getting file list for "{project_id}"…')

    files = ctx.obj["client"].list_remote_files(project_id)

    if ctx.obj["format_json"]:
        print_json(files)
    else:
        if files:
            log(f'Files for project "{project_id}":')
            for file in files:
                log(f'{file["last_modified"]}\t{file["name"]}')
        else:
            log(f'No files within project "{project_id}"')


@cli.command()
@click.argument("name")
@click.option(
    "--owner",
    "owner",
    help="Owner of the project. If omitted, the current user is the owner.",
)
@click.option("--description", "description", help="Description of the project.")
@click.option(
    "--is-public/--is-private", "is_public", help="Mark the project as public."
)
@click.pass_context
def create_project(ctx, name, owner, description, is_public):
    """Creates a new empty QFieldCloud project."""

    log("Creating project {}…".format(f"{owner}/{name}" if owner else name))

    project = ctx.obj["client"].create_project(
        name, owner, description=description, is_public=is_public
    )

    if ctx.obj["format_json"]:
        print_json(project)
    else:
        log(
            f'Created project "{project["owner"]}/{project["name"]}" with project id "{project["id"]}".'
        )


@cli.command()
@click.argument("project_id")
@click.pass_context
def delete_project(ctx, project_id):
    """Deletes a QFieldCloud project."""

    log(f'Deleting project "{project_id}"…')

    payload = ctx.obj["client"].delete_project(project_id)

    if ctx.obj["format_json"]:
        # print_json(payload)
        print(payload, payload.content)
    else:
        log(f'Delеted project "{project_id}".')


@cli.command()
@click.argument("project_id")
@click.argument("project_path")
@click.option(
    "--filter",
    "filter_glob",
    help="Do not upload the whole project, but only the files which match the glob.",
)
@click.option(
    "--throw-on-error/--no-throw-on-error",
    help="If any project file upload fails stop uploading the rest. Default: False",
)
@click.pass_context
def upload_files(ctx, project_id, project_path, filter_glob, throw_on_error):
    """Upload files to a QFieldCloud project."""

    log(f'Uploading files "{project_id}" from {project_path}…')

    files = ctx.obj["client"].upload_files(
        project_id,
        sdk.FileTransferType.PROJECT,
        project_path,
        filter_glob=filter_glob,
        throw_on_error=throw_on_error,
        show_progress=True,
    )

    if ctx.obj["format_json"]:
        print_json(files)
    else:
        if files:
            log(f"Upload finished after uploading {len(files)}.")
            for file in files:
                if file.get("error"):
                    log(f'File "{file["name"]}" failed to upload: {file["error"]} .')
        else:
            log("Nothing to upload.")


@cli.command()
@click.argument("project_id")
@click.argument("local_dir")
@click.option(
    "--filter",
    "filter_glob",
    help="Do not download the whole project, but only the files which match the glob.",
)
@click.option(
    "--throw-on-error/--no-throw-on-error",
    help="If any project file downloads fails stop downloading the rest. Default: False",
)
@click.option(
    "--force-download/--no-force-download",
    help="Download file even if it already exists locally. Default: False",
)
@click.pass_context
def download_files(
    ctx, project_id, local_dir, filter_glob, throw_on_error, force_download
):
    """Download QFieldCloud project files."""

    log(f'Downloading project "{project_id}" files to {local_dir}…')

    files = ctx.obj["client"].download_project(
        project_id,
        local_dir,
        filter_glob,
        throw_on_error,
        show_progress=True,
        force_download=force_download,
    )

    if ctx.obj["format_json"]:
        print_json(files)
    else:
        if files:
            count = 0
            for file in files:
                if file.get("error"):
                    log(f'File "{file["name"]}" failed to download: {file["error"]} .')
                else:
                    count += 1

            log(f"Downloaded {count} file(s).")
        else:
            if filter_glob:
                log(f"No files to download for project {project_id} at {filter_glob}")
            else:
                log(f"No files to download for project {project_id}")


@cli.command()
@click.argument("project_id")
@click.argument("paths", nargs=-1, required=True)
@click.option(
    "--throw-on-error/--no-throw-on-error",
    help="If any project file delete operations fails stop, stop deleting the rest. Default: False",
)
@click.pass_context
def delete_files(ctx, project_id, paths, throw_on_error):
    """Delete QFieldCloud project files."""

    log(f'Deleting project "{project_id}" files…')

    paths_result = ctx.obj["client"].delete_files(project_id, paths, throw_on_error)

    if ctx.obj["format_json"]:
        print_json(paths_result)


@cli.command()
@click.argument("project_id")
@click.option(
    "--type",
    "job_type",
    type=sdk.JobTypes,
    help="Job type. One of package, delta_apply or process_projectfile.",
)
@click.pass_context
def list_jobs(ctx, project_id, job_type):
    """List project jobs."""

    log(f'Listing project "{project_id}" jobs…')

    jobs = ctx.obj["client"].list_jobs(project_id, job_type)

    if ctx.obj["format_json"]:
        print_json(jobs)
    else:
        for job in jobs:
            log(
                f'Job "{job["id"]}" of project "{project_id}" is of type "{job["type"]}" and has status "{job["status"]}".'
            )


@cli.command()
@click.argument("project_id")
@click.argument("job_type", type=sdk.JobTypes)
@click.option(
    "--force/--no-force",
    default=False,
    help="Should force creating a new job. Default: False",
)
@click.pass_context
def job_trigger(ctx, project_id, job_type, force):
    """Triggers a new job."""

    log(f'Triggering "{job_type}" job for project "{project_id}"…')

    status = ctx.obj["client"].job_trigger(project_id, job_type, force)

    if ctx.obj["format_json"]:
        print_json(status)
    else:
        log(
            f'Job of type "{job_type}" triggered for project "{project_id}": {status["id"]}'
        )


@cli.command()
@click.argument("job_id")
@click.pass_context
def job_status(ctx, job_id):
    """Get job status."""

    log(f'Getting job "{job_id}" status…')

    status = ctx.obj["client"].job_status(job_id)

    if ctx.obj["format_json"]:
        print_json(status)
    else:
        log(f'Job status for {job_id}: {status["status"]}')


@cli.command()
@click.argument("project_id")
@click.pass_context
def package_latest(ctx, project_id):
    """Check project packaging status."""

    log(f'Getting the latest project "{project_id}" package info…')

    status = ctx.obj["client"].package_latest(project_id)

    if ctx.obj["format_json"]:
        print_json(status)
    else:
        log(f'Packaging status for {project_id}: {status["status"]}')
        if status["layers"] is None:
            if status["status"] == "failed":
                log("Packaging have never been triggered on this project. Please run:")
                log(f"qfieldcloud-cli job-trigger {project_id} package")
            return

        for layer_obj in status["layers"].values():
            if layer_obj["is_valid"]:
                log(
                    f'Layer "{layer_obj["name"]}" is valid, finished with status: {layer_obj["error_code"]}'
                )
            else:
                log(
                    f'Invalid layer "{layer_obj["name"]}", status: {layer_obj["error_code"]}'
                )


@cli.command()
@click.argument("project_id")
@click.argument("local_dir")
@click.option(
    "--filter",
    "filter_glob",
    help="Do not download the whole packaged project, but only the files which match the glob.",
)
@click.option(
    "--throw-on-error/--no-throw-on-error",
    help="If any packaged file downloads fails stop downloading the rest. Default: False",
)
@click.option(
    "--force-download/--no-force-download",
    help="Download file even if it already exists locally. Default: False",
)
@click.pass_context
def package_download(
    ctx, project_id, local_dir, filter_glob, throw_on_error, force_download
):
    """Download packaged QFieldCloud project files."""

    log(f'Downloading the latest project "{project_id}" package files to {local_dir}…')

    files = ctx.obj["client"].package_download(
        project_id,
        local_dir,
        filter_glob,
        throw_on_error,
        show_progress=True,
        force_download=force_download,
    )

    if ctx.obj["format_json"]:
        print_json(files)
    else:
        if files:
            log(f"Download status of packaged files in project {project_id}:")
            for file in files:
                log(f'{file["status"].value}\t{file["name"]}')
        else:
            if filter_glob:
                log(
                    f"No packaged files to download for project {project_id} at {filter_glob}"
                )
            else:
                log(f"No packaged files to download for project {project_id}")


if __name__ == "__main__":
    cli()
