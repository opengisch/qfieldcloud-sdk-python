import collections
import platform
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, TypedDict

import click

from . import sdk
from .utils import format_project_table, log, print_json

QFIELDCLOUD_DEFAULT_URL = "https://app.qfield.cloud/api/v1/"


class OutputFormat(Enum):
    HUMAN = "HUMAN"
    JSON = "JSON"


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


class ContextObject(TypedDict):
    client: sdk.Client
    format_json: bool


class Context(Protocol):
    obj: ContextObject


def paginated(command):
    command = click.option(
        "-o",
        "--offset",
        type=int,
        default=None,
        is_flag=False,
        help="Offsets the given number of records in the paginated JSON response.",
    )(command)
    command = click.option(
        "-l",
        "--limit",
        type=int,
        default=None,
        is_flag=False,
        help="Limits the number of records to return in the paginated JSON response.",
    )(command)
    return command


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

        QFIELDCLOUD_URL - QFieldCloud API endpoint URL

        QFIELDCLOUD_USERNAME - QFieldCloud username or email. Requires `QFIELDCLOUD_PASSWORD` to be set.

        QFIELDCLOUD_PASSWORD - Password. Requires `QFIELDCLOUD_USERNAME` to be set.

        QFIELDCLOUD_TOKEN - Token that can be used instead of passing username and password. It can be obtained by running `qfieldcloud-cli login`.

        QFIELDCLOUD_VERIFY_SSL - When set to `0` has the same effect as passing `--no-verify-ssl`.


    Examples:

        qfieldcloud-cli login user pass

        qfieldcloud-cli -u user -p pass -U https://app.qfield.cloud/api/v1/ list-projects
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
def login(ctx: Context, username, password) -> None:
    """Login to QFieldCloud."""

    user_data = ctx.obj["client"].login(username, password)

    if ctx.obj["format_json"]:
        print_json(user_data)
    else:
        log(f"Log in {username}…")
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

    payload = ctx.obj["client"].logout()

    if ctx.obj["format_json"]:
        print_json(payload)
    else:
        log("Log out…")
        log(payload["detail"])


@cli.command()
@click.pass_context
def status(ctx: Context):
    """Check the status of the QFieldCloud server."""
    log("Checking server status...")
    client: sdk.Client = ctx.obj["client"]
    is_json: bool = ctx.obj["format_json"]

    status_info = client.check_server_status()

    if is_json:
        print_json(status_info)
    else:
        log(click.style("Server Status:", bold=True))

        if isinstance(status_info, dict):
            for key, value in status_info.items():
                log(f"  {key.replace('_', ' ').capitalize()}: {value}")
        else:
            log(str(status_info))


@cli.command()
@paginated
@click.option(
    "--include-public/--no-public",
    default=False,
    is_flag=True,
    help="Includes the public project in the list. Default: False",
)
@click.pass_context
def list_projects(ctx: Context, include_public: bool, **opts) -> None:
    """List QFieldCloud projects."""

    projects: List[Dict[str, Any]] = ctx.obj["client"].list_projects(
        include_public,
        sdk.Pagination(**opts),
    )

    if ctx.obj["format_json"]:
        print_json(projects)
    else:
        log("Listing projects…")
        if projects:
            log("Projects the current user has access to:")
            log(format_project_table(projects))
        else:
            log("User does not have any projects yet.")


@cli.command()
@click.argument("project_id")
@click.pass_context
def get_project(ctx: Context, project_id: str) -> None:
    """Get QFieldCloud project data."""

    project: Dict[str, Any] = ctx.obj["client"].get_project(project_id)

    if ctx.obj["format_json"]:
        print_json(project)
    else:
        if project:
            log("Project data:")
            log(format_project_table([project]))
        else:
            log("User does not have access to projects yet.")


@cli.command()
@click.argument("project_id")
@click.option(
    "--skip-metadata/--no-skip-metadata",
    "skip_metadata",
    default=True,
    help="Skip requesting for additional metadata (currently the `sha256` checksum) for each version. Default: --skip-metadata",
)
@click.pass_context
def list_files(ctx: Context, project_id, skip_metadata):
    """List QFieldCloud project files."""

    files = ctx.obj["client"].list_remote_files(project_id, skip_metadata)

    if ctx.obj["format_json"]:
        print_json(files)
    else:
        log(f'Getting file list for "{project_id}"…')
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
def create_project(ctx: Context, name, owner, description, is_public):
    """Creates a new empty QFieldCloud project."""

    project = ctx.obj["client"].create_project(
        name, owner, description=description, is_public=is_public
    )

    if ctx.obj["format_json"]:
        print_json(project)
    else:
        log("Creating project {}…".format(f"{owner}/{name}" if owner else name))
        log("Created project:")
        log(format_project_table([project]))


