"""
Query router and entity extraction layer for Gym AI.
Categorizes queries, extracts specific database entities, performs conversational
contextualization, and parses target portions/gram weights.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from gym_ai.llm import generate_answer

logger = logging.getLogger("gym_ai.router")

ROUTER_PROMPT = """
You are a query router for a Gym AI system.

Classify the user's query into exactly one of these categories:

- general
  Use this when the user is asking a conversational question such as:
  greetings, asking who you are, what you can do, thanking you,
  ASKING ABOUT THEMSELVES OR THEIR PROFILE (e.g. "Who am I?", "What is my name?",
  "What is my weight?", "How tall am I?", "What are my injuries?", "What is my goal?",
  "What's my BMI?", "Tell me about my profile/stats", "What do you know about me?"),
  or asking general gym/fitness coaching advice that does not require
  looking up specific data or documents.

- database
  Use this when the user needs structured data such as:
  food nutrition, calories, protein, carbs, fat,
  exercise information, muscles, or equipment.

- rag
  Use this when the user needs knowledge from the unstructured
  gym documents, such as injury advice, exercise modification,
  recovery, hydration, sleep, or sports nutrition guidance.

- both
  Use this when the query clearly needs both structured database
  data and unstructured document knowledge.

- out_of_scope
  Use this when the user's query is OUTSIDE of gym training, fitness, workouts,
  bodybuilding, muscle anatomy, sports nutrition, hydration, recovery, rehabilitation,
  or the user's own athlete profile.
  CRITICAL EXCEPTION: Questions where the athlete asks about THEMSELVES (their identity,
  name, weight, height, injuries, goals, BMI, biometrics, profile, or stats) are 100% IN-SCOPE
  and MUST be classified as "general", NEVER "out_of_scope".
  Examples of out_of_scope: computer programming/code, math problems, general history, politics,
  movies, pop culture, automotive, non-fitness trivia, or creative writing.

Return your answer strictly in JSON format matching this schema:
{{"route": "category"}}

User query:
{query}
"""

CLASSIFY_ENTITY_PROMPT = """
You are a database entity classifier for a Gym AI system.

Classify the PRIMARY entity mentioned in the user's query.

Available entity types:
- food
- exercise
- muscle
- equipment

Important rules:
- Choose the primary entity the user is asking about.
- If the query mentions an exercise and asks about its muscles, choose "exercise".
- If the query mentions an exercise and asks about equipment used for it, choose "exercise".
- If the query asks directly about a muscle itself, choose "muscle".
- If the query asks directly about equipment itself, choose "equipment".
- If the query asks about food or nutrition, choose "food".

Return your answer strictly in JSON format matching this schema:
{{"entity_type": "type"}}

User query:
{query}
"""

EXTRACT_ENTITY_PROMPT = """
You extract the primary database entity from a user's Gym AI query.

The database contains:
- food (e.g. "chicken breast", "salmon", "egg", "apple")
- exercise (e.g. "bench press", "squat", "deadlift", "pull up")
- muscle (e.g. "biceps", "chest", "latissimus dorsi")
- equipment (e.g. "barbell", "dumbbell", "kettlebell")

Rules:
- Return ONLY the exact entity name (strip portion sizes like '200g').
- Do NOT return pronouns such as "it", "that", "this", or "them".
- Return your answer strictly in JSON format matching this schema:
{{"entity": "entity name"}}

Examples:
"How much protein is in 200g of chicken breast?" -> {{"entity": "chicken breast"}}
"What muscle does bench press target and what should I avoid with shoulder pain?" -> {{"entity": "bench press"}}
"What equipment is used for barbell squat?" -> {{"entity": "barbell squat"}}
"What muscles does chest refer to?" -> {{"entity": "chest"}}

User query:
{query}
"""

CONTEXTUALIZE_SYSTEM_PROMPT = """
You are a conversation contextualizer for Gym AI.
Your task is to take the recent chat history and the user's latest query, and produce a standalone query that fully captures the user's intent.

