#!/bin/bash

set -e

python load_secrets.py

chmod +x run_evals.py

ls -la

python hello_world/hello_world_basic.py
