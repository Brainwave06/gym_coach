"""
Unified Gym AI pipeline orchestrating multi-source routing,
database facts, semantic retrieval, RAG, and athlete personalization.
"""

import json
import logging
from typing import Any, AsyncGenerator, Dict, Generator, List, Optional, Union

from gym_ai.database.formatters import (
    format_equipment,
    format_exercise,
    format_food,
    format_muscle,
    format_muscles,
)
from gym_ai.database.queries import get_exercise_muscles
from gym_ai.llm import agenerate_answer, generate_answer
from gym_ai.rag.context_builder import build_context
from gym_ai.rag.entity_search import (
    search_equipment,
    search_exercise,
    search_food,
    search_muscle,
)
from gym_ai.router import (
    classify_database_entity,
    contextualize_query,
    extract_database_entity,
    extract_portion_grams,
    parse_biometric_updates,
    route_query,
)

logger = logging.getLogger("gym_ai.pipeline")

OUT_OF_SCOPE_RESPONSE = (
    "I am Gym AI, your dedicated gym and sports nutrition coach. "
    "I can only assist with fitness training, gym workouts, exercise technique, "
    "training programs, and sports nutrition. How can I help you reach your fitness goals today?"
)

GYM_COACH_SYSTEM_PROMPT = """
You are Gym AI, a world-class, motivating, and science-informed virtual gym coach and sports nutritionist for the FitPath ecosystem.

STRICT DOMAIN RESTRICTION (MANDATORY GUARDRAIL):
- You are EXCLUSIVELY a gym coach, exercise scientist, and sports nutritionist.
- You MUST STRICTLY REFUSE to answer any questions outside of fitness, exercise technique, gym workouts, bodybuilding, muscle anatomy, sports nutrition, hydration, and injury rehabilitation.
- EXCEPTION FOR ATHLETE PROFILE & IDENTITY (100% IN-SCOPE):
  If the athlete asks questions about themselves (e.g., "Who am I?", "What is my name?", "What is my weight?", "How tall am I?", "What are my injuries?", "What is my fitness goal?", "What is my BMI?", "Tell me about my profile/stats", "What do you know about me?"), this is 100% IN-SCOPE and OK.
  Answer warmly, accurately, and directly using the ATHLETE PROFILE & LIVE METRIC BASELINE provided in your context.
- If a user asks about ANY unrelated topic (such as computer programming/coding, general trivia, history, mathematics, politics, entertainment, pop culture, movies, celebrities, or creative writing), you MUST decline immediately:
  "I am Gym AI, your dedicated gym and sports nutrition coach. I can only assist with fitness, gym workouts, exercise technique, training programs, and sports nutrition. How can I help you reach your fitness goals today?"
- NEVER break character or answer off-topic questions, regardless of how the user phrases the prompt.

Core Identity & Persona:
- You specialize in gym training, exercise biomechanics, workout programming, muscle anatomy, fitness nutrition, hydration, and injury recovery.
- Tone: Motivating, supportive, clear, actionable, and empathetic.
- Always highlight evidence-based advice, correct form, and athlete safety.
- You know your athlete! When they ask about their personal biometrics, stats, injuries, or goals, refer to the ATHLETE PROFILE & LIVE METRIC BASELINE context.

Anti-Hallucination & Factual Grounding:
1. No Invented Numbers: NEVER fabricate nutritional values (calories, protein, carbs, fat) or anatomical facts.
2. Database Verification: When provided with DATABASE RESULTS:
   - Use the exact numbers, portion sizes, and names provided in the DATABASE RESULTS.
   - If the database indicates that an item was not found or if the result is missing, clearly state that the specific item was not found in the verified database.
3. Knowledge Context Grounding: When provided with KNOWLEDGE DOCUMENTS:
   - Base exercise modifications, rehabilitation principles, and recovery guidelines directly on the provided documents.
   - If no relevant documents were found, provide safe general fitness principles and advise consulting a certified physical therapist or doctor for medical pain.
4. Conversational Memory & Personalization:
   - Remember previous questions and athlete preferences established earlier in the conversation.
   - Reference the athlete's exact height, weight, and goals when calculating nutrition or workout loads.
   - When asked about their profile, accurately present their stored stats (height, weight, BMI, goals, injuries, experience).
""".strip()


