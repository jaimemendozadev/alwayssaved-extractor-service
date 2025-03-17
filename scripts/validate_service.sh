#!/bin/bash
set -e

echo "Checking if Notecasts Extractor Service is running..."
if systemctl is-active --quiet notecasts; then
  echo "Service is running successfully."
  exit 0
else
  echo "Service failed to start."
  exit 1
fi
