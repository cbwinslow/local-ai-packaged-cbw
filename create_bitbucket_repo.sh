#!/bin/bash

# Bitbucket Repository Creation Script
# Requires BITBUCKET_USERNAME and BITBUCKET_APP_PASSWORD environment variables

REPO_NAME="local-ai-packaged-cbw"
BITBUCKET_API="https://api.bitbucket.org/2.0/repositories"

# Check if required environment variables are set
if [[ -z "$BITBUCKET_USERNAME" || -z "$BITBUCKET_APP_PASSWORD" ]]; then
  echo "Error: Please set BITBUCKET_USERNAME and BITBUCKET_APP_PASSWORD environment variables"
  exit 1
fi

# Create repository using Bitbucket API
response=$(curl -s -X POST -u "$BITBUCKET_USERNAME:$BITBUCKET_APP_PASSWORD" \
  -H "Content-Type: application/json" \
  -d '{
    "scm": "git",
    "is_private": true,
    "fork_policy": "allow_forks"
  }' \
  "$BITBUCKET_API/$BITBUCKET_USERNAME/$REPO_NAME")

if [[ $response == *"\"type\": \"error\""* ]]; then
  echo "Error creating repository: $response"
  exit 1
else
  echo "Repository created successfully: https://bitbucket.org/$BITBUCKET_USERNAME/$REPO_NAME"
fi
