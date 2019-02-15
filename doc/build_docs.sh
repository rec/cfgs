#!/bin/bash
set -Eeuxo pipefail

pdoc --html --overwrite --html-dir build cfgs
mv build/cfgs.html doc/
rm -Rf build
