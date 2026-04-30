import os
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=True)
    username = Column(String, unique=True, nullable=True)
    first_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

class Poll(Base):
    __tablename__ = 'polls'
    id = Column(Integer, primary_key=True)
    telegram_poll_id = Column(String, unique=True)
    message_id = Column(Integer)
    poll_type = Column(String) # 'choose_day' or 'choose_time'
    is_closed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    winning_option = Column(String, nullable=True)
    options = Column(String) # comma-separated list of option text for reference

class PollAnswer(Base):
    __tablename__ = 'poll_answers'
    id = Column(Integer, primary_key=True)
    poll_id = Column(Integer, ForeignKey('polls.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    option_ids = Column(String) # comma-separated list of chosen option indices
    
    poll = relationship("Poll", backref="answers")
    user = relationship("User", backref="answers")

class Meeting(Base):
    __tablename__ = 'meetings'
    id = Column(Integer, primary_key=True)
    date = Column(DateTime)
    topic = Column(String)
    status = Column(String, default="upcoming") # 'upcoming', 'completed'
    notes = Column(String, nullable=True)

engine = create_engine(os.environ.get("DATABASE_URL", "sqlite:///bot.db"))
SessionLocal = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
