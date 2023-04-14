import datetime
import html
import logging
import os
import traceback

import pandas as pd
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ParseMode
from telegram.ext import CallbackQueryHandler
from telegram.ext import Updater, CallbackContext, CommandHandler, ConversationHandler, MessageHandler, Filters

from tools import read_config, read_csv, write_csv, read_currencies, run_request, save_currencies

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

outdir = "budget_csvs"
df_columns = ["date", "amount", "category", "description"]

config = read_config(outdir)
currencies = read_currencies(outdir)
developer_chat_id = config["developer_chat_id"]
bot_token = config["bot_token"]
currency_exchange_api = config["currency_exchange_api"]

expense_dates = dict()
expense_amounts = dict()
expense_currencies = dict()
expense_categories = dict()
expense_descriptions = dict()

(
    EXPENSE_DATE,
    EXPENSE_DATE_ANSWER,
    EXPENSE_CURRENCY,
    EXPENSE_AMOUNT,
    EXPENSE_CATEGORY,
    EXPENSE_DESCRIPTION,
    ADD_CURRENCY,
) = range(7)
NUMBER_OF_DAYS_TO_SEND = 9


def start(update: Update, context: CallbackContext) -> int:
    context.bot.send_message(
        update.message.chat.id,
        "Hi there! I’m Budget Bot.\n"
        "Send me your expenses and I'll keep track of them for you.\n"
        "If you find issues or have any questions, please contact budgetbot@jakubwaller.eu\n"
        "If you want to support the bot, you can buy him a coffee here https://ko-fi.com/jakubwaller\n"
        "Feel free to also check out the code at: https://github.com/jakubwaller/budgetbot",
    )

    return EXPENSE_DATE


def add_currency(update: Update, context: CallbackContext) -> int:
    context.bot.send_message(update.message.chat.id, "Send me the currency three-letter name.")

    return ADD_CURRENCY


def add_currency_answer(update: Update, context: CallbackContext) -> int:
    currency_name = update.message.text.strip()
    url = f"https://api.apilayer.com/exchangerates_data/convert?to={currency_name}&from=EUR&amount=1"

    headers = {"apikey": currency_exchange_api}

    currency_exchange_rate = run_request("GET", url, request_headers=headers)["result"]

    currencies[currency_name] = currency_exchange_rate
    save_currencies(currencies, outdir)

    context.bot.send_message(
        update.message.chat.id,
        f"Currency {currency_name} added with " f"exchange rate EUR/{currency_name}: {currency_exchange_rate}",
    )

    return EXPENSE_DATE


def expense_date(update: Update, context: CallbackContext) -> int:
    """Asks for a date."""
    dates = [
        (datetime.date.today() - datetime.timedelta(days=x)).strftime("%d.%m.%Y")
        for x in range(0, NUMBER_OF_DAYS_TO_SEND)
    ]

    keyboard = [InlineKeyboardButton(d, callback_data=d) for d in dates]

    chunk_size = 3
    chunks = [keyboard[x : x + chunk_size] for x in range(0, len(keyboard), chunk_size)]

    reply_markup = InlineKeyboardMarkup(chunks)
    update.message.reply_text("Select date:", reply_markup=reply_markup)

    return EXPENSE_DATE_ANSWER


def expense_date_answer(update: Update, context: CallbackContext) -> int:
    global expense_dates
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    query.answer()

    received_expense_date = query.data
    query.edit_message_text(text=f"Selected date: {received_expense_date}")
    expense_dates[query.message.chat.id] = received_expense_date

    keyboard = [InlineKeyboardButton(d, callback_data=d) for d in sorted(list(currencies.keys()))]

    chunk_size = 3
    chunks = [keyboard[x : x + chunk_size] for x in range(0, len(keyboard), chunk_size)]

    reply_markup = InlineKeyboardMarkup(chunks)

    context.bot.send_message(query.message.chat.id, "What currency?", reply_markup=reply_markup)

    return EXPENSE_CURRENCY


def expense_currency(update: Update, context: CallbackContext) -> int:
    global expense_currencies
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    query.answer()

    received_expense_currency = query.data
    query.edit_message_text(text=f"Selected currency: {received_expense_currency}")
    expense_currencies[query.message.chat.id] = received_expense_currency

    context.bot.send_message(query.message.chat.id, "How much?")

    return EXPENSE_AMOUNT


def expense_amount(update: Update, context: CallbackContext) -> int:
    global expense_amounts
    amount = float(update.message.text.strip())
    expense_amounts[update.message.chat.id] = amount

    keyboard = [
        InlineKeyboardButton(d, callback_data=d)
        for d in [
            "Supermarket",
            "Eating Out",
            "Drinking",
            "Busses etc",
            "Car Rental",
            "LocalTransport",
            "Flights",
            "Hotels",
            "Trips",
            "Various",
        ]
    ]

    chunk_size = 3
    chunks = [keyboard[x : x + chunk_size] for x in range(0, len(keyboard), chunk_size)]

    reply_markup = InlineKeyboardMarkup(chunks)

    context.bot.send_message(update.message.chat.id, "What category?", reply_markup=reply_markup)

    return EXPENSE_CATEGORY


