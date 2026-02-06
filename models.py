from sqlalchemy import Column, Integer, String, Text
from database import Base

class QuizSession(Base):
    __tablename__ = "quiz_sessions"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, index=True)
    title = Column(String)
    summary = Column(Text)
    quiz_json = Column(Text)  # full generated JSON
