"""
Test multi-provider LLM support in the protect-generate endpoint.

This script demonstrates how to use different LLM providers (OpenAI, Ollama, Vertex)
via the llm_provider parameter in the API request.
"""

import requests
import json
from typing import Optional

# API Configuration
BASE_URL = "http://localhost:8000"
PROTECT_GENERATE_ENDPOINT = f"{BASE_URL}/api/protect-generate"


def test_protect_generate(
    input_text: str,
    tenant_id: int = 1,
    policy_id: Optional[int] = None,
    llm_provider: Optional[str] = None,
    retrieval_query: Optional[str] = None,
    evidence_payloads: Optional[list] = None,
):
    """
    Test the protect-generate endpoint with a specific LLM provider.
    
    Args:
        input_text: The prompt to send
        tenant_id: Tenant ID (default 1)
        policy_id: Optional policy ID
        llm_provider: LLM provider: 'openai', 'ollama', or 'vertex'
        retrieval_query: Optional RAG retrieval query
        evidence_payloads: Optional evidence chunks for RAG
    """
    payload = {
        "tenant_id": tenant_id,
        "input_text": input_text,
    }
    
    if policy_id:
        payload["policy_id"] = policy_id
    
    if llm_provider:
        payload["llm_provider"] = llm_provider
    
    if retrieval_query:
        payload["retrieval_query"] = retrieval_query
    
    if evidence_payloads:
        payload["evidence_payloads"] = evidence_payloads
    
    print(f"\n{'='*60}")
    print(f"Testing with provider: {llm_provider or 'default (ollama)'}")
    print(f"Input: {input_text[:100]}...")
    print(f"{'='*60}")
    
    try:
        response = requests.post(
            PROTECT_GENERATE_ENDPOINT,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\nAllowed: {result['allowed']}")
            print(f"Risk Score: {result['risk_score']}")
            print(f"Policy Reasons: {result.get('policy_reasons', [])}")
            print(f"Risk Reasons: {result.get('risk_reasons', [])}")
            print(f"\nModel Output Preview: {result['raw_model_output'][:200]}...")
            print(f"Trace ID: {result['trace_id']}")
            
            if result.get('grounded_claims'):
                print(f"\nGrounded Claims: {len(result['grounded_claims'])}")
                for claim in result['grounded_claims'][:3]:
                    print(f"  - {claim['text'][:80]}... (score: {claim['score']:.2f})")
        else:
            print(f"\nError: {response.text}")
    
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to the API server.")
        print("Make sure the backend is running: cd backend && make start")
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")


def main():
    """
    Run tests with different LLM providers.
    """
    print("Multi-Provider LLM Support Test")
    print("=" * 60)
    
    # Test prompt
    prompt = "Write a brief summary of the benefits of renewable energy."
    
    # Test 1: Default provider (Ollama)
    print("\n\n### Test 1: Default Provider (Ollama)")
    test_protect_generate(
        input_text=prompt,
        llm_provider=None,  # Uses default
    )
    
    # Test 2: Explicitly use Ollama
    print("\n\n### Test 2: Explicitly Use Ollama")
    test_protect_generate(
        input_text=prompt,
        llm_provider="ollama",
    )
    
    # Test 3: Use OpenAI
    print("\n\n### Test 3: Use OpenAI")
    print("Note: This requires OPENAI_API_KEY environment variable to be set")
    test_protect_generate(
        input_text=prompt,
        llm_provider="openai",
    )
    
    # Test 4: RAG with evidence and OpenAI
    print("\n\n### Test 4: RAG with Evidence (OpenAI)")
    evidence = [
        {
            "text": "Solar power reduces carbon emissions and helps combat climate change.",
            "source_uri": "https://example.com/renewable-energy",
            "metadata": {"category": "environmental"},
        },
        {
            "text": "Wind energy is cost-effective and creates jobs in local communities.",
            "source_uri": "https://example.com/wind-power",
            "metadata": {"category": "economic"},
        },
    ]
    test_protect_generate(
        input_text=prompt,
        llm_provider="openai",
        retrieval_query="benefits of renewable energy",
        evidence_payloads=evidence,
    )
    
    # Test 5: Vertex AI (if configured)
    print("\n\n### Test 5: Use Vertex AI")
    print("Note: This requires Vertex AI configuration")
    test_protect_generate(
        input_text=prompt,
        llm_provider="vertex",
    )
    
    print("\n\n" + "=" * 60)
    print("Testing Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
