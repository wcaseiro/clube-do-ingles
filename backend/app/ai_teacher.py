import os
import json
from typing import Any
from dotenv import load_dotenv

load_dotenv()

SAFE_TEACHER_PROMPT = """
Você é a Luma, uma robô professora de inglês para crianças e adolescentes brasileiros.

Objetivo:
- Treinar conversação em inglês nível A1/A2.
- Fazer perguntas curtas.
- Corrigir com carinho.
- Manter a criança motivada.
- Responder com frases curtas, boas para voz.

Regras de segurança:
- Não peça sobrenome, telefone, endereço, escola, redes sociais, cidade exata ou localização.
- Não converse sobre temas adultos, violentos, políticos, religiosos, médicos ou inadequados.
- Se o aluno sair do tema, redirecione gentilmente para inglês básico.
- Não faça perguntas pessoais sensíveis.
- Use temas seguros: apresentação, idade, país, comida, escola, família, animais, hobbies, viagem, rotina.

Regras pedagógicas:
- Uma pergunta por vez.
- Use inglês simples.
- Explique em português apenas quando for útil.
- Quando houver erro, mostre uma forma melhor, sem humilhar.
- A resposta deve ser curta o suficiente para ser falada rapidamente.
- Nunca gere textos longos.
- Nunca use markdown.

Formato obrigatório:
Responda SOMENTE JSON válido com:
{
  "feedback": "comentário curto e motivador",
  "correction": "forma melhor da frase do aluno ou null",
  "explanation_pt": "explicação curta em português",
  "next_question": "próxima pergunta simples em inglês",
  "mood": "happy|helping|excited|start",
  "topic": "name|age|country|likes|food|school|family|travel|routine|animals|hobbies"
}
""".strip()

CONVERSATION_FLOW = [
    {"topic": "name", "question": "What is your name?", "hint": "Responda: My name is..."},
    {"topic": "age", "question": "How old are you?", "hint": "Responda: I am twelve years old."},
    {"topic": "country", "question": "Where are you from?", "hint": "Responda: I am from Brazil."},
    {"topic": "likes", "question": "What do you like?", "hint": "Responda: I like music."},
    {"topic": "food", "question": "What is your favorite food?", "hint": "Responda: My favorite food is pizza."},
    {"topic": "school", "question": "Do you like school?", "hint": "Responda: Yes, I like school."},
    {"topic": "family", "question": "Tell me about your family.", "hint": "Responda: This is my family."},
    {"topic": "travel", "question": "Can you say one travel phrase?", "hint": "Responda: I need help. / Where is the bathroom?"},
]


def _topic_for_turn(turn_index: int) -> dict:
    return CONVERSATION_FLOW[max(0, turn_index) % len(CONVERSATION_FLOW)]


def _safe_json(data: dict[str, Any], fallback_question: str) -> dict[str, Any]:
    correction = data.get("correction")

    if correction in ("", "null", "None"):
        correction = None

    return {
        "feedback": str(data.get("feedback") or "Great job! Let's continue.")[:300],
        "correction": correction,
        "explanation_pt": str(data.get("explanation_pt") or "Continue com uma frase curta em inglês.")[:300],
        "next_question": str(data.get("next_question") or fallback_question)[:220],
        "mood": str(data.get("mood") or "happy")[:40],
        "topic": str(data.get("topic") or "conversation")[:40],
    }


def _mock_response(message: str, student_name: str = "student", turn_index: int = 0) -> dict:
    current = _topic_for_turn(turn_index)
    nxt = _topic_for_turn(turn_index + 1)
    text = (message or "").strip()
    lower = text.lower()

    if not text:
        return {
            "feedback": "Hi! I am Luma. Let’s start our English mission!",
            "correction": None,
            "explanation_pt": current["hint"],
            "next_question": current["question"],
            "mood": "start",
            "topic": current["topic"],
        }

    if "i have" in lower and "years" in lower:
        return {
            "feedback": "Great try! I understood you.",
            "correction": text.replace("I have", "I am").replace("i have", "I am"),
            "explanation_pt": "Para falar idade em inglês, usamos 'I am', não 'I have'.",
            "next_question": "Can you try again? Say: I am twelve years old.",
            "mood": "helping",
            "topic": "age",
        }

    return {
        "feedback": "Great job! I liked your answer!",
        "correction": None,
        "explanation_pt": "Muito bem! Vamos continuar com frases curtas.",
        "next_question": nxt["question"],
        "mood": "happy",
        "topic": nxt["topic"],
    }


def _build_user_payload(
    message: str,
    student_name: str,
    lesson_title: str | None,
    turn_index: int,
    history: list[dict],
) -> dict:
    current = _topic_for_turn(turn_index)

    clean_history = []
    for item in history[-4:]:
        clean_history.append({
            "student": str(item.get("user_message") or "")[:300],
            "luma": str(item.get("ai_response") or "")[:500],
        })

    return {
        "student_name": student_name,
        "lesson_title": lesson_title,
        "turn_index": turn_index,
        "suggested_next_topic": current,
        "history": clean_history,
        "student_message": message,
        "instruction": "Responda como Luma. Seja curta. JSON válido apenas.",
    }