@cli.command()
@click.argument("project_id")
@click.pass_context
def delete_project(ctx: Context, project_id):
    """Deletes a QFieldCloud project."""

    payload = ctx.obj["client"].delete_project(project_id)

    if ctx.obj["format_json"]:
        # print_json(payload)
        print(payload, payload.content)
    else:
        log(f'Deleting project "{project_id}"…')
        log(f'Deleted project "{project_id}".')


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
def upload_files(ctx: Context, project_id, project_path, filter_glob, throw_on_error):
    """Upload files to a QFieldCloud project."""

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
        log(f'Uploading files "{project_id}" from {project_path}…')
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
    ctx: Context, project_id, local_dir, filter_glob, throw_on_error, force_download
):
    """Download QFieldCloud project files."""

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
        log(f'Downloading project "{project_id}" files to {local_dir}…')
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
@click.option(
    "--name",
    help="New project name",
)
@click.option(
    "--description",
    help="New project description",
)
@click.option(
    "--owner",
    help="Transfer the project to a new owner",
)
@click.option(
    "--is-public/--is-no-public",
    is_flag=True,
    help="Whether the project shall be public",
)
@click.pass_context
def patch_project(
    ctx: Context,
    project_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    owner: Optional[str] = None,
    is_public: Optional[bool] = None,
) -> None:
    """Patch the project with new data. Pass only the parameters that shall be changed."""

    project = ctx.obj["client"].patch_project(
        project_id, name=name, owner=owner, description=description, is_public=is_public
    )

    if ctx.obj["format_json"]:
        print_json(project)
    else:
        log("Patched project:")
        log(format_project_table([project]))


@cli.command()
@click.argument("project_id")
@click.argument("paths", nargs=-1, required=True)
@click.option(
    "--throw-on-error/--no-throw-on-error",
    help="If any project file delete operations fails stop, stop deleting the rest. Default: False",
)
@click.pass_context
def delete_files(ctx: Context, project_id, paths, throw_on_error):
    """Delete QFieldCloud project files."""

    paths_result = ctx.obj["client"].delete_files(project_id, paths, throw_on_error)

    if ctx.obj["format_json"]:
        print_json(paths_result)
    else:
        log(f'Deleting project "{project_id}" files…')


@cli.command()
@click.argument("project_id")
@click.option(
    "--type",
    "job_type",
    type=sdk.JobTypes,
    help="Job type. One of package, delta_apply or process_projectfile.",
)
@paginated
@click.pass_context
def list_jobs(ctx: Context, project_id, job_type: Optional[sdk.JobTypes], **opts):
    """List project jobs."""

    jobs: List[Dict] = ctx.obj["client"].list_jobs(
        project_id,
        job_type,
        sdk.Pagination(**opts),
    )

    if ctx.obj["format_json"]:
        print_json(jobs)
    else:
        log(f'Listing project "{project_id}" jobs…')
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
def job_trigger(ctx: Context, project_id, job_type, force):
    """Triggers a new job."""

    status = ctx.obj["client"].job_trigger(project_id, job_type, force)

    if ctx.obj["format_json"]:
        print_json(status)
    else:
        log(f'Triggering "{job_type}" job for project "{project_id}"…')
        log(
            f'Job of type "{job_type}" triggered for project "{project_id}": {status["id"]}'
        )


@cli.command()
@click.argument("job_id")
@click.pass_context
def job_status(ctx: Context, job_id):
    """Get job status."""

    status = ctx.obj["client"].job_status(job_id)

    if ctx.obj["format_json"]:
        print_json(status)
    else:
        log(f'Getting job "{job_id}" status…')
        log(f'Job status for {job_id}: {status["status"]}')


@cli.command(short_help="Push a delta file to a project.")
@click.argument("project_id")
@click.argument("delta_filename", type=click.Path(exists=True))
@click.pass_context
def delta_push(ctx: Context, project_id: str, delta_filename: str) -> None:
    """Push a delta file to a project with PROJECT_ID."""

    response = ctx.obj["client"].push_delta(project_id, delta_filename)

    if ctx.obj["format_json"]:
        print_json(response)
    else:
        log(f'Pushing delta file "{delta_filename}" to project "{project_id}"…')
        log(f'Delta file "{delta_filename}" pushed to project "{project_id}".')


@cli.command()
@click.argument("project_id")
@click.pass_context
def package_latest(ctx: Context, project_id):
    """Check project packaging status."""

    status = ctx.obj["client"].package_latest(project_id)

    if ctx.obj["format_json"]:
        print_json(status)
    else:
        log(f'Getting the latest project "{project_id}" package info…')
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
    ctx: Context, project_id, local_dir, filter_glob, throw_on_error, force_download
):
    """Download packaged QFieldCloud project files."""

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
        log(
            f'Downloading the latest project "{project_id}" package files to {local_dir}…'
        )
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


