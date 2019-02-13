#!/bin/bash
set -Eeuxo pipefail

pdoc --html --overwrite --html-dir build cfgs --template-dir pdoc/
mv build/cfgs.html .
rm -Rf build
