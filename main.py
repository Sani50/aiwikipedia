from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import json

from database import SessionLocal, engine
from models import Base, QuizSession
from schemas import QuizRequest
from scraper import scrape_wikipedia
from llm import generate_quiz

app = FastAPI(title="AI Wiki Quiz Generator")

# ✅ CREATE TABLES
Base.metadata.create_all(bind=engine)

# ✅ CORS FIX (THIS IS THE IMPORTANT PART)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",  # ✅ allows null (local file), Netlify, etc.
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- DB DEPENDENCY ----------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------- PREVIEW ----------------

@app.post("/preview")
def preview_url(payload: dict):
    url = payload.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    try:
        data = scrape_wikipedia(url)
        return {
            "title": data["title"],
            "summary": data["summary"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ---------------- GENERATE QUIZ ----------------

@app.post("/generate-quiz")
def generate_quiz_api(req: QuizRequest, db: Session = Depends(get_db)):

    try:
        scraped = scrape_wikipedia(req.url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    required = req.num_questions or 5
    all_questions = []
    attempts = 0
    related_topics = []

    while len(all_questions) < required and attempts < 3:
        llm_output = generate_quiz(
            content=scraped["content"],
            num_questions=required - len(all_questions)
        )

        if isinstance(llm_output, dict):
            quiz_chunk = llm_output.get("quiz", [])
            if isinstance(quiz_chunk, list):
                all_questions.extend(quiz_chunk)

            related_topics = llm_output.get("related_topics", [])

        attempts += 1

    quiz_list = all_questions[:required]

    existing = db.query(QuizSession).filter(
        QuizSession.url == req.url
    ).first()

    if existing:
        existing.title = scraped["title"]
        existing.summary = scraped["summary"]
        existing.quiz_json = json.dumps({
            "quiz": quiz_list,
            "related_topics": related_topics
        })
        quiz_session = existing
    else:
        quiz_session = QuizSession(
            url=req.url,
            title=scraped["title"],
            summary=scraped["summary"],
            quiz_json=json.dumps({
                "quiz": quiz_list,
                "related_topics": related_topics
            })
        )
        db.add(quiz_session)

    db.commit()
    db.refresh(quiz_session)

    return {
        "id": quiz_session.id,
        "url": quiz_session.url,
        "title": quiz_session.title,
        "summary": quiz_session.summary,
        "quiz": quiz_list,
        "related_topics": related_topics
    }

# ---------------- FETCH SAVED QUIZZES ----------------

@app.get("/quizzes")
def list_quizzes(db: Session = Depends(get_db)):
    return db.query(QuizSession).all()

@app.get("/quiz/{quiz_id}")
def quiz_details(quiz_id: int, db: Session = Depends(get_db)):
    q = db.query(QuizSession).filter(QuizSession.id == quiz_id).first()

    if not q:
        raise HTTPException(status_code=404, detail="Quiz not found")

    data = json.loads(q.quiz_json)
    return {
        "id": q.id,
        "url": q.url,
        "title": q.title,
        "summary": q.summary,
        "quiz": data.get("quiz", []),
        "related_topics": data.get("related_topics", [])
    }
