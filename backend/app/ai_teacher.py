import os
from dotenv import load_dotenv

load_dotenv()
SAFE_TEACHER_PROMPT = """
Você é a Luma, uma robô professora de inglês para crianças e adolescentes brasileiros.
Use linguagem simples, segura e motivadora. O aluno está no nível A1/A2.
Não peça endereço, telefone, escola, redes sociais, sobrenome ou localização.
Não entre em assuntos adultos, violentos, políticos, religiosos ou inadequados.
Foque em escola, família, comida, animais, hobbies, rotina, esportes, música e viagem.
Corrija com gentileza e faça apenas uma pergunta por vez.
""".strip()
CONVERSATION_FLOW = [
    {"topic":"name","question":"What is your name?","hint":"Responda: My name is..."},
    {"topic":"age","question":"How old are you?","hint":"Responda: I am twelve years old."},
    {"topic":"country","question":"Where are you from?","hint":"Responda: I am from Brazil."},
    {"topic":"likes","question":"What do you like?","hint":"Responda: I like music."},
    {"topic":"food","question":"What is your favorite food?","hint":"Responda: My favorite food is pizza."},
    {"topic":"school","question":"Do you like school?","hint":"Responda: Yes, I like school."},
    {"topic":"family","question":"Tell me about your family.","hint":"Responda: This is my family."},
    {"topic":"travel","question":"Can you say one travel phrase?","hint":"Responda: I need help. / Where is the bathroom?"},
]
def _topic_for_turn(turn_index:int)->dict:
    return CONVERSATION_FLOW[max(turn_index,0)%len(CONVERSATION_FLOW)]
def _next_topic(turn_index:int)->dict:
    return _topic_for_turn(turn_index+1)
def _mock_response(message:str, student_name:str="student", turn_index:int=0)->dict:
    text=(message or '').strip(); lower=text.lower(); current=_topic_for_turn(turn_index); nxt=_next_topic(turn_index)
    if not text:
        return {"feedback":"Hi! I am Luma. Let's start our English mission!","correction":None,"explanation_pt":current['hint'],"next_question":current['question'],"mood":"start","topic":current['topic']}
    correction=None; explanation="Muito bem! Vamos continuar a conversa com uma frase curta."
    if 'i have' in lower and 'years' in lower:
        correction=text.replace('I have','I am').replace('i have','I am'); explanation="Para falar idade em inglês, usamos 'I am', não 'I have'. Exemplo: I am twelve years old."; feedback="Great try! I understood you. Let's fix just one little thing."; next_question="Can you try again? Say: I am twelve years old."; topic='age'
    elif current['topic']=='name' and 'my name is' in lower:
        feedback=f"Fantastic! Nice to meet you, {student_name}!"; next_question=nxt['question']; topic=nxt['topic']
    elif current['topic']=='age' and ('years old' in lower or 'i am' in lower):
        feedback="Excellent! You said your age very well!"; next_question=nxt['question']; topic=nxt['topic']
    elif current['topic']=='country' and ('brazil' in lower or 'from' in lower):
        feedback="Amazing! Brazil is a great answer!"; next_question=nxt['question']; topic=nxt['topic']
    elif current['topic']=='likes' and ('i like' in lower or 'like' in lower):
        feedback="Great! I like your answer!"; next_question=nxt['question']; topic=nxt['topic']
    elif current['topic']=='food' and ('favorite food' in lower or 'pizza' in lower or 'food' in lower or 'i like' in lower):
        feedback="Yummy! That sounds delicious!"; next_question=nxt['question']; topic=nxt['topic']
    elif current['topic']=='school' and ('yes' in lower or 'no' in lower or 'school' in lower or 'i like' in lower):
        feedback="Good answer! You are doing great!"; next_question=nxt['question']; topic=nxt['topic']
    elif current['topic']=='family' and ('family' in lower or 'mother' in lower or 'father' in lower or 'brother' in lower or 'sister' in lower):
        feedback="Very nice! You can talk about your family!"; next_question=nxt['question']; topic=nxt['topic']
    elif current['topic']=='travel' and ('help' in lower or 'bathroom' in lower or 'ticket' in lower or 'slowly' in lower):
        feedback="Perfect! That is a useful travel phrase!"; next_question=nxt['question']; topic=nxt['topic']
    else:
        feedback="Nice try! I understood part of it. Let's make it even better."; explanation=f"Dica: {current['hint']}"; next_question=current['question']; topic=current['topic']
    return {"feedback":feedback,"correction":correction,"explanation_pt":explanation,"next_question":next_question,"mood":"happy" if correction is None else "helping","topic":topic}
def generate_ai_response(message:str, student_name:str="student", lesson_title:str|None=None, turn_index:int=0)->dict:
    return _mock_response(message, student_name=student_name, turn_index=turn_index)
