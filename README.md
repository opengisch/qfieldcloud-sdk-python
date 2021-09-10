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
- `QFIELDCLOUD_USERNAME` - QFieldCloud username or email. Need `QFIELDCLOUD_PASSWORD` to be set.
- `QFIELDCLOUD_PASSWORD` - Password. Needs `QFIELDCLOUD_USERNAME` to be set.
- `QFIELDCLOUD_TOKEN` - Token that can be used instead of passing username and password. It can be obtained by running `qfieldcloud-cli login`.

### Commands overview

```
  download-files  Download QFieldCloud project files
  list-files      List QFieldCloud project files
  list-projects   List QFieldCloud projects
  login           Login into QFieldCloud
```

#### login

Login to QFieldCloud.

```
qfieldcloud-cli login [OPTIONS] USERNAME PASSWORD
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

#### download-files

Download QFieldCloud project files.

```
qfieldcloud-cli download-files [OPTIONS] PROJECT_ID LOCAL_DIR

Options:
  --subdir TEXT                   Do not download the whole project, but only
                                  the subdirectory passed.

  --exit-on-error / --no-exit-on-error
                                  If any project file download fails stop
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
python3 -m pip install --upgrade build pre-commit
pre-commit install
```

To run CLI interface for development purposes execute:

```
python src/bin/qfieldcloud-cli
```

### Building the package

Run:

```
python3 -m build
```

Then install on your system:

```
pip install dist/qfieldcloud_sdk-dev-py3-none-any.whl --force-reinstall
```

Voila!
