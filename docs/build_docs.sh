#!/bin/bash
set -Eeuxo pipefail

pdoc --html --overwrite --html-dir build cfgs
mv build/cfgs.html docs/
rm -Rf build
docs/make_index_file.py README.rst docs/index.html
