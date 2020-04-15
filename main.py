from telegram import ChatAction, InlineQueryResultArticle, InlineQueryResultDocument, ParseMode, InputTextMessageContent, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, InlineQueryHandler, CallbackQueryHandler, MessageHandler, Filters
from telegram.utils.helpers import escape_markdown
from six.moves import cPickle as pickle
from datetime import datetime
from functools import wraps
from shutil import copy
from emoji import emojize
from uuid import uuid4

import ing_sprinters
import threading
import logging
import queue
import time
import re
import os

flag = False  # Flag to skip inline 1
sprinter = ''  # Sprinter memory
sprinter_ls = ''  # Sprinter + Long/Short memory
add = False  # User selected Track
remove = False  # User selected Remove

keyboard = [
    ["➕ Track",
     emojize(':page_with_curl:') + " List",
     emojize(':wastebasket:') + " Remove",
     emojize(':gear:') + " Settings"]
]

reply_markup = ReplyKeyboardMarkup(
    keyboard=keyboard,
    resize_keyboard=True,
    one_time_keyboard=False)

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
    global keyboard, reply_markup

    message = "I send the stock exchange rates for ING Sprinters!"
    user_id = update.message.from_user['id']
    ing_sprinters.new_user(user_id)

    home(update, context, message)


@send_typing_action
def cancel(update, context):
    global add, remove
    add = False
    remove = False
    message = "Action cancelled!"
    home(update, context, message)


@send_typing_action
def home(update, context, message):
    global keyboard, reply_markup

    context.bot.send_message(chat_id=update.message.chat_id,
                             text=message,
                             parse_mode='Markdown',
                             reply_markup=reply_markup)


# Callback for list paging
def callback_paging(update, context):
    user_id = update._effective_user['id']
    query = update.callback_query
    offset = int(query.data)

    # Load paged data
    with open('database.pkl', 'rb') as file:
        try:
            data = pickle.load(file)
            message_list = data[user_id]["List"]
            message = ''
        except EOFError:
            return None

    for item in message_list[offset][0]:
        message += item

    # Determine button layout
    keyboard = [[
        InlineKeyboardButton("Previous", callback_data=offset - 1),
        InlineKeyboardButton("Next", callback_data=offset + 1)
    ]]
    if offset == 0:  # Next only
        keyboard[0].pop(0)
    if offset == len(message_list) - 1:  # Previous only
        keyboard[0].pop(1)

    reply_markup = InlineKeyboardMarkup(keyboard)

    query.edit_message_text(text=message,
                            parse_mode='Markdown',
                            reply_markup=reply_markup)


# Callback for settings
def callback_settings(update, context):
    user_id = update._effective_user['id']
    query = update.callback_query

    data = ing_sprinters.settings(user_id, query.data)

    query.edit_message_text(text="{}".format(query.data) + " is %s" % (data[1:].lower()))


