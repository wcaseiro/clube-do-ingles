import os
import re
import json
import string
from datetime import datetime, timezone
from typing import Any
from dotenv import load_dotenv

load_dotenv()

AI_STATUS_FILE = os.getenv("AI_STATUS_FILE", "/tmp/clube-do-ingles-ai-status.json")

def _write_ai_status(provider: str, status: str, message: str = "", retry_after_seconds: int | None = None):
    try:
        payload = {
            "provider": provider,
            "status": status,
            "message": str(message or "")[:1000],
            "retry_after_seconds": retry_after_seconds,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(AI_STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
    except Exception:
        pass

def _mark_ai_ok(provider: str):
    _write_ai_status(provider, "ok", "IA respondendo normalmente.")

def _extract_retry_after_seconds(message: str) -> int | None:
    m = re.search(r"retry in ([0-9]+(?:\.[0-9]+)?)s", message or "", re.I)
    if m:
        try:
            return int(float(m.group(1)))
        except Exception:
            return None
    m = re.search(r"retryDelay['\"]?:\s*['\"]?([0-9]+)s", message or "", re.I)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    return None

def _is_quota_error(message: str) -> bool:
    low = (message or "").lower()
    return (
        "resource_exhausted" in low
        or "quota exceeded" in low
        or "generate_content_free_tier_requests" in low
        or "insufficient_quota" in low
        or "rate limit" in low
    )


SAFE_TEACHER_PROMPT = """
Você é a Luma, uma robô professora de inglês para crianças e adolescentes brasileiros.

Objetivo:
- Treinar conversação em inglês nível A1/A2.
- Fazer perguntas curtas sobre assuntos cotidianos.
- Corrigir com carinho, sem exagerar em pontuação, maiúsculas ou pequenas vírgulas.
- Manter a criança motivada.
- Responder com frases curtas, boas para voz.

Regras de segurança:
- Não peça sobrenome, telefone, endereço, escola, redes sociais, cidade exata ou localização.
- Não converse sobre temas adultos, violentos, políticos, religiosos, médicos ou inadequados.
- Se o aluno sair do tema, redirecione gentilmente para inglês básico.
- Não faça perguntas pessoais sensíveis.
- Use temas seguros: apresentação, idade, país, comida, escola, família, animais, hobbies, rotina, brincadeiras, matérias da escola, viagem.

Regras pedagógicas:
- Use o primeiro nome do aluno apenas quando iniciar conversa, mudar claramente de assunto, elogiar algo importante ou chamar atenção com carinho.
- Não comece todas as respostas com o nome do aluno.
- Uma pergunta por vez.
- Use inglês simples.
- Explique em português apenas quando for útil.
- Quando houver erro real de gramática ou sentido, mostre uma forma melhor.
- Não marque como erro apenas por letra maiúscula, vírgula, ponto final, acento ou frase sem pontuação.
- Quando o aluno perguntar "what do you mean?", "I don't understand", "não entendi" ou pedir ajuda, não avance de assunto. Explique melhor e peça para repetir.
- Não repita sempre o mesmo assunto. Olhe o histórico e escolha um tema novo.
- Se já falou sobre nome em conversas anteriores, não comece perguntando o nome de novo.
- A resposta deve ser curta.
- Nunca use markdown.

Formato obrigatório:
Responda SOMENTE JSON válido com:
{
  "feedback": "comentário curto e motivador em inglês",
  "correction": "forma melhor da frase do aluno ou null",
  "explanation_pt": "explicação curta em português",
  "next_question": "próxima pergunta simples em inglês. Use o nome do aluno só quando mudar de assunto ou quando soar natural.",
  "mood": "happy|helping|excited|start",
  "topic": "name|age|country|likes|food|school|family|travel|routine|animals|hobbies|clarification|games|subjects|friends",
  "understood": true,
  "needs_repeat": false,
  "status": "ok|correction|repeat"
}
""".strip()

CONVERSATION_FLOW = [
    {"topic": "name", "question": "What is your name?", "hint": "Responda: My name is..."},
    {"topic": "age", "question": "{name}, how old are you?", "hint": "Responda: I am twelve years old."},
    {"topic": "animals", "question": "Do you have a pet?", "hint": "Responda: Yes, I have a dog."},
    {"topic": "family", "question": "{name}, what is your brother's name?", "hint": "Responda: His name is..."},
    {"topic": "food", "question": "What is your favorite food?", "hint": "Responda: My favorite food is pizza."},
    {"topic": "school", "question": "Do you like studying English?", "hint": "Responda: Yes, I like studying English."},
    {"topic": "subjects", "question": "What is your favorite subject?", "hint": "Responda: My favorite subject is math."},
    {"topic": "games", "question": "What do you like to play?", "hint": "Responda: I like to play soccer."},
    {"topic": "hobbies", "question": "What do you like to do after school?", "hint": "Responda: I like to play games."},
    {"topic": "routine", "question": "What do you do in the morning?", "hint": "Responda: I brush my teeth."},
    {"topic": "travel", "question": "Can you say one travel phrase?", "hint": "Responda: I need help. / Where is the bathroom?"},
]

HELP_PATTERNS = [
    "what do you mean", "i dont understand", "i don't understand", "i do not understand",
    "não entendi", "nao entendi", "explique", "explain", "help", "ajuda"
]

def _student_name(name: str | None) -> str:
    name = (name or "explorer").strip().split()[0]
    return name[:40] or "explorer"

def _format_question(q: str, student_name: str) -> str:
    return q.format(name=_student_name(student_name))

def _normalize_for_minor_compare(text: str) -> str:
    text = (text or "").strip().lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"\s+", " ", text)
    return text

def _is_minor_only(original: str, correction: str | None) -> bool:
    if not correction:
        return False
    return _normalize_for_minor_compare(original) == _normalize_for_minor_compare(correction)

def _history_text(history: list[dict]) -> str:
    parts = []
    for item in history[-20:]:
        parts.append(str(item.get("user_message") or ""))
        parts.append(str(item.get("ai_response") or ""))
    return " ".join(parts).lower()

def _used_topics(history: list[dict]) -> set[str]:
    text = _history_text(history)
    topics = set()
    for t in [x["topic"] for x in CONVERSATION_FLOW]:
        if f'"topic": "{t}"' in text or f'"topic":"{t}"' in text or t in text:
            topics.add(t)
    # heuristics from questions/answers
    checks = {
        "name": ["what is your name", "my name is"],
        "age": ["how old", "years old"],
        "animals": ["pet", "dog", "cat"],
        "family": ["brother", "sister", "mother", "father", "family"],
        "food": ["favorite food", "pizza", "hamburger"],
        "school": ["school", "studying english"],
        "subjects": ["favorite subject", "math", "science"],
        "games": ["play soccer", "play with"],
        "hobbies": ["after school", "hobby"],
        "routine": ["morning", "brush my teeth"],
        "travel": ["travel phrase", "bathroom", "ticket"],
    }
    for topic, words in checks.items():
        if any(w in text for w in words):
            topics.add(topic)
    return topics

def _topic_for_turn(turn_index: int, history: list[dict] | None = None) -> dict:
    history = history or []
    used = _used_topics(history)
    # On very first time, ask name. After that, prefer new topics.
    if not history and turn_index <= 0:
        return CONVERSATION_FLOW[0]
    for item in CONVERSATION_FLOW[1:]:
        if item["topic"] not in used:
            return item
    return CONVERSATION_FLOW[max(1, turn_index) % len(CONVERSATION_FLOW)]

def _next_topic(turn_index: int, history: list[dict] | None = None) -> dict:
    return _topic_for_turn(turn_index + 1, history or [])

def _looks_like_help(message: str) -> bool:
    low = (message or "").strip().lower()
    return any(p in low for p in HELP_PATTERNS)

def _safe_json(data: dict[str, Any], fallback_question: str, original_message: str = "") -> dict[str, Any]:
    correction = data.get("correction")
    if correction in ("", "null", "None", "none"):
        correction = None
    if _is_minor_only(original_message, correction):
        correction = None
        data["status"] = "ok"
        data["understood"] = True
        data["needs_repeat"] = False
    status = str(data.get("status") or ("correction" if correction else "ok")).lower()
    needs_repeat = bool(data.get("needs_repeat") or status in ("repeat", "correction"))
    understood = bool(data.get("understood", not needs_repeat))
    return {
        "feedback": str(data.get("feedback") or "Great job! Let's continue.")[:300],
        "correction": correction,
        "explanation_pt": str(data.get("explanation_pt") or "Continue com uma frase curta em inglês.")[:360],
        "next_question": str(data.get("next_question") or fallback_question)[:240],
        "mood": str(data.get("mood") or ("helping" if needs_repeat else "happy"))[:40],
        "topic": str(data.get("topic") or "conversation")[:40],
        "status": status if status in ("ok", "correction", "repeat") else ("correction" if correction else "ok"),
        "understood": understood,
        "needs_repeat": needs_repeat,
    }

def _mock_response(message: str, student_name: str = "student", turn_index: int = 0, history: list[dict] | None = None) -> dict:
    history = history or []
    current = _topic_for_turn(turn_index, history)
    nxt = _next_topic(turn_index, history)
    text = (message or "").strip()
    lower = text.lower()
    name = _student_name(student_name)

    if not text or text == "__START_CONVERSATION__":
        q = _format_question(current["question"], name)
        if current["topic"] == "name":
            feedback = f"Hi, {name}! I am Luma. Let’s start our English mission!"
        else:
            feedback = f"Hi, {name}! Great to see you again. Let’s talk about something new!"
        return {
            "feedback": feedback,
            "correction": None,
            "explanation_pt": current["hint"],
            "next_question": q,
            "mood": "start",
            "topic": current["topic"],
            "status": "ok",
            "understood": True,
            "needs_repeat": False,
        }

    if _looks_like_help(text):
        q = _format_question(current["question"], name)
        return {
            "feedback": f"No problem, {name}. I can explain!",
            "correction": None,
            "explanation_pt": f"A Luma perguntou: '{q}'. Responda com uma frase simples. Exemplo: {current['hint']}",
            "next_question": q,
            "mood": "helping",
            "topic": "clarification",
            "status": "repeat",
            "understood": False,
            "needs_repeat": True,
        }

    if "i have" in lower and "years" in lower:
        return {
            "feedback": f"Great try, {name}! I understood you.",
            "correction": text.replace("I have", "I am").replace("i have", "I am"),
            "explanation_pt": "Para falar idade em inglês, usamos 'I am', não 'I have'.",
            "next_question": f"{name}, can you try again? Say: I am twelve years old.",
            "mood": "helping",
            "topic": "age",
            "status": "correction",
            "understood": False,
            "needs_repeat": True,
        }

    return {
        "feedback": f"Great job, {name}! I understood you.",
        "correction": None,
        "explanation_pt": "Sua frase fez sentido. Vamos continuar com outro assunto.",
        "next_question": _format_question(nxt["question"], name),
        "mood": "happy",
        "topic": nxt["topic"],
        "status": "ok",
        "understood": True,
        "needs_repeat": False,
    }

def _build_user_payload(message: str, student_name: str, lesson_title: str | None, turn_index: int, history: list[dict]) -> dict:
    current = _topic_for_turn(turn_index, history)
    name = _student_name(student_name)
    clean_history = []
    for item in history[-12:]:
        clean_history.append({
            "student": str(item.get("user_message") or "")[:320],
            "luma": str(item.get("ai_response") or "")[:700],
        })
    return {
        "student_name": name,
        "lesson_title": lesson_title,
        "turn_index": turn_index,
        "suggested_next_topic": {
            **current,
            "question": _format_question(current["question"], name),
        },
        "recent_topics_to_avoid": sorted(_used_topics(history)),
        "learning_profile_hint": "Observe o histórico: se o aluno acerta mais um tema, avance gradualmente. Se erra, faça uma pergunta mais simples no mesmo assunto. Não repita nome em toda frase.",
        "history": clean_history,
        "student_message": message,
        "is_start": message == "__START_CONVERSATION__",
        "is_help_request": _looks_like_help(message),
        "instruction": (
            "Responda como Luma. Seja curta. JSON válido apenas. "
            "Use o nome do aluno apenas se for início de conversa, mudança de contexto ou soar natural. "
            "Se is_start=true, cumprimente e faça a pergunta sugerida. "
            "Se is_help_request=true, explique melhor a última pergunta e não avance de assunto. "
            "Não corrija só por pontuação ou letra maiúscula."
        ),
    }

def _gemini_response(message: str, student_name: str, lesson_title: str | None, turn_index: int, history: list[dict]) -> dict:
    from google import genai
    from google.genai import types

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY não configurada no .env")

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite").strip()
    max_tokens = int(os.getenv("AI_MAX_OUTPUT_TOKENS", "180"))
    temperature = float(os.getenv("AI_TEMPERATURE", "0.35"))
    timeout_seconds = float(os.getenv("AI_TIMEOUT_SECONDS", "12"))

    current = _topic_for_turn(turn_index, history)
    fallback_question = _format_question(current["question"], student_name)

    client = genai.Client(api_key=api_key)
    payload = _build_user_payload(message, student_name, lesson_title, turn_index, history)
    prompt = SAFE_TEACHER_PROMPT + "\n\nDados da conversa:\n" + json.dumps(payload, ensure_ascii=False)

    # google-genai currently controls HTTP timeout internally in many environments;
    # timeout_seconds stays in env for future compatibility and fallback policy.
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
            "status": "ok",
            "understood": True,
            "needs_repeat": False,
        }
    return _safe_json(data, fallback_question=fallback_question, original_message=message)

