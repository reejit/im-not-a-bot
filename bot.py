# -*- coding: utf-8 -*-

'''
I'M NOT A BOT.

This bot it's just a simple implementation of
a captcha for everyone that joins a telegram group.
'''
import html
import yaml
import logging
from time import sleep
from functools import wraps
from telegram.ext.dispatcher import run_async
from telegram import (InlineKeyboardMarkup,
                      InlineKeyboardButton, ChatAction, ChatPermissions)
from telegram.ext import (Updater, CallbackQueryHandler,
                          MessageHandler, Filters)

# reading the config from the yaml file
with open("config.yml", 'r') as ymlfile:
    cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)

# global variable where I'll append the new members IDs
# temporanely when they join and press the button just
# so I can verify if they actually pressed the button
new_members = []

# enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - '
                    '%(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


# simple function for making bold text in HTML
def b(s): return f'<b>{html.escape(s)}</b>'


@run_async
def send_typing_action(func):
    '''
    Decorator that sends an 'is typing..' action.
    '''
    @wraps(func)
    def command_func(update, context, *args, **kwargs):
        context.bot.send_chat_action(
            chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)
        return func(update, context,  *args, **kwargs)

    return command_func


@run_async
def add_group(update, context):
    '''
    This function triggers a new member and it
    restricts the user from doing anything until
    they press the button.
    '''
    # if someone adds manually more members the
    # function will not trigger itself
    if len(update.message.new_chat_members) > 1:
        return
    else:
        # defining chat id and new member object
        chat_id = update.effective_chat.id
        member = update.message.new_chat_members[0]

        # defining a button and adding it to the keyboard
        # the callback is the actual member id converted as
        # string type because telegram doesn't allow ints
        no_but = [InlineKeyboardButton(
            text=cfg['button'], callback_data=str(member.id))]
        keyboard = InlineKeyboardMarkup([no_but])

        # if the member is not a bot (An actual telegram bot)
        if not member.is_bot:
            # if the chat type is 'supergroup',
            # because you can't restrict members
            # in normal groups using the bot
            if update.message.chat.type == 'supergroup':

                text = (cfg['joins_text'].format(b(member.first_name)))

                # this restricts the user from doing anything
                context.bot.restrict_chat_member(
                    chat_id, member.id, ChatPermissions(
                        can_send_messages=False,
                        can_send_media_messages=False,
                        can_send_polls=False,
                        can_send_other_messages=False,
                        can_add_web_page_previews=False,
                        can_change_info=False,
                        can_invite_users=False,
                        can_pin_messages=False))

                # reply to the join message with the text defined
                # in the 'joins_text' of the config.yml and using the
                # keyboard defined in the 'keyboard' variable
                mess = update.message.reply_text(text, parse_mode='HTML',
                                                 reply_markup=keyboard)

                # this function, as every function, runs in a separate thread
                wait(cfg['time_kick'], member.id,
                     context, chat_id, mess.message_id)


@run_async
def wait(time, member_id, context, chat_id, message_id):
    '''
    Async function that waits the seconds defined in time and then
    checks if the user pressed the button
    '''
    # sleeps for the time specified in the
    # 'time_kick' of the config.yml
    sleep(time)

    # if the member is in the global list of
    # new members (meaning they pressed the button)
    # remove they from the list
    if member_id in new_members:
        new_members.remove(member_id)
        return

    # if the member isn't in the global list of
    # new members (meaning they didn't press the button)
    # they will be kicked and the message deleted
    else:
        context.bot.kick_chat_member(chat_id, member_id)
        context.bot.delete_message(chat_id, message_id)


@run_async
def catching_callbacks(update, context):
    '''
    Function that catches the ID as callbacks from the button.
    '''
    member = int(update.callback_query.data)
    chat_id = update.callback_query.message.chat_id
    clicked = update.effective_user.id
    name = update.effective_user.first_name

    # if the actual new member that is in the
    # callback clicks the button
    if member == clicked:

        # removing the restrictions of the member
        context.bot.restrict_chat_member(
            chat_id, member, ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_change_info=True,
                can_invite_users=True,
                can_pin_messages=True))

        # editing the first message and telling
        # the user that everything is ok
        mess = update.callback_query.edit_message_text(
            cfg['notbot_text'].format(b(name)), parse_mode='HTML')

        # adding the member in the global variable
        new_members.append(member)

        # waiting 10 seconds and deleting the message itself
        sleep(10)
        mess.delete()

    # if someone else is pressing the button they will be prompted
    # with the message in 'not4u_text' of the config.yml
    else:
        context.bot.answer_callback_query(
            update.callback_query.id,
            cfg['not4u_text'],
            show_alert=True)


def error(update, context):
    '''
    Logging of all errors.
    '''
    logger.warning(f'Update {update} caused error {context.error}')


def main():
    '''
    main function to make the bot start
    '''
    updater = Updater(cfg['token'], use_context=True)

    # setting the dispatcher handlers
    dp = updater.dispatcher

    # this handler catches every new join
    # updates and starts the 'add_group' funcion
    dp.add_handler(MessageHandler(
        Filters.status_update.new_chat_members, add_group))

    # this handler catches all callbacks defined
    # in the 'catching_callbacks' function
    dp.add_handler(CallbackQueryHandler(catching_callbacks))

    # this handler logs errors
    dp.add_error_handler(error)

    # starting the bot
    updater.start_polling(clean=True)

    # idle to stop the bot gracefully using ctrl-c
    updater.idle()


# starting the main function
if __name__ == '__main__':
    main()
