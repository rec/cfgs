#!/bin/bash
set -Eeuxo pipefail

pdoc --html --overwrite --html-dir build cfgs
