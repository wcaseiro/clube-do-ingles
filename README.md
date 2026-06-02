# Clube do Inglês — MVP v2

Web App/PWA para aprendizado de inglês com trilha A1, XP, ranking, quiz obrigatório e IA professora com suporte a voz no navegador.

## Contas iniciais

Aluno:
- Turma: `HELENA2026`
- Nickname: `Helena`
- Senha: `helena123`

Admin:
- Turma: `HELENA2026`
- Nickname: `admin`
- Senha: `admin123`

## Rodar backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 -m app.seed
uvicorn app.main:app --host 0.0.0.0 --port 8008
```

Teste:

```bash
curl http://127.0.0.1:8008/api/health
```

## Rodar frontend em teste

Em outro terminal:

```bash
cd frontend
python3 -m http.server 8083
```

Acesse:

```text
http://IP-DA-VM:8083
```

Quando o frontend está em `8080` ou `8083`, ele chama automaticamente a API em `http://IP-DA-VM:8008/api`.
Quando publicado com Nginx no domínio, ele usa `/api`.

## Novidades v2

- Quiz obrigatório para concluir cada aula.
- Botão `Concluir` fica bloqueado até o aluno acertar o quiz.
- Feedback visual quando acerta ou erra.
- Tela de trilha mais moderna, com módulos, progresso e próxima missão.
- Aula com navegação anterior/próxima.
- IA por voz usando recursos do navegador:
  - microfone para transformar fala em texto;
  - leitura em voz alta da resposta da IA.

## Observação sobre voz

O reconhecimento de voz depende do navegador. Teste preferencialmente no Chrome/Edge. Em alguns cenários, o navegador pode exigir HTTPS para liberar o microfone em domínio público.

## Publicação com Nginx

Use os arquivos em `deploy/` como base para publicar em:

```text
https://clube-do-ingles.4cloud.tech
```