def _openai_response(message: str, student_name: str, lesson_title: str | None, turn_index: int, history: list[dict]) -> dict:
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY não configurada no .env")

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
    max_tokens = int(os.getenv("AI_MAX_OUTPUT_TOKENS", "180"))
    temperature = float(os.getenv("AI_TEMPERATURE", "0.35"))
    timeout_seconds = float(os.getenv("AI_TIMEOUT_SECONDS", "12"))

    current = _topic_for_turn(turn_index, history)
    fallback_question = _format_question(current["question"], student_name)
    client = OpenAI(api_key=api_key, timeout=timeout_seconds)

    payload = _build_user_payload(message, student_name, lesson_title, turn_index, history)
    messages = [{"role": "system", "content": SAFE_TEACHER_PROMPT}]
    messages.append({"role": "user", "content": json.dumps(payload, ensure_ascii=False)})

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
            "status": "ok",
            "understood": True,
            "needs_repeat": False,
        }
    return _safe_json(data, fallback_question=fallback_question, original_message=message)

def _fallback_enabled() -> bool:
    return os.getenv("AI_FALLBACK_TO_LOCAL", "false").lower().strip() in ("1", "true", "yes", "sim")

def _temporary_failure(student_name: str, provider: str) -> dict:
    name = _student_name(student_name)
    return {
        "feedback": f"{name}, I need one more try.",
        "correction": None,
        "explanation_pt": f"A Luma online ({provider}) atingiu o limite temporário ou demorou para responder. Tente novamente em alguns segundos.",
        "next_question": f"{name}, can you send your sentence again?",
        "mood": "helping",
        "topic": "retry",
        "status": "repeat",
        "understood": False,
        "needs_repeat": True,
        "source": provider,
        "fallback": False,
    }

