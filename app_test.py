import urllib.request
import json
from typing import Any, Dict

BACKEND_URL = 'http://localhost:8000'

def check_policy(text: str, *, tenant_id: int = 1, policy_id: int = 1, evidence_ids: str = ""):
    """Check if text complies with the policy using numeric policy_id and optional evidence_ids."""
    url = BACKEND_URL.rstrip('/') + '/api/protect'
    payload: Dict[str, Any] = {
        'tenant_id': int(tenant_id),
        'policy_id': int(policy_id),
        'input_text': text,
    }
    # Pass evidence IDs in metadata to let the backend derive types; omit if empty
    ids = [int(x) for x in evidence_ids.split(',') if x.strip().isdigit()]
    if ids:
        payload['metadata'] = { 'evidence_ids': ids }

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get('allowed', False), result.get('reasons', []), result.get('risk_score', None)
    except Exception as e:
        print(f'Error: {e}')
        return False, [str(e)], None

if __name__ == '__main__':
    input_text = input("Enter text to check: ")
    allowed, reasons, score = check_policy(input_text)
    if allowed:
        print(f'✓ Allowed (risk={score})')
    else:
        print(f'✗ Denied (risk={score}) Reasons:', reasons)