def expense_category(update: Update, context: CallbackContext) -> int:
    global expense_categories
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    query.answer()

    received_expense_category = query.data
    query.edit_message_text(text=f"Selected category: {received_expense_category}")
    expense_categories[query.message.chat.id] = received_expense_category

    context.bot.send_message(query.message.chat.id, "Send a short description:")

    return EXPENSE_DESCRIPTION


def expense_description(update: Update, context: CallbackContext) -> int:
    global expense_descriptions
    description = update.message.text.strip()
    expense_descriptions[update.message.chat.id] = description

    send_info(update.message.chat.id, context)

    return EXPENSE_DATE


def send_info(chat_id, context: CallbackContext):
    global expense_amounts
    global expense_dates
    global expense_currencies
    global expense_categories
    global expense_descriptions

    converted_amount = 0
    for currency, exchange_rate in currencies.items():
        if expense_currencies[chat_id] == currency:
            converted_amount = round(expense_amounts[chat_id] / exchange_rate, 2)

    context.bot.send_message(
        chat_id,
        f"{expense_dates[chat_id]}: {expense_amounts[chat_id]} {expense_currencies[chat_id]} "
        f"({converted_amount} EUR), "
        f"{expense_categories[chat_id]}, "
        f"{expense_descriptions[chat_id]}.",
    )

    df = read_csv(outdir, chat_id, df_columns)
    df = pd.concat(
        [
            df,
            pd.DataFrame(
                [
                    [
                        expense_dates[chat_id],
                        converted_amount,
                        expense_categories[chat_id],
                        expense_descriptions[chat_id],
                    ]
                ],
                columns=df_columns,
            ),
        ]
    )
    write_csv(df, outdir, chat_id)


def send_all_expenses(update: Update, context: CallbackContext) -> int:
    df = read_csv(outdir, update.message.chat.id, df_columns)
    df["sorting_date"] = pd.to_datetime(df["date"], format="%d.%m.%Y")
    df.sort_values(by=["sorting_date"], inplace=True)

    message = ""
    for c in df.itertuples():
        if len(message) > 0:
            message = message + "\n"
        message = message + f"{c.date},{c.amount},{c.category},{c.description}"

    if len(message) == 0:
        context.bot.send_message(update.message.chat.id, "No expenses yet!")
    else:
        context.bot.send_message(update.message.chat.id, message)
        context.bot.send_message(update.message.chat.id, f"Sum: {round(df['amount'].sum(), 2)}")
        context.bot.send_message(
            update.message.chat.id,
            f"Spent today: {round(df[df.date == datetime.date.today().strftime('%d.%m.%Y')]['amount'].sum(), 2)}",
        )

    return EXPENSE_DATE


def delete_last_entry(update: Update, context: CallbackContext) -> int:
    chat_id = update.message.chat.id
    df = read_csv(outdir, chat_id, df_columns)

    df = df.drop([df.iloc[-1].name])
    write_csv(df, outdir, chat_id)

    context.bot.send_message(update.message.chat.id, "Last entry deleted.")

    return EXPENSE_DATE


def clear_all(update: Update, context: CallbackContext) -> int:
    chat_id = update.message.chat.id
    os.remove(os.path.join(outdir, f"{chat_id}.csv"))

    context.bot.send_message(update.message.chat.id, "Removed all entries.")

    return EXPENSE_DATE


def error_handler(update: object, context: CallbackContext) -> int:
    """Log the error and send a telegram message to notify the developer."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    message = f"An exception was raised while handling an update\n" f"<pre>{html.escape(tb_string)}"

    message = message[:500] + "</pre>"

    context.bot.send_message(chat_id=developer_chat_id, text=message, parse_mode=ParseMode.HTML)

    return EXPENSE_DATE


def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation."""

    context.bot.send_message(update.message.chat.id, "Current operation cancelled.")

    return EXPENSE_DATE


def main() -> None:
    """Setup and run the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater(bot_token)

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("spend", expense_date),
            CommandHandler("start", start),
            CommandHandler("send_all_expenses", send_all_expenses),
            CommandHandler("delete_last_entry", delete_last_entry),
            CommandHandler("clear_all", clear_all),
            CommandHandler("add_currency", add_currency),
        ],
        states={
            EXPENSE_DATE: [
                CommandHandler("spend", expense_date),
                CommandHandler("send_all_expenses", send_all_expenses),
                CommandHandler("delete_last_entry", delete_last_entry),
                CommandHandler("clear_all", clear_all),
                CommandHandler("add_currency", add_currency),
            ],
            EXPENSE_DATE_ANSWER: [CallbackQueryHandler(expense_date_answer)],
            EXPENSE_CURRENCY: [CallbackQueryHandler(expense_currency)],
            EXPENSE_AMOUNT: [MessageHandler(Filters.text & ~Filters.command, expense_amount)],
            EXPENSE_CATEGORY: [CallbackQueryHandler(expense_category)],
            EXPENSE_DESCRIPTION: [MessageHandler(Filters.text & ~Filters.command, expense_description)],
            ADD_CURRENCY: [MessageHandler(Filters.text & ~Filters.command, add_currency_answer)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    updater.dispatcher.add_handler(conv_handler)

    updater.dispatcher.add_error_handler(error_handler)

    # Start the Bot
    updater.start_polling()

    # Run the bot until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT
    updater.idle()


if __name__ == "__main__":
    main()
