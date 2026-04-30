import os
import logging
import google.generativeai as genai
from database import SessionLocal, Meeting
from datetime import datetime

logger = logging.getLogger(__name__)

# Define a tool for Gemini to update the meeting database
def update_meeting_status(topic: str, date_str: str = None) -> str:
    """Updates the database to mark a topic as completed and logs the meeting.
    Args:
        topic: The topic or book that was discussed.
        date_str: The date of the meeting in YYYY-MM-DD format. Defaults to today.
    """
    db = SessionLocal()
    try:
        meeting_date = datetime.strptime(date_str, "%Y-%m-%d") if date_str else datetime.now()
        meeting = Meeting(topic=topic, date=meeting_date, status="completed")
        db.add(meeting)
        db.commit()
        return f"Successfully logged meeting about '{topic}'."
    except Exception as e:
        return f"Error logging meeting: {str(e)}"
    finally:
        db.close()

def get_system_prompt() -> str:
    curriculum = "Программа кружка не найдена. Пожалуйста, создайте файл curriculum.txt."
    try:
        with open("curriculum.txt", "r", encoding="utf-8") as f:
            curriculum = f.read()
    except FileNotFoundError:
        logger.warning("curriculum.txt not found. Using default prompt.")

    db = SessionLocal()
    try:
        recent_meetings = db.query(Meeting).order_by(Meeting.date.desc()).limit(5).all()
        history = "\n".join([f"- {m.date.strftime('%Y-%m-%d')}: {m.topic} ({m.status})" for m in recent_meetings])
        if not history:
            history = "Пока нет записей о проведенных встречах."
    finally:
        db.close()

    return f"""Ты - дружелюбный ИИ-ассистент 'Филадельфийского кружка по философии'.
Отвечай вежливо, кратко и по делу, опираясь на программу кружка.
Если пользователи говорят, что они закончили обсуждать какую-то тему или книгу, используй инструмент update_meeting_status чтобы записать это в базу.

Текущая история встреч:
{history}

Программа:
{curriculum}
"""

async def generate_response(user_message: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "Ключ GEMINI_API_KEY не настроен. ИИ недоступен."
        
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            tools=[update_meeting_status],
            system_instruction=get_system_prompt()
        )
        
        chat = model.start_chat(enable_automatic_function_calling=True)
        response = chat.send_message(user_message)
        return response.text
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return "Извините, у меня небольшие неполадки с ИИ-модулем. Попробуйте позже."