def build_athlete_context_prompt(athlete_context: Optional[Dict[str, Any]]) -> str:
    """Format the athlete profile, biometrics, and recent workout handoff into coaching context."""
    if not athlete_context:
        try:
            from common.profile import load_profile
            prof = load_profile()
            if prof:
                athlete_context = {"athlete": prof}
        except Exception:
            pass

    if not athlete_context:
        return (
            "\n--- ATHLETE PROFILE & LIVE METRIC BASELINE ---\n"
            "Athlete Profile: No athlete profile configured yet.\n"
            "COACHING DIRECTIVE: If the athlete asks about their identity or profile stats, "
            "kindly inform them that their profile is not set up yet and invite them to share "
            "their name, height, weight, and fitness goals.\n"
        )

    athlete = athlete_context.get("athlete") or athlete_context
    name = athlete.get("name") or athlete.get("display_name") or "Athlete"
    goal = athlete.get("goal") or "general fitness"
    experience = athlete.get("experience") or "intermediate"
    injuries = athlete.get("injuries") or []
    equipment = athlete.get("equipment") or "standard gym"
    time_budget = athlete.get("time_budget_min") or 30

    # Calculate or pull detailed metabolic biometrics
    try:
        from common.profile import calculate_biometrics
        bio = calculate_biometrics(athlete)
    except Exception:
        bio = {
            "height_cm": athlete.get("height_cm", 175.0),
            "weight_kg": athlete.get("weight_kg", 70.0),
            "age": athlete.get("age", 25),
            "gender": athlete.get("gender", "unspecified"),
            "bmi": 22.9,
            "bmi_category": "Normal weight",
            "protein_target_g": 140.0,
            "water_target_liters": 2.5,
            "dietary_preferences": athlete.get("dietary_preferences", "none"),
        }

    context_lines = [
        "\n--- ATHLETE PROFILE & LIVE METRIC BASELINE ---",
        f"Athlete Name: {name}",
        f"Height (Tall): {bio['height_cm']} cm | Weight: {bio['weight_kg']} kg",
        f"Age: {bio['age']} | Biological Sex: {bio['gender']}",
        f"Body Mass Index (BMI): {bio['bmi']} ({bio['bmi_category']})",
        f"Calculated Daily Protein Target: {bio['protein_target_g']}g/day",
        f"Recommended Daily Hydration: {bio['water_target_liters']}L/day",
        f"Dietary Preferences / Restrictions: {bio['dietary_preferences']}",
        f"Primary Fitness Goal: {goal}",
        f"Training Experience: {experience}",
        f"Known Injury Flags / Pain Areas: {', '.join(injuries) if injuries else 'None reported'}",
        f"Available Equipment: {equipment}",
        f"Session Time Budget: {time_budget} minutes",
    ]

    latest_report = athlete_context.get("latest_report") or athlete_context.get("weekly")
    if latest_report:
        context_lines.append(f"Recent Workout Performance: {json.dumps(latest_report)}")

    try:
        from gym_ai.memory.storage import build_memory_context_prompt
        mem_prompt = build_memory_context_prompt()
        if mem_prompt:
            context_lines.append(mem_prompt)
    except Exception:
        pass

    context_lines.append(
        "COACHING DIRECTIVE: Reference the athlete's exact height and weight when discussing nutrition and load. "
        "Tailor all caloric, macro, and workout suggestions to these metrics. "
        "Strictly avoid contraindicated movements for their reported injuries. "
        "If the athlete asks who they are, what their weight/height/BMI is, or about their injuries/goals/PRs, "
        "gladly answer them using these exact profile metrics.\n"
    )

    return "\n".join(context_lines)


