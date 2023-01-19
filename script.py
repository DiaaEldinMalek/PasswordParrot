#!/usr/bin/env python
# pylint: disable=unused-argument, wrong-import-position
# This program is dedicated to the public domain under the CC0 license.

BOT_TOKEN = '5908452830:AAGMNG43D-g33YVC7j4aifsUEKeRlnBypM8'

import logging

from telegram import __version__ as TG_VER

from pymongo_scripts import (
    get_user_data,
    set_user_data,
    user_exists,
    add_credential,
    get_credential_list,
    get_credential,
    delete_credential)

from collections import defaultdict

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO,
    filename='logfile.log', filemode = 'a'
)
logger = logging.getLogger(__name__)

GENDER, PHOTO, LOCATION, BIO = range(4)
NAME, EMAIL, OPTIONS, ADD_CRED, RET_CRED, DEL_CRED, SET_EXPIRY, SET_TIMER = range(8)

user_data_dict = {} #item: _id: {'_id', 'name_default', 'name_preferred', 'email'}
scheduled_delete = {} #item: _id: {service', 'is_scheduled'}





async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation checks if the user is in our database"""

    user = update.message.from_user

    user_id = str(user.id)
    username = user.first_name


    if user_exists(user_id):
        name_preferred = get_user_data(user_id, 'name_preferred')
        if name_preferred:
            username = name_preferred
        recognized =True
    else:
        pass
        recognized = False

    message = f"Hi {username}! I am Password Parrot, the solution to all your password managing needs. Send /exit anytime to stop talking to me.\n\n"

    if recognized:
        logger.info(f"User {user_id} started a conversation. User recognized as {username}")
        await update.message.reply_text(message)
        return await open_menu(update)

    else:
        logger.info(f"User {user_id} started a conversation. No data for the user was found in database")
        message += "It seems this is our first conversation, so please allow me to gather some information about you.\n\n"+\
        "Please enter your first name, or send /skip if you want me to use your telegram name"

        #nested dictionary, to prevent multiple users' data from mixing together if they use the bot at the same time
        user_data_dict[user_id] = {'_id': user_id, 'name_default': username}
        await update.message.reply_text(message)
        return NAME


async def name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the user's name"""

    user = update.message.from_user
    user_id = str(user.id)
    name_preferred = update.message.text.strip()

    user_data_dict[user_id]['name_preferred'] = name_preferred

    logger.info("Preferred Name of %s: %s", user_id, name_preferred)
    await update.message.reply_text(
        f"Nice to meet you, {name_preferred}!\n\n"
        "Please type in your email address, or /skip to skip this step",
    )

    return EMAIL

async def skip_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skips the name and uses the default name instead. Moves to email"""

    user = update.message.from_user
    user_id = str(user.id)

    user_data_dict[user_id]['name_preferred'] = None

    logger.info(f"User {user_id} skipped their name. Telegram name ({user.first_name}) will be used instead")
    await update.message.reply_text(
        f"Oh, okay then..... From here on out, I will refer to you as {user.first_name}. \n\n"
        "Please type in your email address, or /skip to skip this step",
    )

    return EMAIL


async def email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the email and saves data"""

    user = update.message.from_user
    user_id = str(user.id)

    user_data_dict[user_id]['email'] = update.message.text.strip()

    logger.info("Email address of %s: %s", user.first_name, update.message.text)
    await update.message.reply_text(
        f"Got it, thank you! One moment while I store this information somewhere secure.",
    )
    # logger.info("Uploading user data to mongodb")
    set_user_data(user_id, user_data_dict[user_id])
    #store information to mongodb

    return await open_menu(update)


