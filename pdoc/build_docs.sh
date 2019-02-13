#!/bin/bash
set -Eeuxo pipefail

# PYTHONWARNINGS='error::UserWarning' \
pdoc --html --overwrite --html-dir build cfgs --template-dir pdoc/
