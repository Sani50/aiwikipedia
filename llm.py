import json
import os
import re
from langchain_groq import ChatGroq

# ✅ LOAD API KEY SAFELY
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY not set")

llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model="llama-3.1-8b-instant",
    temperature=0.4,
    timeout=30,          # ✅ HARD TIMEOUT
    max_retries=2        # ✅ RETRY ON TRANSIENT FAILURES
)

def _extract_json(text: str) -> dict:
    """
    Extract first valid JSON object from model output.
    Raises ValueError if invalid.
    """
    # Remove markdown fences if present
    text = text.replace("```json", "").replace("```", "").strip()

    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("No JSON object found in LLM output")

    return json.loads(match.group())

def generate_quiz(content: str, num_questions: int):
    if not content or num_questions <= 0:
        raise ValueError("Invalid content or question count")

    prompt = f"""
You are an expert educator.

Using ONLY the Wikipedia text below, generate EXACTLY {num_questions}
high-quality multiple-choice questions.

TEXT:
\"\"\"{content[:4000]}\"\"\" 

Rules:
- Use ONLY the given text
- No extra commentary
- Output VALID JSON only

Return this exact schema:

{{
  "quiz": [
    {{
      "question": "",
      "options": ["A","B","C","D"],
      "answer": "",
      "difficulty": "easy | medium | hard",
      "explanation": ""
    }}
  ],
  "related_topics": []
}}
"""

    try:
        response = llm.invoke(prompt)
        raw_text = response.content.strip()

        data = _extract_json(raw_text)

        quiz = data.get("quiz", [])
        related_topics = data.get("related_topics", [])

        if not isinstance(quiz, list):
            raise ValueError("Quiz is not a list")

        return {
            "quiz": quiz[:num_questions],
            "related_topics": related_topics if isinstance(related_topics, list) else []
        }

    except Exception as e:
        # ✅ LOG HARD FAILURE
        print("LLM FAILURE:", str(e), flush=True)

        # ✅ FAIL FAST, NOT SILENTLY
        raise RuntimeError("Quiz generation failed")
