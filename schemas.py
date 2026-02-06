from pydantic import BaseModel
from typing import List, Dict, Any

class QuizRequest(BaseModel):
    url: str
    num_questions: int = 5


class QuizResponse(BaseModel):
    id: int
    url: str
    title: str
    summary: str
    quiz: List[Dict[str, Any]]
    related_topics: List[str]

    class Config:
        orm_mode = True
