#!/bin/bash
set -e

echo "Applying correct permissions..."
sudo chown -R ec2-user:ec2-user /home/ec2-user/notecasts-extractor-service
cd /home/ec2-user/notecasts-extractor-service

echo "Setting up virtual environment..."
pip3 install --upgrade pip
pip3 install -r requirements.txt
