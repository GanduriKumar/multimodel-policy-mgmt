# Multi-Provider LLM Architecture

## Request Flow

```
┌──────────────────────────────────────────────────────────────┐
│                     API Client Request                       │
│  POST /api/protect-generate                                  │
│  {                                                           │
│    "tenant_id": 1,                                          │
│    "input_text": "Explain AI",                             │
│    "llm_provider": "openai"  ◄── NEW FIELD                 │
│  }                                                           │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────────┐
│           FastAPI Route (protect_generate.py)                │
│  @router.post("/protect-generate")                           │
│  def protect_and_generate(                                   │
│      payload: ProtectGenerateRequest  ◄── Contains provider  │
│  ):                                                          │
│      service = get_governed_generation_service(              │
│          llm_provider=payload.llm_provider  ◄── Extract      │
│      )                                                       │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────────┐
│            Dependency Factory (deps.py)                      │
│  def get_governed_generation_service(                        │
│      llm_provider: Optional[str] = None  ◄── NEW PARAM      │
│  ):                                                          │
│      return GovernedGenerationService(                       │
│          llm_client=get_llm_client(llm_provider)  ◄── Pass   │
│      )                                                       │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────────┐
│           LLM Client Factory (deps.py)                       │
│  def get_llm_client(provider: Optional[str] = None):         │
│      return create_llm_client(provider)  ◄── Delegate        │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────────┐
│         Multi-Provider Gateway (llm_gateway.py)              │
│  def create_llm_client(provider: Optional[str]):             │
│      if provider == "openai":                                │
│          return OpenAiLLMClient()  ◄── OpenAI Client         │
│      elif provider == "vertex":                              │
│          return VertexLLMClient()  ◄── Vertex Client         │
│      else:                                                   │
│          return OllamaLLMClient()  ◄── Default/Ollama        │
└────────────────────┬─────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
┌──────────────┐ ┌──────────┐ ┌────────────┐
│ OpenAI Client│ │  Ollama  │ │Vertex Client│
│ (GPT-4, etc.)│ │ (Llama2) │ │  (PaLM)    │
└──────────────┘ └──────────┘ └────────────┘
        │            │            │
        └────────────┼────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────────┐
│       GovernedGenerationService (orchestrator)               │
│  - Pre-check with policy                                     │
│  - Call LLM client.generate()  ◄── Uses selected client     │
│  - Post-check safety                                         │
│  - Score groundedness                                        │
│  - Log to governance ledger                                  │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────────┐
│                   API Response                               │
│  {                                                           │
│    "allowed": true,                                         │
│    "risk_score": 15,                                        │
│    "raw_model_output": "...",  ◄── From selected provider   │
│    "trace_id": "...",                                       │
│    "grounded_claims": [...]                                 │
│  }                                                          │
└──────────────────────────────────────────────────────────────┘
```

## Component Changes

### 1. Schema Layer (Request Models)

```
ProtectRequest (protect.py)
├── tenant_id: int
├── input_text: str
├── policy_slug: Optional[str]
└── llm_provider: Optional[str]  ◄── NEW FIELD
    └── Values: "openai" | "ollama" | "vertex"

ProtectGenerateRequest (generation.py)
├── Inherits from ProtectRequest
├── retrieval_query: Optional[str]
└── evidence_payloads: Optional[List[Dict]]
    └── llm_provider inherited ◄── Automatically available
```

### 2. Dependency Injection Layer (deps.py)

```
BEFORE:
get_llm_client() → always returns OllamaLLMClient()

AFTER:
get_llm_client(provider: Optional[str])
├── if provider → create_llm_client(provider)
├── if None → create_llm_client(None) → defaults to Ollama
└── Returns: LLMClient protocol implementation
```

### 3. API Route Layer (protect_generate.py)

