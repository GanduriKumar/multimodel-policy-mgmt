import urllib.request
import json

def check_policy(text):
    """Check if text complies with the policy."""
    url = 'http://localhost:8000/api/protect'
    payload = {
        'tenant_id': 1,
        'policy_id': 1,
        'input_text': text,
        'evidence_types': ["text"]
    }
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result['allowed'], result.get('reasons', [])
    except Exception as e:
        print(f'Error: {e}')
        return False, [str(e)]

# Usage
input_text = input("Enter text to check: ")
allowed, reasons = check_policy(input_text)
if allowed:
    print('✓ Message is safe')
else:
    print('✗ Message blocked:', reasons)