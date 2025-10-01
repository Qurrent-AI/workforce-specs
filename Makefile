.PHONY: install-qurrent venv check-python

APPROVED_PYTHON_VERSIONS = 3.10 3.11 3.12
DEFAULT_PYTHON_VERSION = 3.12
DEFAULT_QURENT_VERSION = 0.9.36

PYTHON := $(shell which python3 2>/dev/null || which python)
PIP := $(shell which pip3 2>/dev/null || which pip)

check-python:
	@if [ "$$VERBOSE" = "1" ]; then \
		echo "Checking Python location..."; \
		echo "Using Python: $(PYTHON)"; \
	fi
	@if [ "$$VERBOSE" = "1" ]; then \
		echo "Checking Python version..."; \
	fi
	@PY_VER=$$($(PYTHON) -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'); \
	APPROVED="$(APPROVED_PYTHON_VERSIONS)"; \
	if [ "$$VERBOSE" = "1" ]; then \
		echo "Detected Python version: $$PY_VER"; \
		echo "Approved versions: $$APPROVED"; \
	fi; \
	echo "$$APPROVED" | grep -w "$$PY_VER" > /dev/null; \
	if [ $$? -ne 0 ]; then \
		echo "Error: Python version $$PY_VER is not in the approved list: $$APPROVED"; \
		exit 1; \
	else \
		if [ "$$VERBOSE" = "1" ]; then \
			echo "Python version $$PY_VER is approved."; \
		fi; \
	fi
	@if [ "$$VERBOSE" = "1" ]; then \
		echo "Checking for active virtual environment..."; \
	fi
	@VENV_ACTIVE=$$($(PYTHON) -c 'import sys; print("1" if hasattr(sys, "real_prefix") or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix) else "0")'); \
	if [ "$$VENV_ACTIVE" = "1" ]; then \
		if [ "$$VERBOSE" = "1" ]; then \
			echo "Virtual environment is active."; \
		fi; \
	else \
		echo "Warning: No Python virtual environment detected. It is recommended to use a virtual environment."; \
	fi; \
	echo "✔ Python setup is approved."

venv: check-python
	$(PYTHON) -m venv .venv
	.venv/bin/python -m pip install --upgrade pip
	@echo "✔ Virtual environment created."
	@echo "To activate the virtual environment, run:"
	@echo "  source .venv/bin/activate"

install-qurrent: check-python
	@echo "Fetching Google Cloud access token..."
	@ACCESS_TOKEN=$$(gcloud auth print-access-token) && \
	VERSION=$${VERSION:-$(DEFAULT_QURENT_VERSION)} && \
	$(PIP) install --extra-index-url https://oauth2accesstoken:$${ACCESS_TOKEN}@us-central1-python.pkg.dev/qurrent-prod-02192025/qurrent-prod-02192025-pypi/simple/ qurrent==$$VERSION
