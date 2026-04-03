# The official QFieldCloud SDK and CLI

`qfieldcloud-sdk` is the official client to connect to QFieldCloud API either as a Python module, or directly from the command line interface (CLI).

## Contents

- [Documentation](#documentation)
- [Installation](#install)
- [CLI usage](#cli-usage)
- [Module usage](#module-usage)

## Documentation

[QFieldCloud SDK Documentation](https://opengisch.github.io/qfieldcloud-sdk-python/)

## Installation

### Linux/macOS

    pip3 install qfieldcloud-sdk

### Windows

Install Python with your favorite package manager. Then:

    python -m pip install qfieldcloud-sdk

## CLI usage

The package provides the official QFieldCloud CLI tool.

### Usage

```
qfieldcloud-cli [OPTIONS] COMMAND [ARGS]...
```

### Examples

```shell
# logs in user "user" with password "pass"
qfieldcloud-cli login user pass

# gets the projects of user "user" with password "pass" at "https://localhost/api/v1/"
qfieldcloud-cli -u user -p pass -U https://localhost/api/v1/ list-projects

# gets the projects of user authenticated with token `QFIELDCLOUD_TOKEN` at "https://localhost/api/v1/" as JSON
export QFIELDCLOUD_URL=https://localhost/api/v1/
export QFIELDCLOUD_TOKEN=017478ee2464440cb8d3e98080df5e5a
qfieldcloud-cli --json list-projects
```

Check [the examples page](https://opengisch.github.io/qfieldcloud-sdk-python/examples/) in the documentation for more examples.

## Module usage

```python
from qfieldcloud_sdk import sdk

client = sdk.Client(url="https://app.qfield.cloud/api/v1/")
client.login(
    username="user1",
    password="pass1",
)

projects = client.list_projects()
> projects
Projects:
0       myusername/myproject1
1       myusername/myproject2
...
```

## Development

Contributions are more than welcome!

### Code style

Code style done with [precommit](https://pre-commit.com/).

```
uv sync --group dev
# if you want to have git commits trigger pre-commit, install pre-commit hook:
uv run pre-commit install
# else run manually before (re)staging your files:
uv run pre-commit run --all-files
```

### Cloning the project

One time action to clone and setup:

```shell
git clone https://github.com/opengisch/qfieldcloud-sdk-python
cd qfieldcloud-sdk-python
# install dev dependencies (+ standard dependencies)
uv sync --group dev
uv run pre-commit install
```

To run CLI interface for development purposes execute:

```shell
uv run python -m qfieldcloud_sdk
```

To ease development, you can set a `.env` file. Therefore you can use directly the `qfieldcloud-cli` executable:
```
cp .env.example .env
uv run qfieldcloud-cli
```

### Building the package

```shell
# make sure your shell is sourced to no virtual environment
deactivate
# build
uv run python -m build
# and install with
uv run python -m pip install . --force-reinstall
```
Voilà!

### Running the tests

```shell
uv sync --group dev
ENVIRONMENT=test uv run python -m unittest discover -s tests
```
