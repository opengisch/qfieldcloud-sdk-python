# The official QFieldCloud SDK and CLI

`qfieldcloud-sdk` is the official client to connect to QFieldCloud API either as a python module, or directly from the command line.

## Install

`pip install qfieldcloud-sdk`

## Module usage

```
import qfieldcloud_sdk
import requests

client = qfieldcloud_sdk.Client(
    url="https://app.qfield.cloud/api/v1/",
    username="user1",
    password="pass1",
)

try:
    projects = client.projects()
except requests.HttpRequest:
    print("Oops!")
```

## CLI usage

The official QFieldCloud CLI tool.

### Usage

```
qfieldcloud-cli [OPTIONS] COMMAND [ARGS]...
```

### Examples

```
# logs in user "user" with password "pass"
qfieldcloud-cli login user pass

# gets the projects of user "user" with password "pass" at "https://localhost/api/v1/"
qfieldcloud-cli -u user -p pass -U https://localhost/api/v1/ list-projects

# gets the projects of user authenticated with token `QFIELDCLOUD_TOKEN` at "https://localhost/api/v1/" as JSON
export QFIELDCLOUD_URL=https://localhost/api/v1/
export QFIELDCLOUD_TOKEN=017478ee2464440cb8d3e98080df5e5a
qfieldcloud-cli --json list-projects
```

### Global options overview

```
-U, --url TEXT                  URL to the QFieldCloud API endpoint. If not
                                passed, gets the value from QFIELDCLOUD_URL
                                environment variable. Default:
                                https://app.qfield.cloud/api/v1/
-u, --username TEXT             Username or email.
-p, --password TEXT
-t, --token TEXT                Session token.
--json / --human                Output the result as newline formatted json. Default: False
--verify-ssl / --no-verify-ssl  Verify SSL. Default: True
--help                          Show this message and exit.
```

Environment variables can be used instead of passing some common global options.

- `QFIELDCLOUD_API` - QFieldCloud API endpoint URL
- `QFIELDCLOUD_USERNAME` - QFieldCloud username or email. Requires `QFIELDCLOUD_PASSWORD` to be set.
- `QFIELDCLOUD_PASSWORD` - Password. Requires `QFIELDCLOUD_USERNAME` to be set.
- `QFIELDCLOUD_TOKEN` - Token that can be used instead of passing username and password. It can be obtained by running `qfieldcloud-cli login`.
- `QFIELDCLOUD_VERIFY_SSL` - When set to `0` has the same effect as passing `--no-verify-ssl`.

### Commands overview

```
  login             Login to QFieldCloud.
  logout            Logout and expire the token.
  list-projects     List QFieldCloud projects.
  list-files        List QFieldCloud project files.
  create-project    Creates a new empty QFieldCloud project.
  delete-project    Deletes a QFieldCloud project.
  upload-files      Upload files to a QFieldCloud project.
  download-files    Download QFieldCloud project files.
  delete-files      Delete QFieldCloud project files.
  list-jobs         List project jobs.
  job-trigger       Triggers a new job.
  job-status        Get job status.
  package-latest    Check project packaging status.
  package-download  Download packaged QFieldCloud project files.
```

#### login

Login to QFieldCloud.

```
qfieldcloud-cli login [OPTIONS] USERNAME PASSWORD
```

#### logout

Logout from QFieldCloud.

```
qfieldcloud-cli logout
```

#### list-projects

List QFieldCloud projects.

```
qfieldcloud-cli list-projects [OPTIONS]

Options:
  --include-public / --no-public  Includes the public project in the list. Default: False
```

#### list-files

List QFieldCloud project files.

```
qfieldcloud-cli list-files [OPTIONS] PROJECT_ID
```

#### create-project

Creates a new empty QFieldCloud project.

```
qfieldcloud-cli create-project [OPTIONS] NAME

Options:
  --owner TEXT                Owner of the project. If omitted, the current
                              user is the owner.
  --description TEXT          Description of the project.
  --is-public / --is-private  Mark the project as public.
```

#### delete-project

Deletes a QFieldCloud project.

```
qfieldcloud-cli delete-project [OPTIONS] PROJECT_ID
```

#### upload-files

Upload files to a QFieldCloud project.

```
qfieldcloud-cli upload-files [OPTIONS] PROJECT_ID PROJECT_PATH

Options:
  --filter TEXT                   Do not upload the whole project, but only
                                  the files which match the glob.
  --throw-on-error / --no-throw-on-error
                                  If any project file upload fails stop
                                  uploading the rest. Default: False
```

#### download-files

Download QFieldCloud project files.

```
qfieldcloud-cli download-files [OPTIONS] PROJECT_ID LOCAL_DIR

Options:
  --filter TEXT                   Do not download the whole project, but only
                                  the files which match the glob.
  --throw-on-error / --no-throw-on-error
                                  If any project file downloads fails stop
                                  downloading the rest. Default: False
```

#### delete-files

Delete QFieldCloud project files.

```
qfieldcloud-cli delete-files [OPTIONS] PROJECT_ID PATHS...

Options:
  --throw-on-error / --no-throw-on-error
                                  If any project file delete operations fails
                                  stop, stop deleting the rest. Default: False
```

#### job-list

List project jobs.

```
qfieldcloud-cli list-jobs [OPTIONS] PROJECT_ID

Options:
  --type JOBTYPES  Job type. One of package, delta_apply or
                   process_projectfile.
```

#### job-trigger

Triggers a new job.

```
qfieldcloud-cli job-trigger [OPTIONS] PROJECT_ID JOB_TYPE

Options:
  --force / --no-force  Should force creating a new job. Default: False
```

#### job-status

Get job status.

```
qfieldcloud-cli job-status [OPTIONS] JOB_ID
```

#### package-latest

Check project packaging status.

```
qfieldcloud-cli package-latest [OPTIONS] PROJECT_ID
```

#### package-download

Download packaged QFieldCloud project files.

```
qfieldcloud-cli package-download [OPTIONS] PROJECT_ID LOCAL_DIR

Options:
  --filter TEXT                   Do not download the whole packaged project,
                                  but only the files which match the glob.
  --throw-on-error / --no-throw-on-error
                                  If any packaged file downloads fails stop
                                  downloading the rest. Default: False
```

## Development

Contributions are more than welcome!

### Code style
Code style done with [precommit](https://pre-commit.com/).

```
pip install pre-commit
# install pre-commit hook
pre-commit install
```

### Cloning the project

One time action to clone and setup:

```
git clone https://github.com/opengisch/qfieldcloud-sdk-python
cd qfieldcloud-sdk-python
# install dev dependencies
python3 -m pip install pipenv
pipenv install --dev
pre-commit install
```

To run CLI interface for development purposes execute:

```
pipenv run python src/bin/qfieldcloud-cli
```

To ease the development, you can set a `.env` file. Therefore you can use directly the `qfieldcloud-cli` executable:
```
cp .env.example .env
pipenv run qfieldcloud-cli
```

### Building the package

Run:

```
python3 -m build
```

Then install on your system:

```
python3 -m pip install dist/qfieldcloud_sdk-dev-py3-none-any.whl --force-reinstall
```

Voila!
