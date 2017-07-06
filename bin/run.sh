#!/usr/bin/env bash

# Get full path to the directory of this file
pushd `dirname $0` > /dev/null
SCRIPTPATH=`pwd -P`
popd > /dev/null

VENV_NAME="venv"

LOGO="
====================================
=======   HackPad Migrator   =======
====================================
"

# Print some intro
echo "$LOGO"

echo "Bootstraping HACKPAD MIGRATOR Environment..."

# Go into the app root directory
cd "$SCRIPTPATH/../"

# Activate Virtual Env
source "$VENV_NAME/bin/activate"

# Run script
python3 migrator/__init__.py
deactivate