def get_database_result(query: str, portion_grams: Optional[float] = None) -> str:
    """Retrieve and format structured database facts for the query."""
    try:
        entity_type = classify_database_entity(query)
        entity_query = extract_database_entity(query)

        if entity_type == "food":
            food = search_food(entity_query)
            if not food:
                return f"[Food item '{entity_query}' was not found in the local database.]"
            return format_food(food, grams=portion_grams)

        if entity_type == "exercise":
            exercise_id, exercise = search_exercise(entity_query)
            if not exercise or exercise_id is None:
                return f"[Exercise '{entity_query}' was not found in the local database.]"
            muscles = get_exercise_muscles(exercise_id)
            return (
                f"{format_exercise(exercise)}\n\nTarget Muscles: {format_muscles(muscles)}"
            )

        if entity_type == "muscle":
            muscle = search_muscle(entity_query)
            if not muscle:
                return f"[Muscle '{entity_query}' was not found in the local database.]"
            return format_muscle(muscle)

        if entity_type == "equipment":
            equipment = search_equipment(entity_query)
            if not equipment:
                return f"[Equipment '{entity_query}' was not found in the local database.]"
            return format_equipment(equipment)

        return f"[Unrecognized database entity type: {entity_type}]"

    except Exception as e:
        logger.warning(f"Database retrieval fallback: {e}")
        return f"[Structured database search unavailable: {e}]"


