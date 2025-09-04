#!/bin/bash

set -euo pipefail

# Move to project root (directory of this script)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Config
PORT="${PORT:-8000}"
CONDA_ENV_NAME="${CONDA_ENV_NAME:-cam_server}"

# --- UFW Firewall Status Check ---

# 1. Check if ufw command exists
if ! command -v ufw &> /dev/null
then
    echo "UFW is not installed. Starting the server."
else
    # 2. Check if ufw is active
    if ! ufw status | grep -q "Status: active"
    then
        echo "UFW is installed but not active. Starting the server."
    else
        echo "UFW is active."
        # 3. Check if target port is open
        if ufw status | grep -q "${PORT}"
        then
            echo "Confirmed that port ${PORT} is open."
        else
            echo "Warning: UFW is active, but port ${PORT} is not open."
            echo "To allow external connections, please run 'sudo ufw allow ${PORT}'."
            exit 1
        fi
    fi
fi

echo "" # Newline for readability
echo "--- Starting Server Program on port ${PORT} ---"

CONDA_ACTIVATED=0
if command -v conda &> /dev/null
then
    # Initialize conda in this shell
    eval "$(conda shell.bash hook)"
    if conda env list | awk '{print $1}' | grep -qx "${CONDA_ENV_NAME}"
    then
        echo "Activating conda environment: ${CONDA_ENV_NAME}"
        conda activate "${CONDA_ENV_NAME}"
        CONDA_ACTIVATED=1
    else
        echo "Conda env '${CONDA_ENV_NAME}' not found. Falling back to system python."
    fi
else
    echo "Conda not found. Falling back to system python."
fi

# Ensure python is available
if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null
then
    echo "Error: Python is not installed or not in PATH."
    exit 1
fi

PYTHON_BIN="python"
if ! command -v python &> /dev/null && command -v python3 &> /dev/null
then
    PYTHON_BIN="python3"
fi

# Run server
${PYTHON_BIN} -m server.main

# Cleanup
if [ "$CONDA_ACTIVATED" -eq 1 ]
then
    conda deactivate
fi

echo "--- Server Program Terminated ---"