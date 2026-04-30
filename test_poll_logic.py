import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, User, Poll, PollAnswer
from utils import calculate_day_winner

@pytest.fixture
def db_session():
    """Provides a fresh in-memory SQLite database for each test."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_calculate_day_winner_clear_winner(db_session):
    """Test standard case where one day has more votes."""
    # Setup Data
    user1 = User(id=1, telegram_id=101, username="alice")
    user2 = User(id=2, telegram_id=102, username="bob")
    user3 = User(id=3, telegram_id=103, username="charlie")
    db_session.add_all([user1, user2, user3])
    
    poll = Poll(
        id=1, 
        telegram_poll_id="poll_123", 
        poll_type="choose_day", 
        options="Суббота (04.05),Воскресенье (05.05),Не приду"
    )
    db_session.add(poll)
    
    # Alice votes Sat (0), Bob votes Sat (0) and Sun (1), Charlie votes Sun (1)
    # Sat gets 2 votes, Sun gets 2 votes. Let's make Sat win.
    # Actually let's make Bob only vote Sat.
    db_session.add(PollAnswer(poll_id=1, user_id=1, option_ids="0"))
    db_session.add(PollAnswer(poll_id=1, user_id=2, option_ids="0"))
    db_session.add(PollAnswer(poll_id=1, user_id=3, option_ids="1"))
    db_session.commit()

    winner_text, losers, tied_users = calculate_day_winner(1, db_session)
    
    assert winner_text == "Суббота"
    assert len(losers) == 1
    assert losers[0].username == "charlie"
    assert len(tied_users) == 0

def test_calculate_day_winner_tie(db_session):
    """Test case where multiple days have the same number of votes."""
    user1 = User(id=1, telegram_id=101, username="alice")
    user2 = User(id=2, telegram_id=102, username="bob")
    db_session.add_all([user1, user2])
    
    poll = Poll(
        id=1, 
        telegram_poll_id="poll_123", 
        poll_type="choose_day", 
        options="Суббота (04.05),Воскресенье (05.05),Не приду"
    )
    db_session.add(poll)
    
    # Alice votes Sat (0), Bob votes Sun (1)
    db_session.add(PollAnswer(poll_id=1, user_id=1, option_ids="0"))
    db_session.add(PollAnswer(poll_id=1, user_id=2, option_ids="1"))
    db_session.commit()

    winner_text, losers, tied_users = calculate_day_winner(1, db_session)
    
    assert winner_text == "Суббота/Воскресенье"
    assert len(losers) == 0
    assert len(tied_users) == 2 # both alice and bob are involved in the tie

def test_calculate_day_winner_no_votes(db_session):
    """Test case where no one votes or only 'Не приду' is voted."""
    user1 = User(id=1, telegram_id=101, username="alice")
    db_session.add(user1)
    
    poll = Poll(
        id=1, 
        telegram_poll_id="poll_123", 
        poll_type="choose_day", 
        options="Суббота (04.05),Воскресенье (05.05),Не приду"
    )
    db_session.add(poll)
    
    # Alice votes "Не приду" (2)
    db_session.add(PollAnswer(poll_id=1, user_id=1, option_ids="2"))
    db_session.commit()

    winner_text, losers, tied_users = calculate_day_winner(1, db_session)
    
    assert winner_text == "Голосов нет"
    assert len(losers) == 0
    assert len(tied_users) == 0
