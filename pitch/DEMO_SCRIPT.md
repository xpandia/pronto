# PRONTO — 3-Minute Demo Script

## Setup & Tone
- Confident, conversational, zero filler
- Show, don't tell — every second on screen is product
- One continuous flow: Write -> Test -> Optimize -> Ship
- No slides during demo — pure product

---

## 0:00 — 0:15 | THE SETUP

**[Screen: Pronto landing page]**

> "If you write code, you have an IDE. If you write data pipelines, you have notebooks. But if you write prompts — the thing that actually controls AI — you have a text box and a prayer."
>
> "This is Pronto. The IDE for prompts. Let me show you what it does."

**[Click: Open Pronto app]**

---

## 0:15 — 0:50 | WRITE

**[Screen: Prompt Editor — clean, VS Code-style interface]**

> "Here's the editor. It's built for one thing: writing production-grade prompts."

**[Type out a prompt in real-time]**

Create a customer support prompt:
```
System: You are a support agent for an e-commerce platform.
Given a customer message, classify the intent and draft a response.

Variables: {{customer_name}}, {{order_id}}, {{message}}

Output schema:
- intent: [refund, tracking, complaint, general]
- response: string
- escalate: boolean
```

> "Structured authoring. Variables with interpolation. Output schema validation. This isn't a text box — it's an instrument."
>
> "And every edit is versioned automatically. I can go back to any point in this prompt's history, just like git."

**[Quick flash: version history sidebar showing v1, v2, v3]**

---

## 0:50 — 1:30 | TEST

**[Click: "Test" button]**

> "Now here's where it gets interesting. I'm going to test this prompt against three AWS Bedrock models at the same time."

**[Screen: Model selector — check Claude 3.5, Titan Text, Llama 3]**

**[Fill in test variables]**
- customer_name: "Sarah Chen"
- order_id: "ORD-4821"
- message: "I never received my package and it's been 12 days. I want a refund."

**[Click: "Run All"]**

**[Screen: Three results appear side by side within seconds]**

> "Three models. One click. Ten seconds."
>
> "Look at this — Claude classified it correctly as 'refund,' drafted a polished response, and flagged it for escalation. Titan got the intent right but the tone is off. Llama missed the escalation flag entirely."

**[Highlight the comparison metrics below each result]**

> "And right here — latency, token count, estimated cost per call. Claude is the best output but costs 3x more than Titan. That's a real engineering decision you can now make with data, not guesswork."

---

## 1:30 — 2:10 | OPTIMIZE

**[Click: "Optimize" button on the prompt]**

> "But we're not done. Watch this."

**[Screen: AI Optimization panel slides in with suggestions]**

Suggestions shown:
1. "Add explicit tone instruction to reduce variance across models"
2. "Constrain response length to reduce token usage by ~40%"
3. "Add fallback intent category for ambiguous messages"

> "Pronto's optimization engine analyzes your prompt and gives you concrete suggestions. Not vague advice — specific, actionable changes."

**[Click: "Apply suggestion #1" — prompt updates in editor]**

> "One click. The prompt is tighter. Let me re-run the test."

**[Click: "Run All" again — new results appear]**

> "Look — Titan's response just got dramatically better with that one change. Same model, same cost, better output. That's what a real tool gives you."

---

## 2:10 — 2:45 | SHIP

**[Click: "Ship" button]**

> "The prompt works. Now I ship it."

**[Screen: Deploy modal with options]**

> "I can export the config as JSON for my codebase. I can generate a shareable link so my team can review it — like a pull request, but for prompts. Or I can deploy it directly through the Pronto API."

**[Click: "Generate API Endpoint"]**

**[Screen: API endpoint and code snippet appear]**

```python
import requests

response = requests.post(
    "https://api.getpronto.dev/v1/prompts/cs-support/run",
    json={"customer_name": "Sarah Chen", "order_id": "ORD-4821",
          "message": "Where is my package?"},
    headers={"Authorization": "Bearer pk_live_..."}
)
```

> "One endpoint. Versioned. Monitored. Production-ready."

---

## 2:45 — 3:00 | THE CLOSE

**[Screen: Pull back to show the full Pronto dashboard — prompts, analytics, team activity]**

> "Write it. Test it across Bedrock models. Optimize it with AI. Ship it with one click."
>
> "Thirty million developers are writing prompts every day with zero tools built for the job."
>
> "Pronto changes that."
>
> "The IDE for prompts. Built on AWS."

**[Screen: Pronto logo + tagline: "Write better prompts. Ship better AI."]**

---

## Demo Checklist

- [ ] Prompt editor is loaded and empty before demo starts
- [ ] Bedrock models are pre-configured and warmed up (avoid cold start delays)
- [ ] Test variables are ready to paste (don't waste time typing inputs)
- [ ] Optimization engine is primed with the target prompt structure
- [ ] API endpoint generation works end-to-end
- [ ] Have a backup recording in case of live demo failure
- [ ] Total runtime rehearsed to exactly 3 minutes