async def skip_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skips the email and saves data. Moves to menu"""

    user = update.message.from_user
    user_id = str(user.id)

    user_data_dict[user_id]['email'] = None

    logger.info(f"User {user.first_name} skipped their email address")
    await update.message.reply_text(
        "No problem, I will leave this field empty. One moment while I store this information somewhere secure."
    )
    set_user_data(user_id, user_data_dict[user_id])

    return await open_menu(update)


possible_commands = {"ret_data" : "Retrieve user data",
            "add_cred" : "Add new credential record",
            "ret_cred" : "Retrieve credential record",
            "view_all" : "View all credential records",
            "del_cred" : "Remove exact credential record",
            "set_expiry" : "Mark a credential record to expire after time",
            "cancel" : "Cancel current operation and display options",
            "exit" : "Exit program"
}

async def open_menu(update: Update):
    """Display command options to user"""
    menu_msg = 'What would you like to do?\n\n' + '\n'.join([f"/{key} -> {val}" for key,val in possible_commands.items()])


    await update.message.reply_text(menu_msg, reply_markup=ReplyKeyboardRemove())

    return OPTIONS

async def buffer(update: Update, context: ContextTypes.DEFAULT_TYPE, command: str) ->int:
    """Buffer function that prompts input for commands that handle a single credential record"""

    reply_keyboard = [get_credential_list(str(update.message.from_user.id), services_only =True)]

    if command == 'add_cred':
        await update.message.reply_text(
        "Please enter service name, followed by the username and password, each in its own line.\n"
        "Example:\n\nFacebook\njohn.doe@gmail.com\nqwertyqwerty"
        )
        return ADD_CRED
    elif command == 'ret_cred':
        await update.message.reply_text(
        "Please enter service name of the record you wish to retrieve. For a list of available records, click /view_all",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=False, input_field_placeholder="Schedule expiry"
            ),
        )
        return RET_CRED
    elif command == 'del_cred':

        await update.message.reply_text(
        "Please enter service name of the record you wish to delete. For a list of available records, click /view_all",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=False, input_field_placeholder="Schedule expiry"
            ),
        )
        return DEL_CRED
    elif command == 'set_expiry':
        # reply_keyboard = [get_credential_list(str(update.message.from_user.id), services_only =True)]
        await update.message.reply_text(
        "Please choose service name of the record to set an expiry date",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=False, input_field_placeholder="Schedule expiry"
            ),
        )
        return SET_EXPIRY

async def ret_data(update: Update, context: ContextTypes.DEFAULT_TYPE) ->int:
    """Retrieve user data"""

    key_to_display_mapping = {'_id': 'Telegram_ID',
                              'name_default': 'Telegram username',
                              'name_preferred': 'Given name',
                              'email' :'Email Address'}

    user = update.message.from_user
    user_id = str(user.id)

    logger.info(f"Retrieving user data for user {user_id}")
    user_data = get_user_data(user_id, 'all')
    logger.info("Displaying user data")
    msg = '\n\n'.join([f'{key_to_display_mapping[key]}: \n{val}' for key, val in user_data.items()])
    await update.message.reply_text(msg)

    return await open_menu(update)
    # return OPTIONS


async def add_cred(update: Update, context: ContextTypes.DEFAULT_TYPE) ->int:
    """Add new credential"""
    user = update.message.from_user
    user_id = str(user.id)

    user_response = update.message.text.strip().split('\n')
    if len(user_response) != 3:
        await update.message.reply_text("Invalid response")

        return await open_menu(update)

    credential = {}
    for i, key in enumerate(['service', 'username', 'password']):
        credential[key] = user_response[i].strip()
    credential['service'] = credential['service'].lower()

    response = add_credential(user_id, credential)
    if response:
        await update.message.reply_text(f"'{credential['service']}' credential added successfuly")
    else:
        await update.message.reply_text("Duplicate credential")

    return await open_menu(update)



async def ret_cred(update: Update, context: ContextTypes.DEFAULT_TYPE) ->int:
    """Retrieve specified credential"""
    user = update.message.from_user
    user_id = str(user.id)

    queried_service = update.message.text.strip()
    logger.info(f"Querying {queried_service} credential for user {user_id}")

    credential = get_credential(user_id, queried_service)
    if not credential:
        await update.message.reply_text("Record cannot be found. Click /view_all for all available records")
    else:
        msg = f"Service: {credential['service']}\n" +\
                f"Username: {credential['username']}\n"+\
                f"Password: {credential['password']}"
        await update.message.reply_text(msg)


    return await open_menu(update)
    # return OPTIONS

async def del_cred(update: Update, context: ContextTypes.DEFAULT_TYPE) ->int:
    """Delete credential from database"""
    user = update.message.from_user
    user_id = str(user.id)

    queried_service = update.message.text.strip()

    response = delete_credential(user_id, queried_service)

    if response:
        await update.message.reply_text(f"{queried_service} credential deleted successfuly")
    else:
        await update.message.reply_text("Did not find credential to delete")

    return await open_menu(update)


async def view_all(update: Update, context: ContextTypes.DEFAULT_TYPE) ->int:
    """View all credential records"""
    user = update.message.from_user
    user_id = str(user.id)

    logger.info(f"Querying all credentials of user {user_id}")
    cred_list = get_credential_list(user_id)

    if not cred_list:
        await update.message.reply_text("No records to show")
        logger.info("Did not find any records")

    else:
        msg = ''
        for i, credential in enumerate(cred_list):
            msg += f"Service: {credential['service']}\nUsername: {credential['username']}\n\n"
        await update.message.reply_text(msg)

    return await open_menu(update)
    # return OPTIONS

async def set_expiry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    user_id = str(user.id)
    queried_service = update.message.text.strip()
    logger.info(f"User {user_id} selected '{queried_service}' credential to expire")
    scheduled_delete[user_id] = queried_service

    await update.message.reply_text(
        "Please set an expiry time for the credential.\n Usage: /set <seconds>",

    )
    return SET_TIMER


async def set_timer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set expiry time of record, and add job to queue"""
    chat_id = update.effective_message.chat_id
    try:
        # args[0] should contain the time for the timer in seconds
        due = float(context.args[0])
        if due < 0:
            await update.effective_message.reply_text("Sorry we can not go back to future!")
            return

        user_id = str(update.message.from_user.id)
        job_removed = remove_job_if_exists(str(chat_id), context)
        context.job_queue.run_once(scheduled_remove, due, chat_id=chat_id, name=str(chat_id), data=((due, user_id, scheduled_delete[user_id])))
        logger.info(f"'{scheduled_delete[user_id]}' credential of user {user_id} set to expire in {due} seconds")

        text = "Timer successfully set!"
        if job_removed:
            text += " Old one was removed."
        await update.effective_message.reply_text(text)

    except (IndexError, ValueError):
        await update.effective_message.reply_text("Usage: /set <seconds>")

    return await open_menu(update)

