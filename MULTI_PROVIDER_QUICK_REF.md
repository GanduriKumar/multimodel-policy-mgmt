# Multi-Provider LLM Quick Reference

## API Request Format

```json
{
  "tenant_id": 1,
  "input_text": "Your prompt here",
  "policy_slug": "content-safety",
  "llm_provider": "openai"  // Optional: "openai" | "ollama" | "vertex"
}
```

## Provider Options

| Provider | Value | Setup Required |
|----------|-------|----------------|
| Ollama (default) | `"ollama"` or omit field | `ollama serve` |
| OpenAI | `"openai"` | `export OPENAI_API_KEY=sk-...` |
| Vertex AI | `"vertex"` | GCP credentials |

## Quick Test

```bash
# Default provider
curl -X POST http://localhost:8000/api/protect-generate \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":1,"input_text":"Hello"}'

# OpenAI
curl -X POST http://localhost:8000/api/protect-generate \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":1,"input_text":"Hello","llm_provider":"openai"}'
```

## Python

```python
import requests

requests.post(
    "http://localhost:8000/api/protect-generate",
    json={"tenant_id": 1, "input_text": "Hello", "llm_provider": "openai"}
).json()
```

## Response

```json
{
  "allowed": true,
  "risk_score": 10,
  "raw_model_output": "...",
  "trace_id": "...",
  "policy_reasons": [...],
  "risk_reasons": [...],
  "grounded_claims": [...]
}
```

## Environment Setup

```bash
# Ollama
ollama pull llama2
ollama serve

# OpenAI
export OPENAI_API_KEY=sk-...
export OPENAI_MODEL=gpt-4  # optional

# Vertex AI
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/creds.json
export VERTEX_PROJECT_ID=your-project
export VERTEX_LOCATION=us-central1
```

## Full Documentation

See [MULTI_PROVIDER_LLM.md](backend/MULTI_PROVIDER_LLM.md) for complete guide.