```
BEFORE:
service = Depends(get_governed_generation_service)
└── Fixed Ollama client

AFTER:
service = get_governed_generation_service(
    llm_provider=payload.llm_provider  ◄── Dynamic selection
)
└── Uses client based on request
```

## Data Flow Example

### Example 1: Using OpenAI

```
Request:
{
  "tenant_id": 1,
  "input_text": "Explain renewable energy",
  "llm_provider": "openai"
}
         │
         ▼
protect_generate endpoint
  │ extracts: llm_provider = "openai"
  ▼
get_governed_generation_service(llm_provider="openai")
  │
  ▼
get_llm_client("openai")
  │
  ▼
create_llm_client("openai")
  │
  ▼
OpenAiLLMClient()
  │ configured with OPENAI_API_KEY
  ▼
GovernedGenerationService
  │ calls: client.generate("Explain renewable energy")
  ▼
OpenAI API (GPT-4)
  │
  ▼
Response with OpenAI-generated content
```

### Example 2: Using Default (Ollama)

```
Request:
{
  "tenant_id": 1,
  "input_text": "Explain renewable energy"
  // No llm_provider field
}
         │
         ▼
protect_generate endpoint
  │ llm_provider = None
  ▼
get_governed_generation_service(llm_provider=None)
  │
  ▼
get_llm_client(None)
  │
  ▼
create_llm_client(None)
  │ provider is None → defaults to "ollama"
  ▼
OllamaLLMClient()
  │ configured with OLLAMA_BASE_URL
  ▼
GovernedGenerationService
  │ calls: client.generate("Explain renewable energy")
  ▼
Ollama API (Llama2)
  │
  ▼
Response with Ollama-generated content
```

## Provider Interface (Protocol)

```python
class LLMClient(Protocol):
    """Protocol defining LLM client interface"""
    
    def generate(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate text from prompt"""
        ...

# Implementations:
- OllamaLLMClient (fully implemented)
- OpenAiLLMClient (fully implemented)
- VertexLLMClient (placeholder)
```

## Configuration Per Provider

```
┌────────────────────────────────────────────────┐
│ Environment Variables                          │
├────────────────────────────────────────────────┤
│                                                │
│ OLLAMA                                         │
│ ├── OLLAMA_BASE_URL=http://localhost:11434    │
│ └── OLLAMA_MODEL=llama2                        │
│                                                │
│ OPENAI                                         │
│ ├── OPENAI_API_KEY=sk-...                     │
│ └── OPENAI_MODEL=gpt-4                         │
│                                                │
│ VERTEX AI                                      │
│ ├── GOOGLE_APPLICATION_CREDENTIALS=/path/...  │
│ ├── VERTEX_PROJECT_ID=my-project              │
│ └── VERTEX_LOCATION=us-central1               │
│                                                │
└────────────────────────────────────────────────┘
```

## Testing Strategy

```
test_multi_provider.py
├── Test 1: Default provider (no llm_provider field)
├── Test 2: Explicit Ollama (llm_provider="ollama")
├── Test 3: OpenAI (llm_provider="openai")
├── Test 4: RAG with evidence (any provider)
└── Test 5: Vertex AI (llm_provider="vertex")

Each test validates:
✓ Request accepted
✓ Provider used correctly
✓ Response format consistent
✓ Governance ledger updated
```

## Key Benefits

```
┌─────────────────────────────────────────────┐
│ 1. Flexibility                              │
│    Choose best LLM for each use case        │
├─────────────────────────────────────────────┤
│ 2. Cost Optimization                        │
│    Use cheaper provider when appropriate     │
├─────────────────────────────────────────────┤
│ 3. Redundancy                               │
│    Fallback if one provider unavailable     │
├─────────────────────────────────────────────┤
│ 4. Dev/Prod Split                           │
│    Ollama (dev) → OpenAI (production)       │
├─────────────────────────────────────────────┤
│ 5. Backward Compatible                      │
│    Existing code works without changes      │
└─────────────────────────────────────────────┘
```
