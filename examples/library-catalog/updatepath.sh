#!/usr/bin/env bash

# To update the PYTHONPATH in your shell environment to make custom modules 
# in this directory visible to the Python interpreter, run:
#
# $ source updatepath.sh

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"
