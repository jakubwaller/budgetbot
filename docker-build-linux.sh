#!/usr/bin/env bash

git pull
docker build -t budgetbot/budgetbot -f Dockerfile-linux .
