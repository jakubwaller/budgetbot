# Budget Bot

![budgetbot](budgetbot.gif)

This Telegram Bot keeps track of your budget.

Features:

- date selection (currently set to today minus 8 days - adjustable)
- currency selection
- add a new currency -> values obtained automatically from https://exchangeratesapi.io/
- category selection (again easy to adjust)
- send all expanses - in a nice csv format -> easy to import elsewhere
- delete last entry
- clear all entries

The bot is running on my Raspberry Pi and can be found here [![@budget_42_bot](https://img.shields.io/badge/Telegram%20Bot-@budget_42_bot-blue?logo=telegram&style=plastic)](https://telegram.me/budget_42_bot)

But it is also easy to build and deploy on your own server. See below.

## Development

### Setup

```shell
source setup-local-venv.sh
```

## Deployment

### Setup Environment

- Create a Telegram Bot using the BotFather
- Create a chat where the bot will send logs and errors
- Create an Exchange Rate Api key [here](https://exchangeratesapi.io/)
- Create a file `env.json` in the `budget_csvs` subdirectory with the developer_chat_id, the bot_token, and the currency_exchange_api
```json
{
  "developer_chat_id": "<REPLACE WITH DEVELOPER CHAT ID>",
  "bot_token": "<REPLACE WITH BOT TOKEN>",
  "currency_exchange_api": "<REPLACE WITH EXCHANGE RATE API KEY>"
}
```

### Build docker

#### Raspberry Pi

```shell
./docker-build-raspberry-pi.sh
```

#### Linux/Mac

```shell
./docker-build-linux.sh
```

### Run docker

```shell
./docker-run.sh
```

## Sources

- Using [Exchange Rate Api key](https://exchangeratesapi.io/)
- Inspired by https://github.com/python-telegram-bot/python-telegram-bot/wiki/InlineKeyboard-Example