Rules:
1. If the user's query references earlier conversation (e.g. using pronouns like "it", "that", "those", "which one", or follow-ups like "What about chicken?", "How much protein?", "Is that safe?", "Give me another exercise"), rewrite it into a clear, complete, self-contained standalone question.
2. If the user's query is ALREADY standalone and clear (e.g. "How many calories in an apple?", "Who are you?", "What is hypertrophy?"), return it EXACTLY as-is.
3. If the user's query is a simple greeting, sign-off, or conversational remark (e.g. "hello", "hi", "thanks", "exit"), return it EXACTLY as-is.
4. Do NOT answer the question. Only output the rewritten standalone query.
5. Do NOT add any quotes, markdown formatting, or introductory words.
"""


def extract_portion_grams(query: str) -> Optional[float]:
    """
    Deterministic gram-based portion extraction from user queries.
    Recognizes patterns like '200g', '200 g', '200 grams', '0.5kg', '1 kg'.
    """
    q = query.lower()

    # Pattern 1: Kilograms, e.g., '0.5kg', '1.5 kg', '2 kilos'
    kg_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:kg|kilos?|kilograms?)", q)
    if kg_match:
        try:
            return float(kg_match.group(1)) * 1000.0
        except ValueError:
            pass

    # Pattern 2: Grams, e.g., '200g', '150 g', '350 grams'
    g_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:g|grams?)\b", q)
    if g_match:
        try:
            return float(g_match.group(1))
        except ValueError:
            pass

    return None


def parse_biometric_updates(query: str) -> Dict[str, float]:
    """
    Detect and extract height (cm) and weight (kg) if the athlete mentions them in chat.
    e.g., 'My weight is 75kg and height is 180cm', 'I weigh 80 kg', 'Update height to 175 cm'.
    """
    updates: Dict[str, float] = {}
    q = query.lower()

    # Weight pattern: '75kg', '75 kg', 'weigh 80 kg', 'weight: 80'
    w_match = re.search(r"(?:weigh|weight|wt)?\s*(?:is|:)?\s*(\d+(?:\.\d+)?)\s*(?:kg|kilos?|kilograms?)\b", q)
    if w_match:
        try:
            val = float(w_match.group(1))
            if 30.0 <= val <= 300.0:
                updates["weight_kg"] = val
        except ValueError:
            pass

    # Height pattern: '175cm', '175 cm', 'height: 180', 'tall: 180 cm'
    h_match = re.search(r"(?:tall|height|ht)?\s*(?:is|:)?\s*(\d+(?:\.\d+)?)\s*(?:cm|centimeters?)\b", q)
    if h_match:
        try:
            val = float(h_match.group(1))
            if 100.0 <= val <= 250.0:
                updates["height_cm"] = val
        except ValueError:
            pass
    else:
        # Height in meters, e.g., '1.80m', '1.75 meters'
        m_match = re.search(r"(?:tall|height|ht)?\s*(?:is|:)?\s*([12]\.\d{1,2})\s*(?:m|meters?)\b", q)
        if m_match:
            try:
                val = float(m_match.group(1)) * 100.0
                if 100.0 <= val <= 250.0:
                    updates["height_cm"] = val
            except ValueError:
                pass

    return updates


def route_query(query: str) -> str:
    """Route the query to general, database, rag, both, or out_of_scope."""
    q_lower = query.lower().strip()

    # 1. Athlete self-inquiry check (ALWAYS in-scope -> general)
    self_inquiry_patterns = [
        r"\bwho am i\b",
        r"\bwho('s| is) (the user|the athlete|logged in|my coach)\b",
        r"\b(tell me|what do you know|do you know)\s+(about\s+)?(me|myself|my profile|my stats|my info|my biometrics)\b",
        r"\b(what('s| is| are)|tell me|do you know)\s+(my\s+)?(name|weight|height|tall|bmi|bmr|injur(?:y|ies)|goal|goals|profile|stats|metrics|diet|routine)\b",
        r"\b(how tall am i|how much do i weigh|what is my weight|what is my height)\b",
        r"\bmy (profile|biometrics|stats|injuries|workout history|fitness goal|bmi|bmr|weight|height)\b",
        r"\bam i (overweight|underweight|obese|healthy|normal weight|fit)\b",
    ]
    for pattern in self_inquiry_patterns:
        if re.search(pattern, q_lower):
            return "general"

    # 2. Fast heuristic check for obvious off-topic queries
    off_topic_patterns = [
        r"\b(write|generate|create)\s+(a\s+)?(python|javascript|code|script|program|html|css|sql|function|algorithm)\b",
        r"\b(who was|capital of|president of|prime minister of)\b",
        r"\bwho is\s+(the\s+)?(president|prime minister|governor|king|queen|ceo|founder|actor|actress|singer|director)\b",
        r"\b(solve|calculate)\s+(the\s+equation|\d+\s*[\+\-\*\/]\s*\d+)",
        r"\b(movie|cinema|netflix|actor|actress|album|song lyrics)\b",
    ]
    for pattern in off_topic_patterns:
        if re.search(pattern, q_lower):
            return "out_of_scope"

    prompt = ROUTER_PROMPT.format(query=query)
    result = generate_answer(prompt, json_mode=True)

    try:
        parsed = json.loads(result)
        route = parsed.get("route", "").strip().lower()
    except Exception:
        route = "general"

    if route not in {"general", "database", "rag", "both", "out_of_scope"}:
        return "general"

    return route


def classify_database_entity(query: str) -> str:
    """Determine whether entity is food, exercise, muscle, or equipment."""
    prompt = CLASSIFY_ENTITY_PROMPT.format(query=query)
    result = generate_answer(prompt, json_mode=True)

    try:
        parsed = json.loads(result)
        entity_type = parsed.get("entity_type", "").strip().lower()
    except Exception:
        entity_type = "food"

    if entity_type not in {"food", "exercise", "muscle", "equipment"}:
        return "food"

    return entity_type


def extract_database_entity(query: str) -> str:
    """Extract the specific entity name to query from vector index or DB."""
    prompt = EXTRACT_ENTITY_PROMPT.format(query=query)
    result = generate_answer(prompt, json_mode=True)

    try:
        parsed = json.loads(result)
        extracted = parsed.get("entity", "").strip()
        if extracted:
            return extracted
    except Exception:
        pass

    # Fallback: basic cleanup
    cleaned = re.sub(r"(how much|what is|tell me about|calories in|protein in|\b\d+\s*g\b)", "", query, flags=re.IGNORECASE)
    return cleaned.strip() or query.strip()


def contextualize_query(query: str, chat_history: Optional[List[Dict[str, Any]]] = None) -> str:
    """
    Resolve follow-up references and pronouns from chat history to produce
    a standalone query for downstream retrieval and routing.
    """
    if not chat_history:
        return query

    stripped = query.strip()
    lower_query = stripped.lower()

    quick_greetings = {
        "hi", "hello", "hey", "who are you", "what can you do",
        "help", "thanks", "thank you", "bye", "goodbye", "exit", "quit"
    }
    if lower_query in quick_greetings:
        return stripped

    recent_history = chat_history[-4:]
    history_lines = []
    for msg in recent_history:
        role = "User" if msg.get("role") == "user" else "Coach"
        content = str(msg.get("content", "")).strip()
        if len(content) > 300:
            content = content[:300] + "..."
        history_lines.append(f"{role}: {content}")

    history_text = "\n".join(history_lines)
    prompt = f"""Recent Conversation:
{history_text}

User's Latest Query:
{stripped}

Standalone Query:"""

    try:
        standalone = generate_answer(
            prompt=prompt,
            system_prompt=CONTEXTUALIZE_SYSTEM_PROMPT,
            stream=False,
        )
        cleaned = standalone.strip().strip('"').strip("'")
        if cleaned:
            return cleaned
    except Exception:
        pass

    return query