def generate_ai_response(
    message: str,
    student_name: str = "student",
    lesson_title: str | None = None,
    turn_index: int = 0,
    history: list[dict] | None = None,
) -> dict:
    provider = os.getenv("AI_PROVIDER", "mock").lower().strip()
    history = history or []

    if provider == "gemini":
        try:
            result = _gemini_response(message, student_name, lesson_title, turn_index, history)
            result["source"] = "gemini"
            result["fallback"] = False
            _mark_ai_ok("gemini")
            return result
        except Exception as exc:
            err_msg = f"{type(exc).__name__}: {exc}"
            print(f"[LUMA_GEMINI_ERROR] {err_msg}", flush=True)
            if _is_quota_error(err_msg):
                _write_ai_status("gemini", "quota_exceeded", err_msg, _extract_retry_after_seconds(err_msg))
            else:
                _write_ai_status("gemini", "error", err_msg, _extract_retry_after_seconds(err_msg))
            if not _fallback_enabled():
                return _temporary_failure(student_name, "gemini")
            result = _mock_response(message, student_name=student_name, turn_index=turn_index, history=history)
            result["source"] = "local"
            result["fallback"] = True
            return result

    if provider == "openai":
        try:
            result = _openai_response(message, student_name, lesson_title, turn_index, history)
            result["source"] = "openai"
            result["fallback"] = False
            _mark_ai_ok("openai")
            return result
        except Exception as exc:
            err_msg = f"{type(exc).__name__}: {exc}"
            print(f"[LUMA_OPENAI_ERROR] {err_msg}", flush=True)
            if _is_quota_error(err_msg):
                _write_ai_status("openai", "quota_exceeded", err_msg, _extract_retry_after_seconds(err_msg))
            else:
                _write_ai_status("openai", "error", err_msg, _extract_retry_after_seconds(err_msg))
            if not _fallback_enabled():
                return _temporary_failure(student_name, "openai")
            result = _mock_response(message, student_name=student_name, turn_index=turn_index, history=history)
            result["source"] = "local"
            result["fallback"] = True
            return result

    result = _mock_response(message, student_name=student_name, turn_index=turn_index, history=history)
    result["source"] = "local"
    result["fallback"] = False
    return result
