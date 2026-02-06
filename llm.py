
import json
import re
from langchain_groq import ChatGroq

llm = ChatGroq(
    api_key="key",
    model="llama-3.1-8b-instant"
,
    temperature=0.4
)

def generate_quiz(content: str, num_questions: int):
    prompt = f"""
You are an expert educator.

Using ONLY the Wikipedia text below, generate EXACTLY {num_questions}
high-quality multiple-choice questions.

TEXT:
\"\"\"{content[:4000]}\"\"\"

Each question must include:
- question
- four options
- correct answer
- difficulty (easy, medium, hard)
- short explanation

Also suggest related topics.

Return ONLY valid JSON in this format:

{{
  "quiz": [
    {{
      "question": "",
      "options": ["A","B","C","D"],
      "answer": "",
      "difficulty": "",
      "explanation": ""
    }}
  ],
  "related_topics": []
}}
"""

    try:
        response = llm.invoke(prompt)
        text = response.content.strip()

        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return {"quiz": [], "related_topics": []}

        data = json.loads(match.group())
        return {
            "quiz": data.get("quiz", [])[:num_questions],
            "related_topics": data.get("related_topics", [])
        }

    except Exception as e:
        print("LLM ERROR:", e)
        return {
            "quiz": [],
            "related_topics": []
        }
