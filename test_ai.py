import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, Meeting
from ai import get_system_prompt, update_meeting_status
import ai

@pytest.fixture
def db_session(monkeypatch):
    """Provides a fresh in-memory SQLite database and patches SessionLocal."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    
    # Patch the SessionLocal in ai.py to use our in-memory DB for tests
    monkeypatch.setattr(ai, 'SessionLocal', Session)
    
    session = Session()
    yield session
    session.close()

def test_update_meeting_status(db_session):
    # Test adding a meeting
    result = update_meeting_status("Plato Republic", "2024-05-01")
    assert "Successfully" in result
    
    meetings = db_session.query(Meeting).all()
    assert len(meetings) == 1
    assert meetings[0].topic == "Plato Republic"
    assert meetings[0].status == "completed"
    assert meetings[0].date.strftime("%Y-%m-%d") == "2024-05-01"

def test_get_system_prompt_with_history(db_session, tmp_path, monkeypatch):
    # Create a temporary curriculum file
    curr_file = tmp_path / "curriculum.txt"
    curr_file.write_text("Fake Curriculum", encoding="utf-8")
    
    # Change working directory so it finds the tmp file
    monkeypatch.chdir(tmp_path)
    
    # Add meeting history
    m1 = Meeting(topic="Topic A", date=datetime(2024, 1, 1), status="completed")
    m2 = Meeting(topic="Topic B", date=datetime(2024, 2, 1), status="completed")
    db_session.add_all([m1, m2])
    db_session.commit()
    
    prompt = get_system_prompt()
    
    assert "Fake Curriculum" in prompt
    assert "Topic A" in prompt
    assert "Topic B" in prompt
    assert "2024-01-01" in prompt
