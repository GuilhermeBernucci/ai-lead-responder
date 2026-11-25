# AI Lead Responder

**Never lose a lead because you replied too late.**

An AI automation for local service businesses (plumbers, contractors, remodelers).
When a customer requests a quote on the website, the AI instantly:

1. **Classifies urgency**: emergency, high, or normal
2. **Identifies the service** and a realistic price range
3. **Replies to the customer within seconds** with a professional, personalized email
4. **Shows everything on an owner dashboard**, with emergencies flagged in red

| Customer quote form | Owner dashboard |
|---|---|
| ![Customer form](demo-cliente.png) | ![Owner dashboard](demo-painel.png) |

## How it works

```
Customer form ──► app.py ──► ia.py ──► Claude (structured JSON output)
                    │                    urgency · service · price · summary · reply email
                    ▼
              pedidos.json ──► /painel (owner dashboard)
```

The AI is required to fill in a fixed JSON schema instead of returning free text,
so the rest of the system always receives predictable, validated data.

## Run it

Requires Python 3.10+.

```bash
python3 app.py
```

Then open http://localhost:8000. Without an API key, the app runs in **demo mode**
(simple keyword rules), so you can try it for free.

To use real AI:

```bash
pip install anthropic
export ANTHROPIC_API_KEY=your-key-here
python3 app.py
```

## Next steps (production version)

- Send the reply email for real (Gmail / SendGrid)
- SMS alert to the owner for emergencies (Twilio)
- Connect to the business's real website form or CRM
