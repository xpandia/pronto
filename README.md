# Pronto

**The IDE for prompts.**

Pronto is an AI prompt engineering platform that gives developers the tools to write, test, optimize, and ship production-grade prompts — with the same rigor they ship code.

---

## The Problem

Every developer building with AI hits the same wall: prompts are treated like magic strings. No version control. No testing. No collaboration. No way to know if a prompt actually works until it's live and breaking things.

Prompt engineering today feels like writing code in Notepad — powerful in theory, painful in practice.

## The Solution

Pronto brings software engineering discipline to prompt development.

Write prompts in a structured editor. Test them against real models instantly. Optimize with AI-powered suggestions. Share and collaborate with your team. Deploy with confidence.

**One platform. Every prompt. Zero guesswork.**

---

## How It Works

### 1. Write
Open the prompt editor. Define your system prompt, user inputs, and expected outputs using a structured schema. Version everything automatically.

### 2. Test
Run your prompt against AWS Bedrock models (Claude, Titan, Llama) side-by-side. Compare outputs, latency, and cost. Catch regressions before they ship.

### 3. Ship
Export production-ready prompt configs, share with your team via a unique link, or deploy directly to your application through the Pronto API.

---

## Tech Stack

| Layer        | Technology                                      |
|------------- |-------------------------------------------------|
| AI Engine    | AWS Bedrock (Claude, Titan, Llama, Mistral)     |
| Backend      | FastAPI (Python), Mangum (Lambda-ready)         |
| Storage      | Amazon DynamoDB (5 tables, single-table design) |
| Frontend     | Vanilla HTML/CSS/JS (static landing page)       |
| Auth         | JWT (python-jose) + bcrypt (passlib)            |
| Infra        | CloudFormation (generated from Python)          |

---

## Architecture

```
User (Browser)
  |
  v
Static Landing Page (HTML/CSS/JS)
  |
  v
FastAPI Backend (Lambda-ready via Mangum)
  |-- Bedrock (multi-model invocations + prompt optimization)
  |-- DynamoDB (prompts, evaluations, A/B tests, analytics, users)
  |-- JWT Auth (bcrypt password hashing)
```

---

## Features

- **Prompt Editor** — Structured authoring with syntax highlighting, variable interpolation, and schema validation
- **Multi-Model Testing** — Run prompts against multiple Bedrock models simultaneously and compare results
- **Prompt Optimization** — AI-powered suggestions to improve clarity, reduce token usage, and boost output quality
- **Version History** — Full git-style versioning for every prompt iteration
- **Team Sharing** — Collaborate on prompts with unique shareable links and team workspaces
- **Analytics Dashboard** — Track latency, token usage, cost, and output quality over time
- **One-Click Deploy** — Export prompt configs or deploy via API to your production application

---

## Team

| Role               | Responsibility                                    |
|--------------------|---------------------------------------------------|
| Product / Design   | UX, landing page, pitch deck                      |
| Frontend Engineer  | Landing page, prompt editor UI                    |
| Backend Engineer   | FastAPI backend, Bedrock integration, DynamoDB    |
| AI / ML Engineer   | Prompt optimization engine, model routing         |

---

## Getting Started

```bash
# Clone the repo
git clone https://github.com/your-org/pronto.git
cd pronto

# Install backend dependencies
cd src/backend
pip install -r requirements.txt

# Set environment variables
export JWT_SECRET="your-secret-key"
export ADMIN_API_KEY="your-admin-key"

# Run locally
uvicorn app:app --host 0.0.0.0 --port 8000 --reload

# Frontend: open src/frontend/index.html in a browser
```

---

## Hackathon Submission Checklist

- [ ] Project registered on DoraHacks (AWS Prompt the Planet Challenge)
- [ ] Working demo deployed and accessible
- [ ] 3-minute pitch video recorded and uploaded
- [ ] README with architecture diagram and setup instructions
- [ ] Landing page live
- [ ] Backend API endpoints functional
- [ ] Prompt editor MVP operational
- [ ] Multi-model testing feature working
- [ ] At least one AWS Bedrock model integrated
- [ ] Team info submitted on DoraHacks
- [ ] Source code pushed to public repository

---

## License

MIT

---

*Built for the AWS Prompt the Planet Hackathon on DoraHacks.*