async def scheduled_remove(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove the credential as per the schedule"""
    job = context.job
    due, user_id, service = job.data
    msg = f"Beep! {due} seconds are over!"

    if service not in get_credential_list(user_id, services_only =True):
        msg += " Could not find credential record"
    else:
        msg += f" Your credential for '{service}' has expired."
        response = delete_credential(user_id, service)

    await context.bot.send_message(job.chat_id, text=msg)


def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels current task and display menu."""
    user = update.message.from_user
    logger.info("User %s canceled the operation.", user.first_name)

    return OPTIONS

async def exit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Exits program"""
    user = update.message.from_user
    logger.info("User %s exited the conversation.", user.first_name)
    await update.message.reply_text(
        "Bye! I hope we can talk again some day.", reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


def main() -> None:
    """Run the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(BOT_TOKEN).build()



    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), MessageHandler(filters.Regex("^([h,H]ello|[h,H]i)"), start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name), CommandHandler("skip", skip_name)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, email), CommandHandler("skip", skip_email)],
            OPTIONS: [
                    CommandHandler("ret_data", ret_data),
                    # CommandHandler("view_all", view_all),
                    CommandHandler("add_cred", lambda update, context : buffer(update, context, command= 'add_cred')),
                    CommandHandler("ret_cred", lambda update, context : buffer(update, context, command= 'ret_cred')),
                    CommandHandler("del_cred", lambda update, context : buffer(update, context, command= 'del_cred')),
                    CommandHandler("set_expiry", lambda update, context : buffer(update, context, command= 'set_expiry')),
                      ],
            ADD_CRED: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_cred)],
            RET_CRED: [MessageHandler(filters.TEXT & ~filters.COMMAND, ret_cred)],
            DEL_CRED: [MessageHandler(filters.TEXT & ~filters.COMMAND, del_cred)],
            SET_EXPIRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_expiry)],
            SET_TIMER:[CommandHandler("set", set_timer)]

        },
        fallbacks=[
        CommandHandler("exit", exit),
        CommandHandler("cancel", cancel),
        CommandHandler("view_all", view_all)],

    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == "__main__":
    main()
