# The official QFieldCloud SDK and CLI

`qfieldcloud-sdk` is the official client to connect to QFieldCloud API either as a python module, or directly from the command line.

## Install

`pip install qfieldcloud-sdk`

## Module usage

```
import requests
from qfieldcloud_sdk import sdk

client = sdk.Client(
    url="https://app.qfield.cloud/api/v1/",
    username="user1",
    password="pass1",
)

try:
    projects = client.list_projects()
except requests.exceptions.RequestException:
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


More detailed documentation can be found [here](https://docs.qfield.org/reference/qfieldcloud/sdk/)


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
