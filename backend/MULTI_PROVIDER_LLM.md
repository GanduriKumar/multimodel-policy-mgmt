# Multi-Provider LLM Support

## Overview

The policy management system now supports multiple LLM providers for the protect-and-generate workflow. Users can specify which LLM provider to use via the API request, allowing flexibility in choosing between different AI services based on requirements, costs, or availability.

## Supported Providers

| Provider | Value | Status | Requirements |
|----------|-------|--------|--------------|
| **Ollama** | `ollama` | ✅ Fully Supported | Ollama running locally or accessible via network |
| **OpenAI** | `openai` | ✅ Fully Supported | `OPENAI_API_KEY` environment variable |
| **Vertex AI** | `vertex` | ⚠️ Placeholder | GCP credentials and configuration |

## Usage

### API Request

Add the `llm_provider` field to your protect-generate request:

```json
{
  "tenant_id": 1,
  "input_text": "Write a summary about renewable energy",
  "llm_provider": "openai"
}
```

### Provider Selection

```python
import requests

# Use OpenAI
response = requests.post(
    "http://localhost:8000/api/protect-generate",
    json={
        "tenant_id": 1,
        "input_text": "Explain machine learning",
        "llm_provider": "openai"
    }
)

# Use Ollama (default)
response = requests.post(
    "http://localhost:8000/api/protect-generate",
    json={
        "tenant_id": 1,
        "input_text": "Explain machine learning",
        "llm_provider": "ollama"
    }
)

# Use default provider (omit llm_provider field)
response = requests.post(
    "http://localhost:8000/api/protect-generate",
    json={
        "tenant_id": 1,
        "input_text": "Explain machine learning"
    }
)
```

## Configuration

### Ollama Setup