# Bot actions when messages are sent to the bot
@send_typing_action
def reply(update, context):
    global add, remove, keyboard
    query = update.message.text
    query_st = query[1:].strip()

    user_id = update.message.from_user['id']
    message = ""
    reply_markup = None

    if query_st == "Cancel":
        cancel(update, context)
        return None

    if add is True:
        add = False
        message = ing_sprinters.add(user_id, query)

        if not message:
            message = "Something went wrong!"
        else:
            home(update, context, message)
            return None

    if remove is True:
        remove = False
        result = ing_sprinters.remove(user_id, query)

        if not result:
            message = "Something went wrong!"
        else:
            message = "Done!"
            home(update, context, message)
            return None

    if query_st == "Track":
        message = "📦 I'm ready. Tell me the sprinter's isin. \n\n /cancel"
        add = True

    elif query_st == "List":
        data = ing_sprinters.database()
        track = data[user_id]["Track"].items()

        if data and track:
            message_list = []
            threads = []
            que = queue.Queue()
            for key, value in track:
                for item in value:
                    process = threading.Thread(target=lambda q, arg1: q.put(ing_sprinters.add_to_list(arg1)), args=(que, [user_id, key, item]))
                    process.daemon = True
                    process.start()
                    threads.append(process)
            for process in threads:
                process.join()

            while not que.empty():
                message_list.append(que.get())

            if message_list == []:
                message = "Your list has been cleared of non existing sprinters and there's nothing left!"

            else:
                message_list = list(ing_sprinters.chunks(message_list, 5))  # 5 items per page (message)

                for item in message_list[0]:
                    message += item
                if len(message_list) > 1:
                    data = ing_sprinters.database()
                    with open('database.pkl', 'wb') as file:
                        data[user_id]["List"] = message_list
                        pickle.dump(data, file)

                    keyboard = [[InlineKeyboardButton("Next", callback_data=1)]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
        else:
            message = "Your list is empty!"

    elif query_st == "Remove":
        message = "📦 I'm ready. Tell me the sprinter's isin. \n\n /cancel"
        remove = True

        data = ing_sprinters.database()

        if data:
            keyboard = [[emojize(":cross_mark:") + " Cancel"]]
            track = data[user_id]["Track"].items()

            reply_markup = ReplyKeyboardMarkup(
                keyboard=keyboard,
                resize_keyboard=True,
                one_time_keyboard=True)

            for key, val in track:
                for item in val:
                    keyboard.append(["%s %s" % (key, item)])

    elif query_st == "Settings":
        keyboard = []

        message = "*Settings:*\n"

        data = ing_sprinters.database()

        for key, value in data[user_id]["Settings"].items():
            message += ("%s: %s\n" % (key, value))
            keyboard.append([InlineKeyboardButton(
                (value[0] + key), callback_data=key)])

        reply_markup = InlineKeyboardMarkup(keyboard)

    else:
        message = "Welcome back!"
        keyboard = keyboard
        reply_markup = ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True,
            one_time_keyboard=False)

    context.bot.send_message(chat_id=update.message.chat_id,
                             text=message,
                             parse_mode='Markdown',
                             reply_markup=reply_markup,
                             disable_web_page_preview=True)


@send_typing_action
def market(update, context):
    query = update.message.text.replace("/market", "").strip()

    if not query:
        message = 'Type the market for information about the exchange rate:\n `/market AEX`'
        context.bot.send_message(
            chat_id=update.message.chat_id, text=message, parse_mode='Markdown')
        return None

    result = ing_sprinters.market_info(query)
    key = list(result.keys())
    value = list(result.values())
    percentage = value[0].split(" ")[1]
    val1 = ""

    if "-" in percentage:
        val1 = emojize(':down_arrow:')  # ⬇️
    elif float(percentage.replace(",", ".")) != 0.00:
        val1 = emojize(':up_arrow:')  # ⬆️

    message = '*' + query + '*'
    message += "\n*%s* _%s_ _%s_" % (key[0], val1, value[0])

    context.bot.send_message(
        chat_id=update.message.chat_id, text=message, parse_mode='Markdown')


@send_typing_action
def ing(update, context):
    query = update.message.text.replace("/ing", "").strip()

    if not query:
        message = 'Type the market and isin for information about the exchange rate of a sprinter:\n `/ing AEX NL0012065692`'
        context.bot.send_message(
            chat_id=update.message.chat_id, text=message, parse_mode='Markdown')
        return None

    query = query.split()
    sprinter_name = " ".join(query[:-1])
    isin = query[-1]

    data = ing_sprinters.database()
    with open('database.pkl', 'rb') as file:
        try:
            data = pickle.load(file)
            if not (sprinter_name in data['markets']):
                return None
        except EOFError:
            return None

    # with open("markets.txt", "r") as file:
    #     if not (sprinter_name in file.read()):
    #         return None

    result = ing_sprinters.sprinter_info(isin)

    if result is not None:
        keys = list(result.keys())
        values = list(result.values())

        val1 = ""
        val2 = ""

        if "-" in values[2]:
            val1 = emojize(':down_arrow:')  # ⬇️
        elif float(values[2][:-2].replace(",", ".")) != 0.00:
            val1 = emojize(':up_arrow:')  # ⬆️

        if "-" in values[5][1]:
            val2 = emojize(':down_arrow:')  # ⬇️
        elif "+" in values[5][1]:
            val2 = emojize(':up_arrow:')  # ⬆️

        message = '*' + sprinter_name + '*' + \
            "\n*%s*                           _%s_" % (keys[0], values[0]) + \
            "\n*%s*                           _%s_" % (keys[1], values[1]) + \
            "\n*%s*                    _%s_ _%s_" % (keys[2], val1, values[2]) + \
            "\n*%s*                 _%s_" % (keys[3], values[3]) + \
            "\n*%s*  _%s_" % (keys[4], values[4]) + \
            "\n*%s*   _%s_ _%s_ _%s_" % (keys[5],
                                         val2, values[5][0], values[5][1])

    else:
        message = "Sprinter doesn't exist!"

    context.bot.send_message(
        chat_id=update.message.chat_id, text=message, parse_mode='Markdown')


