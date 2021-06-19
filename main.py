import sys

import settings

sys.dont_write_bytecode = True
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
import django

django.setup()

from db.models import Feedback

from telegram.ext import Updater, ConversationHandler, CallbackContext, \
    MessageHandler, Filters, CommandHandler
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, \
    ReplyKeyboardRemove, MessageEntity

updater: Updater = Updater(
    token=settings.TELEGRAM_TOKEN)
dispatcher = updater.dispatcher

MENU_STATE, FIRST_NAME_STATE, LAST_NAME_STATE, PHONE_STATE, FEEDBACK_STATE \
    = range(5)


def menu_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton('Yangi fikr')],
        [KeyboardButton('Mening fikrlarim')],
    ], resize_keyboard=True, one_time_keyboard=True)


def phone_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton('Telefon raqam yuborish',
                        request_contact=True)]
    ], resize_keyboard=True, one_time_keyboard=True)


def start_handler(update: Update, context: CallbackContext):
    update.message.reply_text('Salom!', reply_markup=menu_keyboard())
    return MENU_STATE


# def code_handler(update: Update, context: CallbackContext):
#     args = context.args
#     code = ''.join(args)
#
#     if len(code) > 0 and code == '007':
#         update.message.reply_text('Hush kelibsiz, 007')
#     else:
#         return start_handler(update, context)


def menu_handler(update: Update, context: CallbackContext):
    update.message.reply_text(
        'Pastdagi menyuni tanlang',
        reply_markup=menu_keyboard(),
    )
    return MENU_STATE


def new_feedback_handler(update: Update, context: CallbackContext):
    update.message.reply_text('Ismingizni kiriting!')
    return FIRST_NAME_STATE


def first_name_handler(update: Update, context: CallbackContext):
    context.chat_data.update({
        'first_name': update.message.text,
    })
    print(context.chat_data)
    update.message.reply_text('Ajoyib! Ana endi familiyangizni kiriting!')
    return LAST_NAME_STATE


def last_name_handler(update: Update, context: CallbackContext):
    context.chat_data.update({
        'last_name': update.message.text,
    })
    update.message \
        .reply_text('Telefon raqamingizni kiriting, yoki pastdagi '
                    'knopkani bosing',
                    reply_markup=phone_keyboard())

    return PHONE_STATE


def last_name_resend_handler(update: Update, context: CallbackContext):
    update.message.reply_text('Familiyangizni kiriting!')


def phone_entity_handler(update: Update, context: CallbackContext):
    phone_number_entity = pne = \
        list(filter(lambda e: e.type == 'phone_number',
                    update.message.entities))[0]
    phone_number = update.message.text[pne.offset:pne.offset + pne.length]
    context.chat_data.update({
        'phone_number': phone_number,
    })
    update.message.reply_text('Endi fikringizni qoldiring')
    return FEEDBACK_STATE


def phone_contact_handler(update: Update, context: CallbackContext):
    contact = update.message.contact
    context.chat_data.update({
        'phone_number': '+' + contact.phone_number,
    })
    update.message.reply_text('Endi fikringizni qoldiring')
    return FEEDBACK_STATE


def phone_resend_handler(update: Update, context: CallbackContext):
    update.message \
        .reply_text('Telefon raqamingizni kiriting, yoki pastdagi '
                    'knopkani bosing',
                    reply_markup=phone_keyboard())


def feedback_handler(update: Update, context: CallbackContext):
    context.chat_data.update({
        'feedback': update.message.text,
    })
    update.message.reply_text('Fikringiz uchun rahmat!')
    print(context.chat_data)

    cd = context.chat_data

    feedback = Feedback.objects.create(
        first_name=cd['first_name'][0:255],
        last_name=cd['last_name'][0:255],
        phone_number=cd['phone_number'][0:63],
        feedback=cd['feedback'],
        user_id=update.effective_user.id,
    )
    print(feedback)

    return menu_handler(update, context)


def feedback_resend_handler(update: Update, context: CallbackContext):
    update.message.reply_text('Fikringizni matn orqali qoldiring')


def all_feedbacks_handler(update: Update, context: CallbackContext):
    update.message.reply_text(
        'Mening ohirgi 5 ta fikrim'
    )

    feedbacks = Feedback.objects.order_by('-id').filter(user_id=update.effective_user.id)[:5]
    print(feedbacks)
    if len(feedbacks) == 0:
        update.message.reply_text('Siz hech qanday fikr qoldirmagansiz')
    else:
        for feedback in feedbacks:
            update.message.reply_text(f'{feedback.feedback}'
                                      f'\n\n'
                                      f'_{feedback.first_name}_ _{feedback.last_name}_',
                                      parse_mode='Markdown')


def stop_handler(update: Update, context: CallbackContext):
    update.message.reply_text('Hayr!', reply_markup=ReplyKeyboardRemove())


dispatcher.add_handler(ConversationHandler(
    entry_points=[
        # CommandHandler('code', code_handler),
        MessageHandler(Filters.all, start_handler),
    ],
    states={
        MENU_STATE: [
            MessageHandler(Filters.regex(r'^Yangi fikr$'),
                           new_feedback_handler),
            MessageHandler(Filters.regex(r'^Mening fikrlarim$'),
                           all_feedbacks_handler),
            MessageHandler(Filters.all, menu_handler),
        ],
        FIRST_NAME_STATE: [
            MessageHandler(Filters.text, first_name_handler),
            MessageHandler(Filters.all, new_feedback_handler),
        ],
        LAST_NAME_STATE: [
            MessageHandler(Filters.text, last_name_handler),
            MessageHandler(Filters.all, last_name_resend_handler),
        ],
        PHONE_STATE: [
            MessageHandler(
                Filters.text & Filters.entity(MessageEntity.PHONE_NUMBER),
                phone_entity_handler),
            MessageHandler(Filters.contact, phone_contact_handler),
            MessageHandler(Filters.all, phone_resend_handler),
        ],
        FEEDBACK_STATE: [
            MessageHandler(Filters.text, feedback_handler),
            MessageHandler(Filters.all, feedback_resend_handler),
        ],
    },
    fallbacks=[
        CommandHandler('stop', stop_handler),
    ],
))

updater.start_polling()
updater.idle()