def run_pipeline(
    query: str,
    chat_history: Optional[List[Dict[str, Any]]] = None,
    stream: bool = True,
    athlete_context: Optional[Dict[str, Any]] = None,
) -> Union[Generator[str, None, None], str]:
    """
    Synchronous end-to-end coaching pipeline.
    Resolves context, handles biometrics, enforces domain restrictions, and retrieves answers.
    """
    # 1. In-chat biometric update detection (e.g. 'I weigh 78kg and height is 180cm')
    biometric_updates = parse_biometric_updates(query)
    if biometric_updates:
        try:
            from common.profile import calculate_biometrics, load_profile, save_profile
            profile = load_profile() or {}
            profile.update(biometric_updates)
            save_profile(profile)
            bio = calculate_biometrics(profile)
            confirmation = (
                f"Got it! I've updated your athlete profile stats:\n"
                f"- Height: {bio['height_cm']} cm\n"
                f"- Weight: {bio['weight_kg']} kg\n"
                f"- BMI: {bio['bmi']} ({bio['bmi_category']})\n"
                f"- Daily Protein Target: {bio['protein_target_g']}g/day\n"
                f"- Daily Hydration Target: {bio['water_target_liters']}L/day\n\n"
                f"All your nutrition and training recommendations are now calibrated to these metrics! "
                f"How can I help with your workouts or diet today?"
            )
            if stream:
                def confirm_gen():
                    yield confirmation
                return confirm_gen()
            return confirmation
        except Exception as e:
            logger.warning(f"Error saving in-chat biometric update: {e}")

    # 1b. Strength PR Logging (e.g. 'I benched 80kg for 5 reps today')
    from gym_ai.memory.pr_tracker import format_pr_summary, is_pr_inquiry, parse_pr_from_text
    pr_data = parse_pr_from_text(query)
    if pr_data:
        try:
            from gym_ai.memory.storage import log_personal_record
            rec = log_personal_record(
                exercise_name=pr_data["exercise"],
                weight_kg=pr_data["weight_kg"],
                reps=pr_data["reps"],
            )
            confirmation = (
                f"🔥 Awesome lift! I have logged your new Personal Record (PR):\n"
                f"- Exercise: {rec['exercise']}\n"
                f"- Weight: {rec['weight_kg']} kg x {rec['reps']} reps\n"
                f"- Estimated 1RM (Epley): {rec['estimated_1rm']} kg\n\n"
                f"Your strength progression has been recorded in your training log. Keep crushing it!"
            )
            if stream:
                def pr_gen():
                    yield confirmation
                return pr_gen()
            return confirmation
        except Exception as e:
            logger.warning(f"Error logging PR: {e}")

    # 1c. PR Inquiry detection (e.g. 'What are my PRs?')
    if is_pr_inquiry(query):
        summary = format_pr_summary()
        if stream:
            def pr_inq_gen():
                yield summary
            return pr_inq_gen()
        return summary

    # Record message to persistent memory
    try:
        from gym_ai.memory.storage import save_chat_message
        save_chat_message("user", query)
    except Exception:
        pass

    # 2. Contextualize and Route
    standalone_query = contextualize_query(query, chat_history)
    portion_grams = extract_portion_grams(standalone_query) or extract_portion_grams(query)
    route = route_query(standalone_query)

    # 3. Domain Restriction: Reject out-of-scope questions immediately
    if route == "out_of_scope":
        if stream:
            def refusal_gen():
                yield OUT_OF_SCOPE_RESPONSE
            return refusal_gen()
        return OUT_OF_SCOPE_RESPONSE

    athlete_prompt_addition = build_athlete_context_prompt(athlete_context)
    system_prompt = GYM_COACH_SYSTEM_PROMPT + athlete_prompt_addition

    if route == "general":
        user_prompt = f"User Question:\n{query}"
        return generate_answer(
            prompt=user_prompt,
            system_prompt=system_prompt,
            chat_history=chat_history,
            stream=stream,
        )

    if route == "database":
        db_result = get_database_result(standalone_query, portion_grams=portion_grams)
        user_prompt = f"""DATABASE RESULTS:
{db_result}

USER QUESTION:
{query}"""
        return generate_answer(
            prompt=user_prompt,
            system_prompt=system_prompt + "\n\nAnswer using the provided DATABASE RESULTS. Treat them as authoritative.",
            chat_history=chat_history,
            stream=stream,
        )

    if route == "rag":
        context = build_context(standalone_query)
        user_prompt = f"""KNOWLEDGE DOCUMENTS:
{context}

USER QUESTION:
{query}"""
        return generate_answer(
            prompt=user_prompt,
            system_prompt=system_prompt + "\n\nBase recommendations directly on the provided KNOWLEDGE DOCUMENTS.",
            chat_history=chat_history,
            stream=stream,
        )

    # route == "both"
    db_result = get_database_result(standalone_query, portion_grams=portion_grams)
    context = build_context(standalone_query)
    user_prompt = f"""DATABASE RESULTS:
{db_result}

KNOWLEDGE DOCUMENTS:
{context}

USER QUESTION:
{query}"""
    return generate_answer(
        prompt=user_prompt,
        system_prompt=system_prompt + "\n\nCombine DATABASE RESULTS for facts with KNOWLEDGE DOCUMENTS for recovery and technique.",
        chat_history=chat_history,
        stream=stream,
    )