@cli.command(short_help="Get a list of project collaborators.")
@click.argument("project_id")
@click.pass_context
def collaborators_get(ctx: Context, project_id: str) -> None:
    """Get a list of project collaborators for specific project with PROJECT_ID."""
    collaborators = ctx.obj["client"].get_project_collaborators(project_id)

    if ctx.obj["format_json"]:
        print_json(collaborators)
    else:
        log(f'Collaborators for project with id "{project_id}":')
        for collaborator in collaborators:
            log(f'{collaborator["collaborator"]}\t{collaborator["role"]}')


@cli.command(short_help="Add a project collaborator.")
@click.argument("project_id")
@click.argument("username")
@click.argument("role", type=sdk.ProjectCollaboratorRole)
@click.pass_context
def collaborators_add(
    ctx: Context, project_id: str, username: str, role: sdk.ProjectCollaboratorRole
) -> None:
    """Add collaborator with USERNAME with specific ROLE to a project with PROJECT_ID. Possible ROLE values: admin, manager, editor, reporter, reader."""
    collaborator = ctx.obj["client"].add_project_collaborator(
        project_id, username, role
    )

    if ctx.obj["format_json"]:
        print_json(collaborator)
    else:
        log(
            f'Collaborator "{collaborator["collaborator"]}" added to project with id "{collaborator["project_id"]}" with role "{collaborator["role"]}".'
        )


@cli.command(short_help="Remove a project collaborator.")
@click.argument("project_id")
@click.argument("username")
@click.pass_context
def collaborators_remove(ctx: Context, project_id: str, username: str) -> None:
    """Remove collaborator with USERNAME from project with PROJECT_ID."""
    ctx.obj["client"].remove_project_collaborator(project_id, username)

    if not ctx.obj["format_json"]:
        log(f'Collaborator "{username}" removed project with id "{project_id}".')


@cli.command(short_help="Change project collaborator role.")
@click.argument("project_id")
@click.argument("username")
@click.argument("role", type=sdk.ProjectCollaboratorRole)
@click.pass_context
def collaborators_patch(
    ctx: Context, project_id: str, username: str, role: sdk.ProjectCollaboratorRole
) -> None:
    """Change collaborator with USERNAME to new ROLE in project with PROJECT_ID. Possible ROLE values: admin, manager, editor, reporter, reader."""
    collaborator = ctx.obj["client"].patch_project_collaborators(
        project_id, username, role
    )

    if ctx.obj["format_json"]:
        print_json(collaborator)
    else:
        log(
            f'Collaborator "{collaborator["collaborator"]}" added to project with id "{collaborator["project_id"]}" with role "{collaborator["role"]}".'
        )


@cli.command(short_help="Get a list organization members.")
@click.argument("organization")
@click.pass_context
def members_get(ctx: Context, organization: str) -> None:
    """Get a list of ORGANIZATION members."""
    memberships = ctx.obj["client"].get_organization_members(organization)

    if ctx.obj["format_json"]:
        print_json(memberships)
    else:
        log(f'Members of organization "{organization}":')
        for membership in memberships:
            log(f'{membership["member"]}\t{membership["role"]}')


@cli.command(short_help="Add an organization member.")
@click.argument("organization")
@click.argument("username")
@click.argument("role", type=sdk.OrganizationMemberRole)
@click.option("--public/--no-public", "is_public")
@click.pass_context
def members_add(
    ctx: Context,
    organization: str,
    username: str,
    role: sdk.OrganizationMemberRole,
    is_public: bool,
) -> None:
    """Add member with USERNAME with ROLE to ORGANIZATION. Possible ROLE values: admin, member."""
    membership = ctx.obj["client"].add_organization_member(
        organization, username, role, is_public
    )

    if ctx.obj["format_json"]:
        print_json(membership)
    else:
        log(
            f'Member "{membership["member"]}" added to organization "{membership["organization"]}" with role "{membership["role"]}".'
        )


@cli.command(short_help="Remove an organization member.")
@click.argument("organization")
@click.argument("username")
@click.pass_context
def members_remove(ctx: Context, organization: str, username: str) -> None:
    """Remove member with USERNAME from ORGANIZATION."""
    ctx.obj["client"].remove_organization_members(organization, username)

    if not ctx.obj["format_json"]:
        log(f'Member "{username}" removed organization "{organization}".')


@cli.command(short_help="Change organization member role.")
@click.argument("organization")
@click.argument("username")
@click.argument("role", type=sdk.OrganizationMemberRole)
@click.pass_context
def members_patch(
    ctx: Context, organization: str, username: str, role: sdk.OrganizationMemberRole
) -> None:
    """Change member with USERNAME to new ROLE in ORGANIZATION. Possible ROLE values: admin, member."""
    membership = ctx.obj["client"].patch_organization_members(
        organization, username, role
    )

    if ctx.obj["format_json"]:
        print_json(membership)
    else:
        log(
            f'Member "{membership["member"]}" changed role in organization "{membership["organization"]}" to role "{membership["role"]}".'
        )


