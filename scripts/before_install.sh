#!/bin/bash
set -e

echo "Stopping existing application if running..."
sudo systemctl stop notecasts || true

echo "Removing old application files..."
sudo rm -rf /home/ec2-user/notecasts-extractor-service

echo "Retrieving GitHub credentials from AWS Systems Manager..."
GITHUB_TOKEN=$(aws ssm get-parameter --name "/notecasts/github_pat" --with-decryption --query "Parameter.Value" --output text | tr -d '"')

echo "Cloning the private repository..."
git clone https://${GITHUB_TOKEN}@github.com/jaimemendozadev/notecasts-extractor-service.git /home/ec2-user/notecasts-extractor-service