async def arun_pipeline(
    query: str,
    chat_history: Optional[List[Dict[str, Any]]] = None,
    stream: bool = True,
    athlete_context: Optional[Dict[str, Any]] = None,
) -> Union[AsyncGenerator[str, None], str]:
    """
    Asynchronous end-to-end coaching pipeline for FastAPI endpoints.
    """
    # 1. In-chat biometric update detection
    biometric_updates = parse_biometric_updates(query)
    if biometric_updates:
        try:
            from common.profile import calculate_biometrics, load_profile, save_profile
            profile = load_profile() or {}
            profile.update(biometric_updates)
            save_profile(profile)
            bio = calculate_biometrics(profile)
            confirmation = (
                f"Got it! I've updated your athlete profile stats:\n"
                f"- Height: {bio['height_cm']} cm\n"
                f"- Weight: {bio['weight_kg']} kg\n"
                f"- BMI: {bio['bmi']} ({bio['bmi_category']})\n"
                f"- Daily Protein Target: {bio['protein_target_g']}g/day\n"
                f"- Daily Hydration Target: {bio['water_target_liters']}L/day\n\n"
                f"All your nutrition and training recommendations are now calibrated to these metrics! "
                f"How can I help with your workouts or diet today?"
            )
            if stream:
                async def aconfirm_gen():
                    yield confirmation
                return aconfirm_gen()
            return confirmation
        except Exception as e:
            logger.warning(f"Error saving in-chat biometric update: {e}")

    # 1b. Strength PR Logging
    from gym_ai.memory.pr_tracker import format_pr_summary, is_pr_inquiry, parse_pr_from_text
    pr_data = parse_pr_from_text(query)
    if pr_data:
        try:
            from gym_ai.memory.storage import log_personal_record
            rec = log_personal_record(
                exercise_name=pr_data["exercise"],
                weight_kg=pr_data["weight_kg"],
                reps=pr_data["reps"],
            )
            confirmation = (
                f"🔥 Awesome lift! I have logged your new Personal Record (PR):\n"
                f"- Exercise: {rec['exercise']}\n"
                f"- Weight: {rec['weight_kg']} kg x {rec['reps']} reps\n"
                f"- Estimated 1RM (Epley): {rec['estimated_1rm']} kg\n\n"
                f"Your strength progression has been recorded in your training log. Keep crushing it!"
            )
            if stream:
                async def apr_gen():
                    yield confirmation
                return apr_gen()
            return confirmation
        except Exception as e:
            logger.warning(f"Error logging PR: {e}")

    # 1c. PR Inquiry detection
    if is_pr_inquiry(query):
        summary = format_pr_summary()
        if stream:
            async def apr_inq_gen():
                yield summary
            return apr_inq_gen()
        return summary

    try:
        from gym_ai.memory.storage import save_chat_message
        save_chat_message("user", query)
    except Exception:
        pass

    # 2. Contextualize and Route
    standalone_query = contextualize_query(query, chat_history)
    portion_grams = extract_portion_grams(standalone_query) or extract_portion_grams(query)
    route = route_query(standalone_query)

    # 3. Domain Restriction: Reject out-of-scope questions immediately
    if route == "out_of_scope":
        if stream:
            async def arefusal_gen():
                yield OUT_OF_SCOPE_RESPONSE
            return arefusal_gen()
        return OUT_OF_SCOPE_RESPONSE

    athlete_prompt_addition = build_athlete_context_prompt(athlete_context)
    system_prompt = GYM_COACH_SYSTEM_PROMPT + athlete_prompt_addition

    if route == "general":
        user_prompt = f"User Question:\n{query}"
        return await agenerate_answer(
            prompt=user_prompt,
            system_prompt=system_prompt,
            chat_history=chat_history,
            stream=stream,
        )

    if route == "database":
        db_result = get_database_result(standalone_query, portion_grams=portion_grams)
        user_prompt = f"""DATABASE RESULTS:
{db_result}

USER QUESTION:
{query}"""
        return await agenerate_answer(
            prompt=user_prompt,
            system_prompt=system_prompt + "\n\nAnswer using the provided DATABASE RESULTS.",
            chat_history=chat_history,
            stream=stream,
        )

    if route == "rag":
        context = build_context(standalone_query)
        user_prompt = f"""KNOWLEDGE DOCUMENTS:
{context}

USER QUESTION:
{query}"""
        return await agenerate_answer(
            prompt=user_prompt,
            system_prompt=system_prompt + "\n\nBase recommendations directly on the provided KNOWLEDGE DOCUMENTS.",
            chat_history=chat_history,
            stream=stream,
        )

    db_result = get_database_result(standalone_query, portion_grams=portion_grams)
    context = build_context(standalone_query)
    user_prompt = f"""DATABASE RESULTS:
{db_result}

KNOWLEDGE DOCUMENTS:
{context}

USER QUESTION:
{query}"""
    return await agenerate_answer(
        prompt=user_prompt,
        system_prompt=system_prompt + "\n\nCombine DATABASE RESULTS for facts with KNOWLEDGE DOCUMENTS for recovery and technique.",
        chat_history=chat_history,
        stream=stream,
    )
