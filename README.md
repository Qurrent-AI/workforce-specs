# Qurrent Workflow Template

View docs here: https://docs.qurrent.ai

## Development

These workflows are built using Python. Python can be installed and configured in too many ways, so we've created a Makefile to help you get started.

The Makefile will check that you have the correct Python version and that you have a virtual environment activated.

The first thing you should do is run the following command to check that your Python setup is correct:

```bash
make check-python VERBOSE=1
```

If you get an error, you need to fix it before you can continue.

### Python setup

1. To create a virtual environment:

```bash
make venv
```

2. To activate the virtual environment:

```bash
source .venv/bin/activate
```

To deactivate the virtual environment:

```bash
deactivate
```

3. To install the Qurrent OS package:

```bash
make install-qurrent VERSION=<version>
```

> Update `<version>` with the version of the Qurrent OS you want to install.

4. To install the workflow package and its dependencies:

```bash
pip install -e .[dev]
```

> NOTE: Do NOT include the Qurrent OS package in the workflow package. You install it using the `make install-qurrent` command above. If you try to install it in the workflow package, you will get an authentication error.

### Linting

To automatically run the linters before committing, install pre-commit:

```bash
pip install pre-commit
```

Install pre-commit hooks:

```bash
pre-commit install
```

### Build and run

Login to Google Cloud:

```bash
gcloud auth login
```

Then login to application-default:

```bash
gcloud auth application-default login
```

To build your workflow image:

```bash
docker compose build
```

To run your workflow image:

```bash
docker compose up
```

To build and run your workflow image:

```bash
docker compose up --build
```
