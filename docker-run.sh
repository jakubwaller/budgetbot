#!/usr/bin/env bash

docker stop budgetbot
docker rm budgetbot
docker run --restart always --name budgetbot -d -v /home/ubuntu/budgetbot/budget_csvs/:/budgetbot/budgetbot/budget_csvs budgetbot/budgetbot bash -c "cd /budgetbot/budgetbot && python3 -m budgetbot"
docker logs -f budgetbot