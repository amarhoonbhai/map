#!/bin/bash

# Start runner.py in background with nohup
echo "Starting runner.py in background..."
nohup python3 runner.py > runner.log 2>&1 &
echo "Runner started. Logs are being written to runner.log"
