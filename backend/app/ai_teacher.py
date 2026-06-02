import os
import json
from dotenv import load_dotenv

load_dotenv()

SAFE_TEACHER_PROMPT = """
Você é uma professora de inglês para crianças e adolescentes brasileiros.
Use linguagem simples, segura e motivadora. O aluno está no nível A1/A2.
Não peça endereço, telefone, escola, redes sociais, sobrenome ou localização.
Não entre em assuntos adultos, violentos, políticos, religiosos ou inadequados.
Foque em escola, família, comida, animais, hobbies, rotina, esportes, música e viagem.
Corrija com gentileza e faça apenas uma pergunta por vez.
Responda sempre em JSON com feedback, correction, explanation_pt e next_question.
""".strip()

def _mock_response(message: str) -> dict:
    text = (message or "").strip()
    lower = text.lower()
    if not text:
        return {
            "feedback": "Vamos tentar juntos!",
            "correction": None,
            "explanation_pt": "Escreva uma frase simples em inglês.",
            "next_question": "What is your name?",
        }
    if "my name is" in lower:
        return {
            "feedback": "Fantastic! I loved your answer! ✨",
            "correction": None,
            "explanation_pt": "A frase está boa para se apresentar.",
            "next_question": "How old are you?",
        }
    if "i have" in lower and "years" in lower:
        return {
            "feedback": "Super try! You are getting stronger in English! 🚀",
            "correction": text.replace("I have", "I am"),
            "explanation_pt": "Para idade em inglês usamos 'I am', não 'I have'. Exemplo: I am twelve years old.",
            "next_question": "Can you try again? Say: I am twelve years old.",
        }
    if "i am" in lower:
        return {
            "feedback": "Excellent! You sounded like an English explorer! 🌟",
            "correction": None,
            "explanation_pt": "Você usou 'I am' corretamente.",
            "next_question": "What is your favorite food?",
        }
    return {
        "feedback": "Nice try! Let's make it even better together! 🤖",
        "correction": None,
        "explanation_pt": "Tente responder com uma frase curta em inglês, como: My name is Helena ou I like pizza.",
        "next_question": "What do you like?",
    }

def generate_ai_response(message: str, student_name: str = "student", lesson_title: str | None = None) -> dict:
    provider = os.getenv("AI_PROVIDER", "mock").lower()
    # MVP: mock seguro. Estrutura pronta para OpenAI/Ollama depois.
    if provider == "mock":
        return _mock_response(message)
    return _mock_response(message)