@cli.command(short_help="Get a list of organization teams.")
@click.argument("organization")
@click.pass_context
def teams_list(ctx: Context, organization: str) -> None:
    """Get a list of organization teams."""
    teams_list = ctx.obj["client"].get_organization_teams(organization)

    if ctx.obj["format_json"]:
        print_json(teams_list)
    else:
        log(f'Teams members in organization "{organization}":')
        for object_team in teams_list:
            log(f'{object_team["team"]}')


@cli.command(name="teams-create", short_help="Create an organization team.")
@click.argument("organization")
@click.argument("team_name")
@click.pass_context
def teams_create(ctx: Context, organization: str, team_name: str) -> None:
    """Create a new team named TEAM_NAME in ORGANIZATION."""
    object_team = ctx.obj["client"].create_organization_team(organization, team_name)

    if ctx.obj["format_json"]:
        print_json(object_team)
    else:
        log(f'Team "{object_team["team"]}" created in organization "{organization}".')


@cli.command(name="teams-get", short_help="Get a list of teams on an organization.")
@click.argument("organization")
@click.argument("team_name")
@click.pass_context
def teams_get(ctx: Context, organization: str, team_name: str) -> None:
    """Get details of team TEAM_NAME in ORGANIZATION."""
    object_team = ctx.obj["client"].get_organization_team(organization, team_name)

    if ctx.obj["format_json"]:
        print_json(object_team)
    else:
        log(
            f'Team "{object_team["team"]}" in organization "{object_team["organization"]}":'
        )
        log(f'  Members: {", ".join(object_team["members"])}')


@cli.command(name="teams-patch", short_help="Rename an organization team.")
@click.argument("organization")
@click.argument("team_name")
@click.option("--name", "new_team_name")
@click.pass_context
def teams_patch(
    ctx: Context, organization: str, team_name: str, new_team_name: str
) -> None:
    """Rename team TEAM_NAME to NEW_TEAM_NAME in ORGANIZATION."""
    object_team = ctx.obj["client"].patch_organization_team(
        organization, team_name, new_team_name
    )

    if ctx.obj["format_json"]:
        print_json(object_team)
    else:
        log(
            f'Team "{team_name}" in organization "{organization}" was renamed to "{object_team["team"]}".'
        )


@cli.command(name="teams-delete", short_help="Delete an organization team.")
@click.argument("organization")
@click.argument("team_name")
@click.pass_context
def teams_delete(ctx: Context, organization: str, team_name: str) -> None:
    """Delete team TEAM_NAME from ORGANIZATION."""
    ctx.obj["client"].delete_organization_team(organization, team_name)

    if not ctx.obj["format_json"]:
        log(f'Team "{team_name}" was deleted from organization "{organization}".')


@cli.command(
    name="team-members-list", short_help="List members of an organization team."
)
@click.argument("organization")
@click.argument("team_name")
@click.pass_context
def team_members_list(ctx: Context, organization: str, team_name: str) -> None:
    """List members of team TEAM_NAME in ORGANIZATION"""
    members = ctx.obj["client"].get_organization_team_members(organization, team_name)
    if ctx.obj["format_json"]:
        print_json(members)
    else:
        log(f'Members of team "{team_name}" in organization "{organization}":')

        for object_member in members:
            log(object_member["member"])


@cli.command(
    name="team-members-add", short_help="Add a member to an organization team."
)
@click.argument("organization")
@click.argument("team_name")
@click.argument("member_username")
@click.pass_context
def team_members_add(
    ctx: Context, organization: str, team_name: str, member_username: str
) -> None:
    """Add member MEMBER_USERNAME to team TEAM_NAME in ORGANIZATION."""
    object_member = ctx.obj["client"].add_organization_team_member(
        organization, team_name, member_username
    )

    if ctx.obj["format_json"]:
        print_json(object_member)
    else:
        log(
            f'Member "{object_member["member"]}" added to team "{team_name}" in organization "{organization}".'
        )


@cli.command(
    name="team-members-remove", short_help="Remove a member from an organization team."
)
@click.argument("organization")
@click.argument("team_name")
@click.argument("member_username")
@click.pass_context
def team_members_remove(
    ctx: Context, organization: str, team_name: str, member_username: str
) -> None:
    """Remove member MEMBER_USERNAME from team TEAM_NAME in ORGANIZATION."""
    ctx.obj["client"].remove_organization_team_member(
        organization, team_name, member_username
    )

    if not ctx.obj["format_json"]:
        log(
            f'Member "{member_username}" removed from team "{team_name}" in organization "{organization}".'
        )
