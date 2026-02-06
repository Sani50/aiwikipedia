from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import json
import pathlib

from database import SessionLocal, engine
from models import Base, QuizSession
from schemas import QuizRequest
from scraper import scrape_wikipedia
from llm import generate_quiz

app = FastAPI(title="AI Wiki Quiz Generator")
Base.metadata.create_all(bind=engine)

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent

@app.get("/", response_class=HTMLResponse)
def serve_frontend():
    return (BASE_DIR / "frontend" / "index.html").read_text(encoding="utf-8")

@app.post("/preview")
def preview_url(req: QuizRequest):
    try:
        data = scrape_wikipedia(req.url)
        return {
            "title": data["title"],
            "summary": data["summary"]
        }
    except Exception as e:
        return {"error": str(e)}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/generate-quiz")
def generate_quiz_api(req: QuizRequest, db: Session = Depends(get_db)):

    # ❌ DISABLE CACHE (was causing same quiz every time)
    # existing = db.query(QuizSession).filter(
    #     QuizSession.url == req.url
    # ).first()

    # Scrape Wikipedia
    try:
        scraped = scrape_wikipedia(req.url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    required = req.num_questions or 5
    all_questions = []
    attempts = 0
    last_related_topics = []

    while len(all_questions) < required and attempts < 3:
        llm_output = generate_quiz(
            content=scraped["content"],
            num_questions=required - len(all_questions)
        )

        # 🔒 GUARD AGAINST BAD LLM OUTPUT
        if not isinstance(llm_output, dict):
            attempts += 1
            continue

        quiz_chunk = llm_output.get("quiz", [])
        if not isinstance(quiz_chunk, list):
            attempts += 1
            continue

        all_questions.extend(quiz_chunk)
        last_related_topics = llm_output.get("related_topics", [])
        attempts += 1

    quiz_list = all_questions[:required]

    # Store in DB
    quiz_session = QuizSession(
        url=req.url,
        title=scraped["title"],
        summary=scraped["summary"],
        quiz_json=json.dumps({
            "quiz": quiz_list,
            "related_topics": last_related_topics
        })
    )
    
    
    
    try:
        db.add(quiz_session)
        db.commit()
        db.refresh(quiz_session)
    except Exception:
        db.rollback()

        existing = db.query(QuizSession).filter(
        QuizSession.url == req.url
        ).first()

        if existing:
            existing.title = scraped["title"]
            existing.summary = scraped["summary"]
            existing.quiz_json = json.dumps({
            "quiz": quiz_list,
            "related_topics": last_related_topics
        })
            db.commit()
            quiz_session = existing

    
    
    
    
    
    
    
    
    
    
    
    
    
    
    

    db.add(quiz_session)
    db.commit()
    db.refresh(quiz_session)

    return {
        "id": quiz_session.id,
        "url": req.url,
        "title": scraped["title"],
        "summary": scraped["summary"],
        "quiz": quiz_list,
        "related_topics": last_related_topics
    }

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
