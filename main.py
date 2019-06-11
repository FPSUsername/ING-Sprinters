from telegram import ChatAction, InlineQueryResultArticle, InlineQueryResultDocument, ParseMode, InputTextMessageContent
from telegram.ext import Updater, CommandHandler, InlineQueryHandler, MessageHandler
from telegram.utils.helpers import escape_markdown
from six.moves import cPickle as pickle
from functools import wraps
from uuid import uuid4

import ing_sprinters
import logging
import time
import re
import os

flag = False  # Flag to skip inline 1
sprinter = ''  # Sprinter memory
sprinter_ls = ''  # Sprinter + Long/Short memory


# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def send_typing_action(func):
    """Sends typing action while processing func command."""
    @wraps(func)
    def command_func(update, context, *args, **kwargs):
        context.bot.send_chat_action(
            chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)
        return func(update, context, *args, **kwargs)

    return command_func


@send_typing_action
def start(update, context):
    query = update.message.text
    query = query.replace("/market", "").strip()
    context.bot.send_message(chat_id=update.message.chat_id, text='I send the stock exchange rates for ING Sprinters!')


@send_typing_action
def market(update, context):
    query = update.message.text.replace("/market", "").strip()

    if not query:
        message = 'Type the market for information about the exchange rate:\n `/market AEX`'
        context.bot.send_message(chat_id=update.message.chat_id, text=message, parse_mode='Markdown')
        return None

    result = ing_sprinters.market_info(query)
    key = list(result.keys())
    value = list(result.values())

    message = '*' + query + '*'
    message += "\n*%s* _%s_" % (key[0], value[0])

    context.bot.send_message(chat_id=update.message.chat_id, text=message, parse_mode='Markdown')


@send_typing_action
def ing(update, context):
    query = update.message.text.replace("/ing", "").strip()

    if not query:
        message = 'Type the market and ISIN for information about the exchange rate of a sprinter:\n `/ing AEX NL0012065692`'
        context.bot.send_message(chat_id=update.message.chat_id, text=message, parse_mode='Markdown')
        return None

    query = query.split()
    sprinter_name = "".join(query[:-1])
    ISIN = query[-1]

    with open("markets.txt", "r") as file:
        if not (sprinter_name in file.read()):
            return None

    result = ing_sprinters.sprinter_info(sprinter_name, ISIN)
    keys = list(result.keys())
    values = list(result.values())

    message = '*' + sprinter_name + '*' + \
        "\n*%s*                           _%s_" % (keys[0], values[0]) +\
        "\n*%s*                           _%s_" % (keys[1], values[1])

    if "-" in values[2]:
        message += "\n*%s*                    ⬇️ _%s_" % (keys[2], values[2])
    elif float(values[2]) != 0.00:
        message += "\n*%s*                   ⬆️ _%s_" % (keys[2], values[2])
    else:
        message += "\n*%s*                    _%s_" % (keys[2], values[2])

    message += "\n*%s*                 _%s_" % (keys[3], values[3]) + \
        "\n*%s*  _%s_" % (keys[4], values[4])

    if "-" in values[5][1]:
        message += "\n*%s*   _%s_ ⬇️ _%s_" % (keys[5], values[5][0], values[5][1])
    elif "+" in values[5][1]:
        message += "\n*%s*   _%s_ ⬆️ _%s_" % (keys[5], values[5][0], values[5][1])
    else:
        message += "\n*%s*   _%s_ _%s_" % (keys[5], values[5][0], values[5][1])

    context.bot.send_message(chat_id=update.message.chat_id, text=message, parse_mode='Markdown')


