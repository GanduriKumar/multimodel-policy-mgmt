"""
Multi-Provider LLM Example

This example demonstrates how to use different LLM providers (OpenAI, Ollama)
with the protect-generate API endpoint.
"""

import json
import urllib.request
from typing import Optional


def protect_and_generate(
    input_text: str,
    tenant_id: int = 1,
    policy_slug: str = "content-safety",
    llm_provider: Optional[str] = None,
    evidence_payloads: Optional[list] = None,
) -> dict:
    """
    Call the protect-generate endpoint with optional provider selection.
    
    Args:
        input_text: The prompt to send to the LLM
        tenant_id: Tenant ID (default 1)
        policy_slug: Policy to enforce (default "content-safety")
        llm_provider: LLM provider ("openai", "ollama", "vertex", or None for default)
        evidence_payloads: Optional RAG evidence chunks
    
    Returns:
        API response as dictionary
    """
    payload = {
        "tenant_id": tenant_id,
        "policy_slug": policy_slug,
        "input_text": input_text,
    }
    
    # Add optional llm_provider field
    if llm_provider:
        payload["llm_provider"] = llm_provider
    
    # Add optional evidence
    if evidence_payloads:
        payload["evidence_payloads"] = evidence_payloads
    
    # Make HTTP request
    req = urllib.request.Request(
        "http://localhost:8000/api/protect-generate",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code}")
        print(e.read().decode("utf-8"))
        raise
    except urllib.error.URLError as e:
        print(f"Connection Error: {e.reason}")
        print("Make sure the backend is running: cd backend && make run")
        raise


def main():
    """Run examples with different LLM providers."""
    
    prompt = "Explain the benefits of renewable energy in 2-3 sentences."
    
    print("Multi-Provider LLM Examples")
    print("=" * 60)
    
    # Example 1: Default provider (Ollama)
    print("\n1. Using Default Provider (Ollama)")
    print("-" * 60)
    try:
        result = protect_and_generate(
            input_text=prompt,
            llm_provider=None,  # Uses default
        )
        print(f"Allowed: {result['allowed']}")
        print(f"Risk Score: {result['risk_score']}")
        print(f"Output: {result['raw_model_output'][:150]}...")
    except Exception as e:
        print(f"Error: {e}")
    
    # Example 2: Explicit Ollama
    print("\n2. Explicitly Using Ollama")
    print("-" * 60)
    try:
        result = protect_and_generate(
            input_text=prompt,
            llm_provider="ollama",
        )
        print(f"Allowed: {result['allowed']}")
        print(f"Risk Score: {result['risk_score']}")
        print(f"Output: {result['raw_model_output'][:150]}...")
    except Exception as e:
        print(f"Error: {e}")
    
    # Example 3: OpenAI (requires OPENAI_API_KEY)
    print("\n3. Using OpenAI")
    print("-" * 60)
    print("(Requires OPENAI_API_KEY environment variable)")
    try:
        result = protect_and_generate(
            input_text=prompt,
            llm_provider="openai",
        )
        print(f"Allowed: {result['allowed']}")
        print(f"Risk Score: {result['risk_score']}")
        print(f"Output: {result['raw_model_output'][:150]}...")
    except Exception as e:
        print(f"Error: {e}")
    
    # Example 4: RAG with OpenAI
    print("\n4. RAG with Evidence (OpenAI)")
    print("-" * 60)
    evidence = [
        {
            "text": "Solar and wind energy reduce carbon emissions by up to 90% compared to fossil fuels.",
            "source_uri": "https://example.com/renewable-study",
            "metadata": {"type": "research", "year": 2024},
        },
        {
            "text": "Renewable energy creates 3x more jobs than traditional energy sources.",
            "source_uri": "https://example.com/job-report",
            "metadata": {"type": "economic", "year": 2024},
        },
    ]
    try:
        result = protect_and_generate(
            input_text=prompt,
            llm_provider="openai",
            evidence_payloads=evidence,
        )
        print(f"Allowed: {result['allowed']}")
        print(f"Risk Score: {result['risk_score']}")
        print(f"Output: {result['raw_model_output'][:150]}...")
        print(f"\nGrounded Claims: {len(result.get('grounded_claims', []))}")
        for claim in result.get('grounded_claims', [])[:2]:
            print(f"  - {claim['text'][:60]}... (score: {claim['score']:.2f})")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 60)
    print("Examples Complete!")


if __name__ == "__main__":
    main()
