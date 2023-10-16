# The official QFieldCloud SDK and CLI

`qfieldcloud-sdk` is the official client to connect to QFieldCloud API either as a python module, or directly from the command line.

## Contents

- [Installation](#install)
- [CLI usage](#cli-usage)
- [Module usage](#module-usage)

## Install

### Linux/macOS

    pip3 install qfieldcloud-sdk

### Windows

Install Python with your favorite package manager. Then:

    python -m pip install qfieldcloud-sdk

## CLI usage

The package also ships with the official QFieldCloud CLI tool.

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

More detailed documentation can be found [here](https://docs.qfield.org/reference/qfieldcloud/sdk/)

## Module usage

```python
from  import sdk

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
pip install pre-commit
# if you want to have git commits trigger pre-commit, install pre-commit hook:
pre-commit install
# else run manually before (re)staging your files:
pre-commit run --all-files
```

### Cloning the project

One time action to clone and setup:

```shell
git clone https://github.com/opengisch/qfieldcloud-sdk-python
cd qfieldcloud-sdk-python
# install dev dependencies
python3 -m pip install pipenv
pre-commit install
# install package in a virtual environment
pipenv install -r requirements.txt
```
To run CLI interface for development purposes execute:

```shell
pipenv shell # if your pipenv virtual environment is not active yet
python -m qfieldcloud_sdk
```
To ease development, you can set a `.env` file. Therefore you can use directly the `qfieldcloud-cli` executable:
```
cp .env.example .env
pipenv run qfieldcloud-cli
```

### Building the package

```shell
# make sure your shell is sourced to no virtual environment
deactivate
# build
python3 -m build
# now either activate your shell with
pipenv shell
# and install with
python -m pip install . --force-reinstall
# or manually ensure it's pipenv and not your global pip doing the installation
pipenv run pip install . --force-reinstall
```
Voilà!