def inline_query(update, context):
    """Handle the inline query."""
    query = update.inline_query.query
    global flag, sprinter, sprinter_ls

    logging.debug("Query: " + query)

    # Inline 1 Shows current markets
    if not flag:
        logging.debug("Inline 1")
        results = []

        data = ing_sprinters.database()
        with open('database.pkl', 'rb') as file:
            try:
                data = pickle.load(file)
                titles = data['markets']
            except EOFError:
                return None

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

        query_short = query.lower().replace(sprinter_ls.lower() + ' ',
                                            '')  # Remove first two inlines from query
        # Extract numbers from the shortened query
        query_nr = re.findall(r'\d*\,?\d+', query_short)
        sprinters = ing_sprinters.sprinter_list(
            sprinter_ls)  # Retreive list of sprinters

        for key, value in sprinters.items():
            key_nr = re.findall(r'\d*\,?\d+', key)

            # If sprinter (key), isin (value) or number (inside key) match
            if key.lower().startswith(query_short) \
                    or value.lower().startswith(query_short) \
                    or (key_nr[-1].startswith(query_nr[-1])):
                output = sprinter + ' ' + value  # Sprinter + Long/Short + isin
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

    update.inline_query.answer(
        results=results[offset:offset + 50], next_offset=str(offset + 50))


# Add market/sprinter to favorites
@send_typing_action
def add(update, context):
    user_id = update.message.from_user['id']
    query = update.message.text.replace("/add", "").strip()

    message = ing_sprinters.add(user_id, query)

    context.bot.send_message(
        chat_id=update.message.chat_id, text=message, parse_mode='Markdown')


# remove market or sprinter
@send_typing_action
def remove(update, context):
    user_id = update.message.from_user['id']
    query = update.message.text.replace("/remove", "").strip()

    message = ing_sprinters.remove(user_id, query)

    context.bot.send_message(
        chat_id=update.message.chat_id, text=message, parse_mode='Markdown')


def callback_market(context):
    ing_sprinters.markets()
    logging.debug("Market list updated!")


def backup(context):
    list_of_files = os.listdir("Backups")

    if len(list_of_files) >= 5:  # Backup count
        for x in range(len(list_of_files) - 5):
            list_of_files = os.listdir("Backups")
            full_path = ["Backups/{0}".format(x) for x in list_of_files]
            oldest_file = min(full_path, key=os.path.getmtime)
            os.remove(oldest_file)
            logging.debug("Deleted file: " + oldest_file)

    copy("database.pkl", "Backups/database_" + str(datetime.now().strftime("%Y_%m_%d")) + ".pkl")

    logging.debug("Database backed up!")


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

    if not os.path.exists("Backups"):
        os.makedirs("Backups")

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
    dp.add_handler(CommandHandler("cancel", cancel))
    dp.add_handler(CommandHandler("home", home))

    dp.add_handler(InlineQueryHandler(inline_query))
    dp.add_handler(MessageHandler(Filters.text, reply))
    dp.add_handler(CallbackQueryHandler(callback_settings, pattern="^(.*[a-zA-Z% -])$"))
    dp.add_handler(CallbackQueryHandler(callback_paging, pattern="^([0-9])+$"))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()
    logging.info("Bot started successfully!")
    job.run_repeating(callback_market, interval=86400,
                      first=1)  # Update markets once a day
    job.run_repeating(backup, interval=86400,
                      first=1)  # Backup database once a day

    # Block until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()
    logging.info("Bot stopped successfully!")


# Run only if it is the main program, and not when it is referenced from some other code
if __name__ == '__main__':
    main()
