#!/bin/sh
# Run the checker on the bundled examples.
# Run from the repo root: sh examples/run-example.sh
# The bad-files run exits 1 because every file in it breaks the
# naming rule on purpose — that is the expected result here.
set -e
cd "$(dirname "$0")/.."
echo "--- check the clean files ---"
python3 src/filename_checker.py examples/clean-files/
echo "--- check the files with bad names ---"
python3 src/filename_checker.py examples/bad-files/ || true