def inline_query(update, context):
    """Handle the inline query."""
    query = update.inline_query.query
    global flag, sprinter, sprinter_ls

    logging.debug("Query: " + query)

    # Inline 1 Shows current markets
    if not flag:
        logging.debug("Inline 1")
        results = []

        with open("markets.txt", "r") as file:
            titles = eval(file.read())

        for item in titles:
            if item.lower().startswith(query.lower()):
                results.append(
                    InlineQueryResultArticle(
                        id=uuid4(),
                        title=item,
                        input_message_content=InputTextMessageContent('/market ' + item)))
            if item in query:
                flag = True
                sprinter = item

    # Inline 2 Shows sprinter types
    if (flag and sprinter):
        logging.debug("Inline 2")
        results = []

        for item in ['Long', 'Short']:
            output = sprinter + ' ' + item  # Sprinter + Long/Short
            results.append(
                InlineQueryResultArticle(
                    id=uuid4(),
                    title=item,
                    input_message_content=InputTextMessageContent('/market ' + sprinter)))
            if item.lower() in query.lower():
                sprinter_ls = output

    # Inline 3 Shows current sprinters
    if (flag and sprinter_ls):
        logging.debug("Inline 3")
        results = []

        query_short = query.lower().replace(sprinter_ls.lower() + ' ', '')  # Remove first two inlines from query
        query_nr = re.findall(r'\d*\,?\d+', query_short)  # Extract numbers from the shortened query
        sprinters = ing_sprinters.sprinter_list(sprinter_ls)  # Retreive list of sprinters

        for key, value in sprinters.items():
            key_nr = re.findall(r'\d*\,?\d+', key)

            # If sprinter (key), ISIN (value) or number (inside key) match
            if key.lower().startswith(query_short) \
                    or value.lower().startswith(query_short) \
                    or (key_nr[-1].startswith(query_nr[-1])):
                output = sprinter + ' ' + value  # Sprinter + Long/Short + ISIN
                results.append(
                    InlineQueryResultArticle(
                        id=uuid4(),
                        title=key,
                        input_message_content=InputTextMessageContent('/ing ' + output)))

    # Reset inlines
    if (sprinter not in query):
        logging.debug("Reset")
        results = []
        flag = False
        sprinter = ''
        sprinter_ls = ''

    if update.inline_query.offset == "":
        offset = 0
    else:
        offset = int(update.inline_query.offset)

    update.inline_query.answer(results=results[offset:offset + 50], next_offset=str(offset + 50))


def reply_keyboard(update, context):
    user_id = update.message.user_id  # placeholder
    # Something https://python-telegram-bot.readthedocs.io/en/stable/telegram.replykeyboardmarkup.html


# Add market/sprinter to favorites
@send_typing_action
def add(update, context):
    user_id = update.message.from_user['id']
    query = update.message.text.replace("/add", "").strip()

    message = ing_sprinters.add(user_id, query)

    context.bot.send_message(chat_id=update.message.chat_id, text=message, parse_mode='Markdown')


# remove market or sprinter
@send_typing_action
def remove(update, context):
    user_id = update.message.from_user['id']
    query = update.message.text.replace("/remove", "").strip()

    message = ing_sprinters.remove(user_id, query)

    context.bot.send_message(chat_id=update.message.chat_id, text=message, parse_mode='Markdown')


def callback_market(context):
    ing_sprinters.markets()
    logging.debug("Market list updated!")


def main():
    # Create the Updater and pass it your bot's token.
    try:
        with open("token.txt", "r") as file:
            token = file.read().strip()
            logging.debug("Token: " + token)

        if not token:
            logging.info("Token file is empty!")
            raise SystemExit

    except FileNotFoundError:
        logging.info("Token file not found!")
        raise SystemExit

    try:
        file = open('database.pkl', 'rb')
        file.close()
    except IOError:
        file = open('database.pkl', 'wb')
        file.close()

    updater = Updater(token, use_context=True)
    job = updater.job_queue

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("ing", ing))
    dp.add_handler(CommandHandler("market", market))
    dp.add_handler(CommandHandler("add", add))
    dp.add_handler(CommandHandler("remove", remove))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(InlineQueryHandler(inline_query))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()
    logging.info("Bot started successfully!")
    job.run_repeating(callback_market, interval=86400, first=0)  # Update markets once a day

    # Block until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()
    logging.info("Bot stopped successfully!")


# Run only if it is the main program, and not when it is referenced from some other code
if __name__ == '__main__':
    main()