def _gemini_response(
    message: str,
    student_name: str,
    lesson_title: str | None,
    turn_index: int,
    history: list[dict],
) -> dict:
    from google import genai
    from google.genai import types

    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY não configurada no .env")

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite").strip()
    max_tokens = int(os.getenv("AI_MAX_OUTPUT_TOKENS", "90"))
    temperature = float(os.getenv("AI_TEMPERATURE", "0.4"))

    current = _topic_for_turn(turn_index)
    fallback_question = current["question"]

    client = genai.Client(api_key=api_key)

    payload = _build_user_payload(
        message=message,
        student_name=student_name,
        lesson_title=lesson_title,
        turn_index=turn_index,
        history=history,
    )

    prompt = SAFE_TEACHER_PROMPT + "\n\nDados da conversa:\n" + json.dumps(payload, ensure_ascii=False)

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=temperature,
            max_output_tokens=max_tokens,
        ),
    )

    raw = response.text or ""

    try:
        data = json.loads(raw)
    except Exception:
        data = {
            "feedback": raw[:180] or "Great job! Let's continue.",
            "correction": None,
            "explanation_pt": "Continue respondendo com frases curtas em inglês.",
            "next_question": fallback_question,
            "mood": "happy",
            "topic": current["topic"],
        }

    return _safe_json(data, fallback_question=fallback_question)


def _openai_response(
    message: str,
    student_name: str,
    lesson_title: str | None,
    turn_index: int,
    history: list[dict],
) -> dict:
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY não configurada no .env")

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
    max_tokens = int(os.getenv("AI_MAX_OUTPUT_TOKENS", "90"))
    temperature = float(os.getenv("AI_TEMPERATURE", "0.4"))
    timeout_seconds = float(os.getenv("AI_TIMEOUT_SECONDS", "6"))

    current = _topic_for_turn(turn_index)
    fallback_question = current["question"]

    client = OpenAI(
        api_key=api_key,
        timeout=timeout_seconds,
    )

    messages = [
        {"role": "system", "content": SAFE_TEACHER_PROMPT}
    ]

    for item in history[-4:]:
        user_msg = item.get("user_message")
        ai_msg = item.get("ai_response")

        if user_msg:
            messages.append({
                "role": "user",
                "content": str(user_msg)[:300],
            })

        if ai_msg:
            messages.append({
                "role": "assistant",
                "content": str(ai_msg)[:500],
            })

    payload = _build_user_payload(
        message=message,
        student_name=student_name,
        lesson_title=lesson_title,
        turn_index=turn_index,
        history=[],
    )

    messages.append({
        "role": "user",
        "content": json.dumps(payload, ensure_ascii=False),
    })

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"},
        max_tokens=max_tokens,
        temperature=temperature,
    )

    raw = response.choices[0].message.content or ""

    try:
        data = json.loads(raw)
    except Exception:
        data = {
            "feedback": raw[:180] or "Great job! Let's continue.",
            "correction": None,
            "explanation_pt": "Continue respondendo com frases curtas em inglês.",
            "next_question": fallback_question,
            "mood": "happy",
            "topic": current["topic"],
        }

    return _safe_json(data, fallback_question=fallback_question)


def generate_ai_response(
    message: str,
    student_name: str = "student",
    lesson_title: str | None = None,
    turn_index: int = 0,
    history: list[dict] | None = None,
) -> dict:
    provider = os.getenv("AI_PROVIDER", "mock").lower().strip()

    if provider == "gemini":
        try:
            return _gemini_response(
                message=message,
                student_name=student_name,
                lesson_title=lesson_title,
                turn_index=turn_index,
                history=history or [],
            )
        except Exception as exc:
            print(f"[LUMA_GEMINI_ERROR] {type(exc).__name__}: {exc}", flush=True)

            result = _mock_response(
                message,
                student_name=student_name,
                turn_index=turn_index,
            )

            result["explanation_pt"] = (
                "A Luma online demorou ou falhou, então usei o modo local. "
                + result["explanation_pt"]
            )

            return result

    if provider == "openai":
        try:
            return _openai_response(
                message=message,
                student_name=student_name,
                lesson_title=lesson_title,
                turn_index=turn_index,
                history=history or [],
            )
        except Exception as exc:
            print(f"[LUMA_OPENAI_ERROR] {type(exc).__name__}: {exc}", flush=True)

            result = _mock_response(
                message,
                student_name=student_name,
                turn_index=turn_index,
            )

            result["explanation_pt"] = (
                "A Luma online demorou ou falhou, então usei o modo local. "
                + result["explanation_pt"]
            )

            return result

    return _mock_response(
        message,
        student_name=student_name,
        turn_index=turn_index,
    )
