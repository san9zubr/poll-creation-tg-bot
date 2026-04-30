import os
from dotenv import load_dotenv

# Load env vars before importing any local modules that depend on them
load_dotenv()

import logging
from datetime import datetime, date, timedelta

from telegram import Update
from telegram.constants import MessageEntityType
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    PollAnswerHandler,
    filters,
)

from database import init_db, SessionLocal, User, Poll, PollAnswer, Meeting
from utils import get_closest_weekday, calculate_day_winner, get_missing_voters
from ai import generate_response

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
if CHAT_ID:
    CHAT_ID = int(CHAT_ID)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tracks users and triggers AI if mentioned."""
    if not update.message:
        return
        
    # 1. Handle users leaving
    db = SessionLocal()
    try:
        if update.message.left_chat_member:
            left_user = update.message.left_chat_member
            user = db.query(User).filter(User.telegram_id == left_user.id).first()
            if user:
                user.is_active = False
                db.commit()
                logger.info(f"User {user.first_name} left chat, marked inactive.")
            return

        # 2. Silently track active users
        sender = update.message.from_user
        if sender and not sender.is_bot:
            _add_user(db, sender.id, sender.username, sender.first_name)

        if update.message.entities:
            for entity in update.message.entities:
                if entity.type == MessageEntityType.MENTION:
                    username = update.message.text[entity.offset:entity.offset+entity.length].lstrip('@')
                    _add_user(db, None, username, None)
                elif entity.type == MessageEntityType.TEXT_MENTION:
                    user = entity.user
                    if not user.is_bot:
                        _add_user(db, user.id, user.username, user.first_name)
    finally:
        db.close()
        
    # 2. Check for AI Trigger
    text = update.message.text
    if not text:
        return
        
    bot_username = context.bot.username
    is_reply_to_bot = (
        update.message.reply_to_message and 
        update.message.reply_to_message.from_user.username == bot_username
    )
    is_mentioned = bot_username and f"@{bot_username}" in text
    starts_with_bot = text.lower().startswith("бот")

    if is_reply_to_bot or is_mentioned or starts_with_bot:
        # Show 'typing...' action
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
        response = await generate_response(text)
        await update.message.reply_text(response)

def _add_user(db, tg_id, username, first_name):
    """Helper to add/update user in DB."""
    if tg_id:
        user = db.query(User).filter(User.telegram_id == tg_id).first()
    elif username:
        user = db.query(User).filter(User.username == username).first()
    else:
        return

    if not user:
        user = User(telegram_id=tg_id, username=username, first_name=first_name)
        db.add(user)
        db.commit()
        logger.info(f"Added new user to DB: {first_name or username}")
    else:
        # Update info if we have more now
        modified = False
        if tg_id and not user.telegram_id:
            user.telegram_id = tg_id
            modified = True
        if first_name and not user.first_name:
            user.first_name = first_name
            modified = True
        if modified:
            db.commit()

async def send_tuesday_poll(context: ContextTypes.DEFAULT_TYPE):
    """Job to send the day selection poll on Tuesday."""
    closest_saturday = get_closest_weekday(5)  # 5=Sat
    closest_sunday = get_closest_weekday(6)  # 6=Sun
    
    # We can format the dates nicely if babel is not available yet
    options = [
        f"Суббота ({closest_saturday.strftime('%d.%m')})",
        f"Воскресенье ({closest_sunday.strftime('%d.%m')})",
        "Не приду",
    ]
    
    message = await context.bot.send_poll(
        chat_id=CHAT_ID,
        question="Выбираем день встречи",
        options=options,
        is_anonymous=False,
        allows_multiple_answers=True,
    )
    
    # Save to DB
    db = SessionLocal()
    try:
        poll = Poll(
            telegram_poll_id=message.poll.id,
            message_id=message.message_id,
            poll_type="choose_day",
            options=",".join(options)
        )
        db.add(poll)
        db.commit()
    finally:
        db.close()

async def send_vote_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Job to send a reminder to users who haven't voted yet."""
    db = SessionLocal()
    try:
        open_polls = db.query(Poll).filter(Poll.is_closed == False).all()
        for poll in open_polls:
            missing = get_missing_voters(poll.id, db)
            if missing:
                tags = " ".join([f"@{u.username}" for u in missing if u.username])
                if tags:
                    await context.bot.send_message(
                        chat_id=CHAT_ID, 
                        text=f"Напоминалка проголосовать! Не забудьте оставить свой голос ☝️\n{tags}"
                    )
    finally:
        db.close()

