# ATS Resume Bot (Hackathon MVP)

Build an ATS scoring + resume fixing tool in under 2 hours:

- Input JD + Resume (`.txt`, `.pdf`, `.docx`, best-effort `.doc`)
- Output ATS score out of 10 + targeted improvement tips
- Auto-generate a fixed resume aligned to JD
- Offer 3 resume templates: `classic`, `modern`, `minimal`
- Return downloadable fixed resume (`.docx` or `.pdf`)
- Optional AI mode (`OPENAI_API_KEY`) for smarter rewrite and suggestions
- Shows runtime mode in bot response (`Mode` + `AI Applied`) for easy demo validation
- Bot channels:
  - Telegram (full conversational flow)
  - Discord (command + attachments)
  - WhatsApp (Twilio webhook text/media flow)

## 1) Quick Start

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Mac/Linux:

```bash
source .venv/bin/activate
```

Install:

```bash
pip install -r requirements.txt
```

Create env file:

```bash
copy .env.example .env
```

Fill `.env`:

```env
TELEGRAM_BOT_TOKEN=...
DISCORD_BOT_TOKEN=...
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.4
OPENAI_BASE_URL=
OPENROUTER_SITE_URL=http://localhost
OPENROUTER_APP_NAME=resume-ats-ai-bot
OUTPUT_DIR=outputs
PUBLIC_FILE_BASE_URL=
```

## 2) Run Services

Telegram bot:

```bash
python run.py telegram
```

Discord bot:

```bash
python run.py discord
```

API + WhatsApp webhook:

```bash
python run.py api --host 0.0.0.0 --port 8000
```

Health check:

```bash
GET /health
```

Templates list:

```bash
GET /templates
```

Analyze endpoint:

```bash
POST /analyze
```

Fix + download endpoint:

```bash
POST /fix-resume
```

## 3) Bot Usage

### Telegram

1. Send `/start`
2. Send `/ats`
3. Upload JD (text/file)
4. Upload Resume (text/file)
5. Receive:
   - ATS score
   - Mode status (`AI ...` or `Heuristic ...`)
   - `AI Applied: Yes/No` indicator
   - Improvement suggestions
   - Template options
6. Click template button and download the fixed resume

### Discord

1. Enable **Message Content Intent** in Discord Developer Portal
2. Invite bot to server
3. Use:

```text
!ats classic
```

Attach exactly 2 files in same message:
- File 1: JD
- File 2: Resume

### OpenRouter AI Mode (Optional)

Set in `.env`:

```env
OPENAI_API_KEY=<your_openrouter_key>
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=openai/gpt-4o-mini
OPENROUTER_SITE_URL=http://localhost
OPENROUTER_APP_NAME=resume-ats-ai-bot
```

Then restart bot processes.  
In bot output, verify:
- `Mode: AI openrouter:...`
- `AI Applied: Yes`

### WhatsApp (Twilio Sandbox)

Set webhook URL to:

```text
POST https://<your-domain>/whatsapp/webhook
```

Then send either:

1. Two media files in same message (JD first, Resume second)
2. Inline text format:

```text
JD: <job description text>
RESUME: <resume text>
```

## 4) Project Structure

```text
ats_bot/
  core/
    ats_engine.py
    parsers.py
    resume_parser.py
    resume_rewriter.py
    templates.py
    pipeline.py
  bots/
    telegram_bot.py
    discord_bot.py
    whatsapp_webhook.py
  api.py
run.py
```

## 5) Local Smoke Test

```bash
$env:PYTHONPATH='.'
python tests\smoke_test.py
```

## 6) GitHub + Teammate Flow

Create branch:

```bash
git checkout -b codex/hackathon-ats-bot
git add .
git commit -m "Build ATS scoring bot with Telegram/Discord/WhatsApp support"
```

Connect remote and push:

```bash
git remote add origin <your-github-repo-url>
git push -u origin codex/hackathon-ats-bot
```

Teammate workflow:

```bash
git fetch origin
git checkout -b codex/<teammate-feature> origin/codex/hackathon-ats-bot
```

Open PRs into `codex/hackathon-ats-bot`, then merge to `main`.

## 7) Deployment (Fastest Path)

### Render / Railway

1. Connect GitHub repo
2. If using Render Blueprint, keep `render.yaml` as-is and create service from repo
3. Build command:

```bash
pip install -r requirements.txt
```

4. Start command (API):

```bash
python run.py api --host 0.0.0.0 --port $PORT
```

5. Add env vars from `.env`
6. For Telegram bot, deploy as a **worker service** with:

```bash
python run.py telegram
```

7. For Discord bot, deploy as another worker:

```bash
python run.py discord
```

## 8) Notes

- `.doc` parsing is best-effort and depends on availability of `antiword`.
- Generated resume includes placeholders like `[add measurable result]` to avoid fake claims.
- If `OPENAI_API_KEY` is set, AI mode enhances suggestions and resume rewrite. If API fails, it falls back automatically to heuristic mode.
- You can use OpenRouter by setting `OPENAI_BASE_URL=https://openrouter.ai/api/v1` and a compatible model in `OPENAI_MODEL` (example: `openai/gpt-4o-mini`).
- AI calls are optional; if provider/model/key is invalid, the app auto-falls back and still completes ATS scoring + resume generation.
- For production, add auth/rate-limit + persistent storage.
