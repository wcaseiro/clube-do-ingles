import json
from sqlalchemy.orm import Session
from .database import Base, engine, SessionLocal
from .models import User, Class, InviteLink, ClassStudent, Module, Lesson, Quiz
from .security import get_password_hash

MODULES = [
    ("Hello", "Aprenda a cumprimentar e se apresentar.", [
        ("Hello and Hi", "Cumprimentar alguém", "Hello!", "Olá!", "Hello! How are you?", "Olá! Como você está?", "Hello!"),
        ("My name is...", "Dizer seu nome", "My name is Helena.", "Meu nome é Helena.", "Hello! My name is Helena.", "Olá! Meu nome é Helena.", "My name is _____."),
        ("I am 12 years old", "Dizer sua idade", "I am twelve years old.", "Eu tenho doze anos.", "I am twelve years old and I am a student.", "Tenho doze anos e sou estudante.", "I am _____ years old."),
        ("I am from Brazil", "Dizer de onde você é", "I am from Brazil.", "Eu sou do Brasil.", "I am from Brazil and I speak Portuguese.", "Sou do Brasil e falo português.", "I am from _____."),
        ("Nice to meet you", "Encerrar uma apresentação", "Nice to meet you.", "Prazer em conhecer você.", "Hello, my name is Helena. Nice to meet you.", "Olá, meu nome é Helena. Prazer em conhecer você.", "Nice to meet _____."),
    ]),
    ("About Me", "Fale sobre gostos e preferências.", [
        ("I like...", "Falar do que gosta", "I like music.", "Eu gosto de música.", "I like music and animals.", "Eu gosto de música e animais.", "I like _____."),
        ("I don't like...", "Falar do que não gosta", "I don't like onions.", "Eu não gosto de cebola.", "I don't like onions, but I like pizza.", "Não gosto de cebola, mas gosto de pizza.", "I don't like _____."),
        ("My favorite color is...", "Falar cor favorita", "My favorite color is blue.", "Minha cor favorita é azul.", "My favorite color is blue.", "Minha cor favorita é azul.", "My favorite color is _____."),
        ("My favorite food is...", "Falar comida favorita", "My favorite food is pizza.", "Minha comida favorita é pizza.", "My favorite food is pizza because it is delicious.", "Minha comida favorita é pizza porque é deliciosa.", "My favorite food is _____."),
        ("I am happy", "Falar sentimentos simples", "I am happy.", "Eu estou feliz.", "I am happy today.", "Eu estou feliz hoje.", "I am _____."),
    ]),
    ("Family", "Fale sobre sua família.", [
        ("Mother and father", "Aprender membros da família", "This is my mother.", "Esta é minha mãe.", "This is my mother and this is my father.", "Esta é minha mãe e este é meu pai.", "This is my _____."),
        ("Brother and sister", "Falar irmãos", "I have one brother.", "Eu tenho um irmão.", "I have one brother and one sister.", "Tenho um irmão e uma irmã.", "I have one _____."),
        ("This is my family", "Apresentar família", "This is my family.", "Esta é minha família.", "This is my family. They are very nice.", "Esta é minha família. Eles são muito legais.", "This is my _____."),
        ("I live with my family", "Dizer com quem mora", "I live with my family.", "Eu moro com minha família.", "I live with my family in Brazil.", "Moro com minha família no Brasil.", "I live with my _____."),
        ("My family is nice", "Descrever família", "My family is nice.", "Minha família é legal.", "My family is nice and funny.", "Minha família é legal e divertida.", "My family is _____."),
    ]),
    ("School", "Fale sobre escola e rotina.", [
        ("I go to school", "Falar que vai à escola", "I go to school.", "Eu vou para a escola.", "I go to school in the morning.", "Vou para a escola de manhã.", "I go to _____."),
        ("My favorite subject", "Falar matéria favorita", "My favorite subject is Math.", "Minha matéria favorita é matemática.", "My favorite subject is Math.", "Minha matéria favorita é matemática.", "My favorite subject is _____."),
        ("I have homework", "Falar tarefa", "I have homework today.", "Eu tenho lição de casa hoje.", "I have homework today.", "Tenho lição de casa hoje.", "I have _____."),
        ("I study English", "Falar estudos", "I study English every day.", "Eu estudo inglês todos os dias.", "I study English every day.", "Estudo inglês todos os dias.", "I study _____."),
        ("My teacher is nice", "Descrever professor", "My teacher is nice.", "Minha professora é legal.", "My teacher is nice and patient.", "Minha professora é legal e paciente.", "My teacher is _____."),
    ]),
    ("Food", "Peça comida e fale preferências.", [
        ("I am hungry", "Dizer que está com fome", "I am hungry.", "Estou com fome.", "I am hungry. I want a sandwich.", "Estou com fome. Quero um sanduíche.", "I am _____."),
        ("I am thirsty", "Dizer que está com sede", "I am thirsty.", "Estou com sede.", "I am thirsty. I want water.", "Estou com sede. Quero água.", "I am _____."),
        ("I would like water", "Pedir água", "I would like water, please.", "Eu gostaria de água, por favor.", "I would like water, please.", "Eu gostaria de água, por favor.", "I would like _____, please."),
        ("Can I have a sandwich?", "Pedir comida", "Can I have a sandwich?", "Posso comer/pegar um sanduíche?", "Can I have a sandwich, please?", "Posso pegar um sanduíche, por favor?", "Can I have _____?"),
        ("How much is it?", "Perguntar preço", "How much is it?", "Quanto custa?", "How much is it, please?", "Quanto custa, por favor?", "How much is _____?"),
    ]),
    ("Travel", "Frases úteis para viagens.", [
        ("Where is the bathroom?", "Perguntar banheiro", "Where is the bathroom?", "Onde fica o banheiro?", "Excuse me, where is the bathroom?", "Com licença, onde fica o banheiro?", "Where is the _____?"),
        ("I need help", "Pedir ajuda", "I need help.", "Eu preciso de ajuda.", "Excuse me, I need help.", "Com licença, preciso de ajuda.", "I need _____."),
        ("I am lost", "Dizer que está perdido", "I am lost.", "Estou perdido/perdida.", "I am lost. Can you help me?", "Estou perdido/perdida. Você pode me ajudar?", "I am _____."),
        ("I would like a ticket", "Comprar bilhete", "I would like a ticket, please.", "Eu gostaria de uma passagem, por favor.", "I would like a ticket to London, please.", "Eu gostaria de uma passagem para Londres, por favor.", "I would like a ticket to _____."),
        ("Can you speak slowly?", "Pedir para falar devagar", "Can you speak slowly, please?", "Você pode falar devagar, por favor?", "I don't understand. Can you speak slowly, please?", "Não entendi. Você pode falar devagar, por favor?", "Can you speak _____, please?"),
    ]),
]