1. **Install Ollama**: Follow instructions at [ollama.ai](https://ollama.ai)

2. **Pull a model**:
   ```bash
   ollama pull llama2
   ```

3. **Configure endpoint** (optional):
   ```bash
   export OLLAMA_BASE_URL=http://localhost:11434
   ```

### OpenAI Setup

1. **Get API Key**: Obtain from [platform.openai.com](https://platform.openai.com)

2. **Set environment variable**:
   ```bash
   export OPENAI_API_KEY=sk-...
   ```

3. **Configure model** (optional):
   ```bash
   export OPENAI_MODEL=gpt-4
   ```

### Vertex AI Setup

⚠️ **Note**: Vertex AI integration is currently a placeholder and requires implementation.

1. **GCP Project Setup**: Create or use existing GCP project
2. **Enable Vertex AI API**: In Google Cloud Console
3. **Service Account**: Create and download credentials
4. **Set credentials**:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
   export VERTEX_PROJECT_ID=your-project-id
   export VERTEX_LOCATION=us-central1
   ```

## RAG with Multiple Providers

The provider selection works seamlessly with RAG (Retrieval-Augmented Generation):

```python
response = requests.post(
    "http://localhost:8000/api/protect-generate",
    json={
        "tenant_id": 1,
        "input_text": "Summarize the benefits of renewable energy",
        "llm_provider": "openai",
        "retrieval_query": "renewable energy benefits",
        "evidence_payloads": [
            {
                "text": "Solar power reduces emissions...",
                "source_uri": "https://example.com/solar",
                "metadata": {"category": "environmental"}
            },
            {
                "text": "Wind energy creates jobs...",
                "source_uri": "https://example.com/wind",
                "metadata": {"category": "economic"}
            }
        ]
    }
)
```

## Response Format

The response format is consistent regardless of provider:

```json
{
  "allowed": true,
  "risk_score": 15,
  "policy_reasons": ["is_safe_output:true"],
  "risk_reasons": [],
  "grounded_claims": [
    {
      "text": "Solar power reduces carbon emissions",
      "score": 0.95,
      "supported": true,
      "matched_evidence_ids": [0]
    }
  ],
  "raw_model_output": "Renewable energy offers numerous benefits...",
  "trace_id": "abc123-def456-..."
}
```

## Testing

Run the multi-provider test suite:

```bash
cd backend
python test_multi_provider.py
```

This will test:
- Default provider (Ollama)
- Explicit Ollama selection
- OpenAI provider
- RAG with evidence
- Vertex AI (if configured)

## Architecture

### Request Flow

1. **API Request** → `ProtectGenerateRequest` with optional `llm_provider`
2. **Endpoint** → Extracts provider from request payload
3. **Dependency Injection** → `get_governed_generation_service(llm_provider=...)`
4. **LLM Client Factory** → `create_llm_client(provider)` creates appropriate client
5. **Generation Service** → Uses client to generate response
6. **Response** → Returns unified format regardless of provider

### Code Structure

```
backend/app/
├── schemas/
│   ├── protect.py              # ProtectRequest with llm_provider field
│   └── generation.py           # ProtectGenerateRequest inherits field
├── services/
│   ├── llm_gateway.py          # Multi-provider LLM abstraction
│   └── governed_generation_service.py  # Orchestrates generation
├── core/
│   └── deps.py                 # Dependency injection with provider
└── api/routes/
    └── protect_generate.py     # Endpoint passes provider through
```

### LLM Gateway

The `llm_gateway.py` module provides a protocol-based abstraction:

```python
from app.services.llm_gateway import create_llm_client

# Create client for specific provider
client = create_llm_client("openai")
output = client.generate("Your prompt here")

# Auto-select based on environment
client = create_llm_client()  # Defaults to Ollama
```

## Error Handling

### Invalid Provider

If an invalid provider is specified:

```json
{
  "llm_provider": "invalid-provider"
}
```

The system will fall back to the default (Ollama) or raise an error depending on configuration.

### Provider Not Available

If the selected provider is not properly configured (e.g., missing API key):

```
Status: 500
{
  "detail": "Internal error"
}
```

Check logs for specific error details:
```bash
tail -f backend/logs/app.log
```

## Best Practices

1. **Default Provider**: Set a reliable default (Ollama for on-prem, OpenAI for cloud)

2. **Cost Management**: Track usage per provider for cost optimization

3. **Fallback Strategy**: Implement retry logic with alternative providers

4. **Provider Selection Logic**:
   - Use Ollama for development and on-premise deployments
   - Use OpenAI for production workloads requiring high quality
   - Use Vertex AI for GCP-integrated applications

5. **Environment Variables**: Keep provider credentials in environment variables, never in code

## Governance & Audit

All LLM calls are tracked in the governance ledger with provider information:

```json
{
  "trace_id": "abc123...",
  "entries": [
    {
      "type": "model_output",
      "data": {
        "provider": "llm_gateway",
        "model": "gpt-4",
        "preview": "..."
      }
    }
  ]
}
```

## Future Enhancements

- [ ] Provider-specific model selection
- [ ] Cost tracking per provider
- [ ] Automatic provider failover
- [ ] Provider performance metrics
- [ ] Azure OpenAI support
- [ ] Anthropic Claude support
- [ ] Cohere support

## Troubleshooting

### Ollama Connection Failed

```
Error: Could not connect to Ollama
```

**Solution**: Verify Ollama is running:
```bash
ollama serve
```

### OpenAI Authentication Error

```
Error: OpenAI API key not found
```

**Solution**: Set API key:
```bash
export OPENAI_API_KEY=sk-...
```

### Provider Timeout

```
Error: Request timeout
```

**Solution**: Increase timeout or check provider availability:
```bash
curl http://localhost:11434/api/version  # Ollama health check
```

## Related Documentation

- [LLM Intent Classification](../LLM_INTENT_CLASSIFICATION.md)
- [Sample App Integration](SampleAppIntegration.md)
- [User Guide](../UserGuide.md)