async def send_thursday_poll(context: ContextTypes.DEFAULT_TYPE):
    """Job to send the time selection poll on Thursday based on Tuesday's winner."""
    db = SessionLocal()
    try:
        # Find the latest open choose_day poll
        tuesday_poll = db.query(Poll).filter(
            Poll.poll_type == "choose_day", 
            Poll.is_closed == False
        ).order_by(Poll.created_at.desc()).first()
        
        winning_day_text = "Суббота/Воскресенье"
        if tuesday_poll:
            tuesday_poll.is_closed = True
            
            winner_text, losers, tied_users = calculate_day_winner(tuesday_poll.id, db)
            winning_day_text = winner_text
            
            if losers:
                tags = " ".join([f"@{u.username}" for u in losers if u.username])
                if tags:
                    await context.bot.send_message(
                        chat_id=CHAT_ID, 
                        text=f"Большинство за {winner_text}. {tags}, сможете прийти?"
                    )
            elif tied_users:
                tags = " ".join([f"@{u.username}" for u in tied_users if u.username])
                if tags:
                    await context.bot.send_message(
                        chat_id=CHAT_ID, 
                        text=f"У нас ничья ({winner_text})! {tags}, кто-то сможет перенести свои планы?"
                    )
                
            db.commit()

        options = [
            "После 12pm", "После 1pm", "После 2pm",
            "После 3pm", "После 4pm", "После 5pm",
            "После 6pm", "После 7pm", "Не приду",
        ]

        message = await context.bot.send_poll(
            chat_id=CHAT_ID,
            question=f"Выбираем время встречи ({winning_day_text})",
            options=options,
            is_anonymous=False,
            allows_multiple_answers=True,
        )
        
        poll = Poll(
            telegram_poll_id=message.poll.id,
            message_id=message.message_id,
            poll_type="choose_time",
            options=",".join(options)
        )
        db.add(poll)
        db.commit()
    finally:
        db.close()

async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tracks votes as they come in."""
    answer = update.poll_answer
    db = SessionLocal()
    try:
        # Ensure user exists
        user_id = answer.user.id
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            user = User(telegram_id=user_id, first_name=answer.user.first_name, username=answer.user.username)
            db.add(user)
            db.commit()

        poll = db.query(Poll).filter(Poll.telegram_poll_id == answer.poll_id).first()
        if not poll:
            return # Poll not tracked by us
        
        # Check if answer exists, update it or create new
        existing_answer = db.query(PollAnswer).filter(
            PollAnswer.poll_id == poll.id,
            PollAnswer.user_id == user.id
        ).first()

        option_str = ",".join(map(str, answer.option_ids))

        if existing_answer:
            existing_answer.option_ids = option_str
        else:
            new_answer = PollAnswer(
                poll_id=poll.id,
                user_id=user.id,
                option_ids=option_str
            )
            db.add(new_answer)
        db.commit()
    finally:
        db.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот запущен и готов к работе!")

if __name__ == "__main__":
    init_db()
    
    if not BOT_TOKEN or not CHAT_ID:
        logger.error("BOT_TOKEN or CHAT_ID is missing in .env file.")
        exit(1)

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(PollAnswerHandler(handle_poll_answer))
    # Track any message to silently build the user DB and handle AI
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    
    # TODO: Add APScheduler jobs for the polls
    
    logger.info("Starting bot...")
    app.run_polling()