def seed():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        admin = db.query(User).filter(User.nickname == "admin", User.role == "admin").first()
        if not admin:
            admin = User(first_name="Admin", nickname="admin", password_hash=get_password_hash("admin123"), role="admin", avatar="🛡️")
            db.add(admin)
        class_ = db.query(Class).filter(Class.code == "HELENA2026").first()
        if not class_:
            class_ = Class(name="Clube da Helena", description="Turma inicial do Clube do Inglês", code="HELENA2026", level="A1 Beginner")
            db.add(class_); db.flush()
        invite = db.query(InviteLink).filter(InviteLink.code == "HELENA2026").first()
        if not invite:
            db.add(InviteLink(class_id=class_.id, code="HELENA2026", is_active=True))
        helena = db.query(User).filter(User.nickname == "Helena").first()
        if admin and class_ and not db.query(ClassStudent).filter(ClassStudent.class_id == class_.id, ClassStudent.user_id == admin.id).first():
            db.add(ClassStudent(class_id=class_.id, user_id=admin.id, status="active"))
        if not helena:
            helena = User(first_name="Helena", nickname="Helena", password_hash=get_password_hash("helena123"), role="student", avatar="🌟")
            db.add(helena); db.flush()
            db.add(ClassStudent(class_id=class_.id, user_id=helena.id, status="active"))
        if db.query(Module).count() == 0:
            lesson_order_global = 1
            for mi, (title, desc, lessons) in enumerate(MODULES, start=1):
                m = Module(title=title, description=desc, level="A1", order_index=mi)
                db.add(m); db.flush()
                for li, lesson in enumerate(lessons, start=1):
                    l_title, objective, phrase_en, phrase_pt, example_en, example_pt, quiz_fill = lesson
                    l = Lesson(module_id=m.id, title=l_title, objective=objective, phrase_en=phrase_en, phrase_pt=phrase_pt, example_en=example_en, example_pt=example_pt, content_json=json.dumps({"practice": [phrase_en, example_en], "tip": "Listen, repeat and say it with confidence."}), order_index=li)
                    db.add(l); db.flush()                    # quiz contextual com distratores menos óbvios
                    quiz_data = {
                        "Hello!": ("Você acabou de encontrar um amigo no corredor. O que você diz primeiro?", "Hello!", "I am from Brazil.", "My favorite food is pizza.", "A", "Usamos 'Hello!' para cumprimentar alguém."),
                        "My name is Helena.": ("Você quer se apresentar para uma colega nova. Qual frase faz mais sentido?", "My name is Helena.", "I am twelve years old.", "This is my family.", "A", "Para dizer o seu nome, usamos 'My name is ...'."),
                        "I am twelve years old.": ("Alguém perguntou sua idade. Qual é a melhor resposta?", "I am twelve years old.", "My name is Helena.", "I am from Brazil.", "A", "Para falar idade em inglês, usamos 'I am ... years old'."),
                        "I am from Brazil.": ("Uma criança perguntou de onde você é. O que você responde?", "I am from Brazil.", "I live with my family.", "I like music.", "A", "'I am from Brazil' indica seu país de origem."),
                        "Nice to meet you.": ("Depois de se apresentar, como encerrar de forma educada?", "Nice to meet you.", "How much is it?", "I am happy.", "A", "'Nice to meet you' é usado ao conhecer alguém."),
                        "I like music.": ("Você quer contar algo de que gosta. Qual frase está correta?", "I like music.", "I am music.", "This is music.", "A", "Use 'I like...' para falar do que você gosta."),
                        "I don't like onions.": ("No almoço, você quer dizer que não gosta de cebola. Qual frase escolhe?", "I don't like onions.", "I like onions.", "My onions is blue.", "A", "Use 'I don't like...' para dizer do que não gosta."),
                        "My favorite color is blue.": ("Qual frase fala sobre cor favorita?", "My favorite color is blue.", "I am blue years old.", "This is my blue.", "A", "Essa estrutura serve para contar sua cor favorita."),
                        "My favorite food is pizza.": ("Você quer contar sua comida favorita. O que diz?", "My favorite food is pizza.", "I would like pizza, please.", "This is my pizza family.", "A", "'My favorite food is...' fala sobre preferência."),
                        "I am happy.": ("Como dizer que você está feliz?", "I am happy.", "I like happy.", "This is happy.", "A", "Usamos 'I am...' para sentimentos."),
                        "This is my mother.": ("Mostrando uma foto da sua mãe, qual frase usar?", "This is my mother.", "I am my mother.", "My mother is school.", "A", "Use 'This is my...' para apresentar alguém."),
                        "I have one brother.": ("Se você tem um irmão, qual frase combina?", "I have one brother.", "This is one brother.", "I am one brother.", "A", "Use 'I have...' para falar de irmãos."),
                        "This is my family.": ("Mostrando uma foto da família, o que você diz?", "This is my family.", "I am my family.", "Can I have a family?", "A", "A frase correta para apresentar a família é 'This is my family.'"),
                        "I live with my family.": ("Qual frase diz com quem você mora?", "I live with my family.", "I am with my family.", "My family is in school.", "A", "Use 'I live with...' para dizer com quem mora."),
                        "My family is nice.": ("Você quer descrever sua família de forma positiva. Qual frase usar?", "My family is nice.", "My family are bathroom.", "I family nice.", "A", "'My family is nice' descreve a família."),
                        "I go to school.": ("Como dizer que você vai para a escola?", "I go to school.", "I am school.", "This is my school go.", "A", "Use 'I go to school.' para falar da sua rotina."),
                        "My favorite subject is Math.": ("Qual frase fala sobre sua matéria favorita?", "My favorite subject is Math.", "I like teacher is Math.", "This is my Math family.", "A", "Essa estrutura serve para contar sua matéria favorita."),
                        "I have homework today.": ("Hoje você tem lição de casa. O que diria?", "I have homework today.", "I am homework today.", "My homework is family.", "A", "Use 'I have homework today.' para falar da tarefa."),
                        "I study English every day.": ("Como dizer que estuda inglês todos os dias?", "I study English every day.", "I go English every day.", "English is my bathroom.", "A", "Use 'I study English every day.' para falar do estudo."),
                        "My teacher is nice.": ("Qual frase descreve sua professora?", "My teacher is nice.", "I like teacher nice.", "Teacher is my family.", "A", "Use essa frase para descrever sua professora."),
                        "I am hungry.": ("Você quer dizer que está com fome. Qual frase escolher?", "I am hungry.", "I like hungry.", "Can I hungry?", "A", "'I am hungry.' significa 'Estou com fome'."),
                        "I am thirsty.": ("Como dizer que está com sede?", "I am thirsty.", "I have thirsty.", "My thirsty is blue.", "A", "'I am thirsty.' significa 'Estou com sede'."),
                        "I would like water, please.": ("Você quer pedir água de forma educada. O que diz?", "I would like water, please.", "My water is please.", "This is a water family.", "A", "Use essa frase para pedir água com educação."),
                        "Can I have a sandwich?": ("Na lanchonete, como pedir um sanduíche?", "Can I have a sandwich?", "I am a sandwich.", "Where is the sandwich family?", "A", "Use 'Can I have...' para pedir algo."),
                        "How much is it?": ("Você quer saber o preço. Qual frase combina?", "How much is it?", "I am from price.", "This is my ticket.", "A", "Essa frase é usada para perguntar o preço."),
                        "Where is the bathroom?": ("Em uma viagem, como perguntar onde fica o banheiro?", "Where is the bathroom?", "I am the bathroom.", "Nice to meet the bathroom.", "A", "Use essa frase para perguntar onde fica o banheiro."),
                        "I need help.": ("Se você precisa de ajuda, qual frase usar?", "I need help.", "I am help.", "Can you speak bathroom?", "A", "Use 'I need help.' quando precisar de ajuda."),
                        "I am lost.": ("Você se perdeu. O que pode dizer?", "I am lost.", "I go lost.", "My lost is blue.", "A", "'I am lost.' significa 'Estou perdido'."),
                        "I would like a ticket, please.": ("Na estação, como pedir uma passagem?", "I would like a ticket, please.", "This is my ticket family.", "I am a ticket, please.", "A", "Use essa frase para pedir uma passagem."),
                        "Can you speak slowly, please?": ("Se alguém fala rápido demais, qual frase usar?", "Can you speak slowly, please?", "I am speak slowly.", "My name is slowly.", "A", "Essa frase pede para a pessoa falar devagar."),
                    }
                    if phrase_en in quiz_data:
                        question, a, b, c, correct, explanation = quiz_data[phrase_en]
                    else:
                        question, a, b, c, correct, explanation = f"Em qual situação você usaria a frase: {phrase_en}?", phrase_en, "I am twelve years old.", "My name is John.", "A", f"Resposta correta: {phrase_en}"
                    db.add(Quiz(lesson_id=l.id, question=question, option_a=a, option_b=b, option_c=c, correct_option=correct, explanation=explanation))
                    lesson_order_global += 1
        db.commit()
        print("Seed concluído: admin/admin123, Helena/helena123, turma HELENA2026")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
