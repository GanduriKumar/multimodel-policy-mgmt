# User Guide: Multimodel Policy Management

Welcome! This guide will help you get the **Multimodel Policy Management** system up and running, even if you're new to programming. We'll walk through everything step-by-step.

---

## Table of Contents

1. [What Is This System?](#what-is-this-system)
2. [What You Need Before Starting](#what-you-need-before-starting)
3. [Step 1: Get the Code](#step-1-get-the-code)
4. [Step 2: Set Up the Backend (The Brains)](#step-2-set-up-the-backend-the-brains)
5. [Step 3: Set Up the Frontend (The Dashboard)](#step-3-set-up-the-frontend-the-dashboard)
6. [Step 4: Create Your First Policy](#step-4-create-your-first-policy)
7. [Step 5: Test the System](#step-5-test-the-system)
8. [How to Provide Evidence (Simple)](#how-to-provide-evidence-simple)
9. [How to View Audits (Simple)](#how-to-view-audits-simple)
10. [Step 6: Connect Your Own Application](#step-6-connect-your-own-application)
11. [Troubleshooting](#troubleshooting)
12. [Next Steps](#next-steps)

---

## What Is This System?

Think of this system as a **safety layer** for AI applications. Here's what it does:

- **Creates Rules (Policies)**: You define what text is allowed and what isn't. For example: "Block any text containing profanity" or "Ensure all responses cite credible sources."
  
- **Checks Text**: Before sending user input to an AI model, the system checks if it follows the rules. Same for AI responses—before showing them to users, the system verifies they're safe.

- **Keeps Records**: Every decision is logged for compliance and auditing. You can prove exactly what was approved, blocked, and why.

- **Works Everywhere**: Once you create a policy, you can use it across all your applications—no need to recreate the same rules in each app.

### Real-World Example

Imagine you run a chatbot for customer support:

1. Customer types: *"Give me the CEO's email"*
2. System checks this against your policy → **BLOCKED** (violates privacy rules)
3. Customer is told: "Sorry, I can't share that information."
4. The decision is logged for compliance.

Now imagine the policy is updated to require responses cite sources:

1. Customer types: *"What's our return policy?"*
2. System allows it ✓
3. AI generates: *"Our return policy is to accept returns within 30 days."*
4. System checks the response → **BLOCKED** (no source cited)
5. The AI is asked to rewrite with a source
6. AI regenerates: *"Per our website, returns are accepted within 30 days."*
7. System checks again → **ALLOWED** ✓
8. Customer sees the response.

---

## What You Need Before Starting

Before you begin, make sure you have these installed on your computer:

### Required Software

1. **Python** (version 3.10 or newer)
   - Download from: https://www.python.org/downloads/
   - After installation, open a terminal and type: `python --version`
   - You should see something like `Python 3.10.x` or higher

2. **Node.js and npm** (version 18 or newer)
   - Download from: https://nodejs.org/
   - After installation, open a terminal and type: `node --version` and `npm --version`
   - You should see version numbers for both

3. **Git** (to download the code)
   - Download from: https://git-scm.com/
   - After installation, open a terminal and type: `git --version`

### Recommended but Optional

- **Visual Studio Code** (a text editor): https://code.visualstudio.com/
- **Postman** (for testing API calls): https://www.postman.com/ (we'll use curl instead for simplicity)

---

## Step 1: Get the Code

This system has two main parts: a backend (the logic) and a frontend (the dashboard).

### For Windows (PowerShell):

```powershell
# Open PowerShell and navigate to where you want the project
cd Documents

# Download the code
git clone https://github.com/your-org/multimodel-policy-mgmt.git

# Enter the folder
cd multimodel-policy-mgmt
```

### For macOS/Linux:

```bash
# Open Terminal and navigate to where you want the project
cd ~/Documents

# Download the code
git clone https://github.com/your-org/multimodel-policy-mgmt.git

# Enter the folder
cd multimodel-policy-mgmt
```

---

## Step 2: Set Up the Backend (The Brains)

The backend is a Python application that handles all the policy logic. Here's how to get it running:

### Windows (PowerShell)

```powershell
# Navigate to the backend folder
cd backend

# Create an isolated Python environment (like a sandbox for your project)
python -m venv .venv

# Activate the environment (you'll see (.venv) in your prompt after this)
.\.venv\Scripts\Activate.ps1

# Install all the packages this system needs
pip install -r requirements.txt

# Set up the database (creates tables for storing policies, decisions, etc.)
python -c "from app.db.base import Base, import_all_models; from app.db.session import engine; import_all_models(); Base.metadata.create_all(bind=engine)"

# Start the backend server
python -m uvicorn app.main:app --reload --port 8000
```

You should see output like:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

**Leave this terminal running!** The backend is now listening for requests.

### macOS/Linux

```bash
# Navigate to the backend folder
cd backend

# Create an isolated Python environment
python -m venv .venv

# Activate the environment
source .venv/bin/activate

# Install all the packages
pip install -r requirements.txt

# Set up the database
python -c "from app.db.base import Base, import_all_models; from app.db.session import engine; import_all_models(); Base.metadata.create_all(bind=engine)"

# Start the backend server
python -m uvicorn app.main:app --reload --port 8000
```

### Verify the Backend Is Running

Open your web browser and go to:
- **Health check**: http://localhost:8000/api/health
- **API Documentation**: http://localhost:8000/docs

You should see a response. The docs page is interactive—you can test API calls right from your browser!

---

## Step 3: Set Up the Frontend (The Dashboard)

The frontend is a web application where you'll see a nice dashboard to manage policies. Open a **new terminal** (keep the backend running in the old one).

### Windows (PowerShell)

```powershell
# Navigate to the frontend folder (from project root)
cd frontend

# Install packages
npm install

# Start the frontend
npm run dev
```

You should see:
```
Local: http://localhost:5173
```

### macOS/Linux

```bash
# Navigate to the frontend folder
cd frontend

# Install packages
npm install

# Start the frontend
npm run dev
```

### Access the Dashboard

Open your web browser and go to:
- **Frontend Dashboard**: http://localhost:5173

You should see a dashboard with navigation options like "Policies," "Protect," "Evidence," and "Audit."

---

## Step 4: Create Your First Policy

A policy is a set of rules. Let's create one to block certain words.

### Via the Dashboard (Easiest)

1. Open your browser to: http://localhost:5173
2. Click on **"Policies"** in the navigation menu
3. Click **"Create New Policy"**
4. Fill in:
   - **Policy Name**: `Content Safety`
   - **Policy Slug**: `content-safety` (no spaces, lowercase)
   - **Description**: `Blocks unsafe content`
   - **Tenant ID**: `1` (for now, use 1)
5. Click **"Create Policy"**

Now you'll create a "version" of this policy (a version is a specific set of rules):

1. Click **"Add Version"**
2. In the version document, add rules like:
   ```json
   {
     "blocked_terms": ["forbidden", "inappropriate"],
     "risk_threshold": 50,
     "required_evidence_types": ["url"]
   }
   ```
   - `blocked_terms`: Words that will block content
   - `risk_threshold`: A sensitivity level (0-100)
   - `required_evidence_types`: Types of evidence (like URLs) that responses should include

3. Click **"Save and Activate"**

Congratulations! You've created your first policy. ✓

### Via Command Line (If You Prefer)

If you're comfortable with the command line, open a new terminal and use these commands:

**Create a policy:**
```bash
curl -X POST http://localhost:8000/api/policies \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": 1,
    "name": "Content Safety",
    "slug": "content-safety",
    "description": "Blocks unsafe content",
    "is_active": true
  }'
```

**Add a version to the policy:**
```bash
curl -X POST http://localhost:8000/api/policies/1/versions \
  -H "Content-Type: application/json" \
  -d '{
    "policy_id": 1,
    "document": {
      "blocked_terms": ["forbidden", "inappropriate"],
      "risk_threshold": 50,
      "required_evidence_types": []
    },
    "is_active": true
  }'
```

---

## Step 5: Test the System

Now let's test that the policy actually works!

### Via the Dashboard

1. Go to http://localhost:5173
2. Click on **"Protect"** in the navigation menu
3. In the test form:
  - **Tenant ID**: `1`
  - **Policy ID**: `1` (tip: see the Policies list to find the ID)
  - **Content to evaluate**: `This is a forbidden word`
  - Click **"Evaluate"**

You should see a result showing **"Not Allowed"** because the word "forbidden" is in your blocked list.

Now try:
   - **Input Text**: `This is a safe sentence`
   - Click **"Check Text"**

This time it should show **"Allowed"** because there are no blocked words.

### Via Command Line

```bash
curl -X POST http://localhost:8000/api/protect \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": 1,
    "policy_id": 1,
    "input_text": "This is a safe sentence",
    "evidence_types": []
  }'
```

You'll see a JSON response like:
```json
{
  "allowed": true,
  "reasons": [],
  "risk_score": 10
}
```

Or if blocked:
```json
{
  "allowed": false,
  "reasons": ["blocked_term:forbidden"],
  "risk_score": 75
}
```

---

## How to Provide Evidence (Simple)

Why evidence matters:
- Your policy can require certain evidence types (for example: url, document, text).
- If those are missing, the request may be denied or marked higher risk (especially in conservative mode).

Two easy ways to provide evidence:

1) Tell the Protect API what kinds of evidence you have
- In the request body, set evidence_types to a list of tags you can provide.
- Example: ["url", "document"]. This satisfies policy checks that only look for the presence of these types.

Example (curl):
```bash
curl -X POST http://localhost:8000/api/protect \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": 1,
    "policy_id": 1,
    "input_text": "Write a short story about a library.",
    "evidence_types": ["text"]
  }'
```

2) Store actual evidence records (optional but useful for audits)
- Use the Evidence API to save a piece of evidence (like a URL or document) with optional metadata.
- Later, you can point back to these records in your own app logic.

Create evidence (curl):
```bash
curl -X POST "http://localhost:8000/api/evidence?tenant_id=1" \
  -H "Content-Type: application/json" \
  -d '{
    "evidence_type": "url",
    "source": "https://example.com/policy",
    "description": "Official policy page",
    "content": "Optional raw text used to compute a content hash",
    "metadata": {"topic": "returns"}
  }'
```

Notes:
- evidence_types in /api/protect is about “what kind” you provided, not linking to a specific record.
- If your policy requires certain types (like ["url", "document"]) and you send none, the system will add reasons like "missing_evidence:url" and may deny the request.
- The dashboard Protect page has an “Evidence Types (CSV)” field; enter values like: url,document

---

## How to View Audits (Simple)

The system logs each request and decision so you can review what happened and why.

Easiest: Use the Dashboard
1) Open http://localhost:5173
2) Click "Audit"
3) You’ll see a list of recent requests, their decision (Allowed/Denied), and risk score
4) Click into a decision to see details and grouped reasons (Policy vs Risk)

APIs (for scripts and exports):

- List recent requests (with snapshot):
```bash
curl "http://localhost:8000/api/audit/requests?tenant_id=1&offset=0&limit=50"
```

- Get full decision detail by decision id (or by request id as fallback in some repos):
```bash
curl "http://localhost:8000/api/audit/decisions/123"
```

Interpreting reasons:
- Policy reasons: blocked_term:..., missing_evidence:..., pii_denied:...
- Risk reasons: prompt_injection:..., pii_like:..., secret_like:..., evidence_missing, risk_above_threshold:...
- If conservative mode is on, you may also see:
  - conservative_risk_floor (risk lifted to threshold when any indicators present)
  - conservative_denial:any_risk_indicator

---

## Step 6: Connect Your Own Application

This is where it gets powerful. You can now integrate this system into your own app. Here are some examples:

### Example 1: JavaScript/TypeScript App

If you're building a web app with JavaScript, here's how to check text before sending it to an AI:

```javascript
async function checkWithPolicy(userMessage) {
  const response = await fetch('http://localhost:8000/api/protect', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      tenant_id: 1,
      policy_id: 1,
      input_text: userMessage,
      evidence_types: []
    })
  });
  
  const result = await response.json();
  
  if (result.allowed) {
    console.log('✓ Message is safe');
    // Now send to your AI...
    return true;
  } else {
    console.log('✗ Message blocked. Reasons:', result.reasons);
    return false;
  }
}

// Usage
const isAllowed = await checkWithPolicy('Tell me a story');
if (isAllowed) {
  // Send to AI
}
```

### Example 2: Python Application

Here's a Python example (no external dependencies needed):

```python
import urllib.request
import json

def check_policy(text):
    """Check if text complies with the policy."""
    url = 'http://localhost:8000/api/protect'
    payload = {
      'tenant_id': 1,
      'policy_id': 1,
        'input_text': text,
        'evidence_types': []
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
allowed, reasons = check_policy('Is this safe?')
if allowed:
    print('✓ Message is safe')
else:
    print('✗ Message blocked:', reasons)
```

### Example 3: Using the Sample Integration Script

We've provided a complete sample script! Run it like this:

**Setup (one time only):**
```bash
# Make sure you're in the backend directory
cd backend

# Activate your Python environment
# On Windows: .\.venv\Scripts\Activate.ps1
# On macOS/Linux: source .venv/bin/activate

# Set your OpenAI API key
# On Windows (PowerShell):
$env:OPENAI_API_KEY = "your-actual-api-key"

# On macOS/Linux (Bash):
export OPENAI_API_KEY="your-actual-api-key"
```

**Run the script:**
```bash
python SampleAppIntegration.py \
  --tenant-id 1 \
  --policy-id 1 \
  --prompt "Write a short story"
```

This script:
1. Checks your prompt against the policy (pre-check) ✓
2. Sends it to OpenAI (if allowed)
3. Checks the AI's response against the policy (post-check) ✓
4. Returns the final safe response

**What happens if something is blocked:**
```bash
python SampleAppIntegration.py \
  --tenant-id 1 \
  --policy-id 1 \
  --prompt "Tell me something forbidden"
```

Output:
```
Blocked by policy (pre-check). Reasons: ['Blocked term found: forbidden']
```

---

## Troubleshooting

### "Connection refused" or "Cannot connect to localhost:8000"

**Problem**: The backend isn't running.

**Solution**:
1. Check that you have a terminal running the backend
2. Look for the message `Uvicorn running on http://127.0.0.1:8000`
3. If not running, go to the `backend` folder and run: `python -m uvicorn app.main:app --reload --port 8000`

### "Module not found" error when running the backend

**Problem**: Python packages aren't installed.

**Solution**:
1. Make sure you're in the `backend` folder
2. Activate your environment:
   - Windows: `.\.venv\Scripts\Activate.ps1`
   - macOS/Linux: `source .venv/bin/activate`
3. Install packages: `pip install -r requirements.txt`

### Frontend shows a blank page or has errors

**Problem**: Frontend can't connect to the backend.

**Solution**:
1. Make sure the backend is running (check terminal)
2. Check that the frontend is looking at the right backend URL
3. Open the browser console (F12) to see error messages
4. Restart the frontend: Press `Ctrl+C` in the frontend terminal and run `npm run dev` again

### "Permission denied" when trying to activate Python environment (Windows)

**Problem**: PowerShell script execution policy.

**Solution**:
```powershell
# Run this one time
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then try activating again
.\.venv\Scripts\Activate.ps1
```

### Policy creation fails with "400 Bad Request"

**Problem**: Missing or incorrect field in the JSON.

**Solution**:
- Make sure `policy_id` in the request matches the path
- All required fields are present: `policy_id`, `document`
- JSON formatting is correct (use a JSON validator online if unsure)

### "OPENAI_API_KEY not set" error when running the sample script

**Problem**: Your OpenAI API key isn't configured.

**Solution**:
1. Get a key from https://platform.openai.com/api-keys
2. Set it in your environment:
   - Windows (PowerShell): `$env:OPENAI_API_KEY = "sk-..."`
   - macOS/Linux (Bash): `export OPENAI_API_KEY="sk-..."`

---

## Next Steps

Congratulations! You've successfully deployed and tested the system. Here's what you can do next:

### 1. **Explore the Audit Dashboard**
   - Go to http://localhost:5173 → Click "Audit"
   - See all decisions made by the system
   - Filter by date, policy, or allowed/blocked status
   - Export results for compliance reporting

### 2. **Create More Policies**
   - Create a policy for PII (Personally Identifiable Information)
   - Create a policy for source citation
   - Create a policy for tone/style guidelines
   - Policies can be versioned and activated independently

### 3. **Integrate with Your Existing Apps**
   - Identify where your app calls an LLM or processes user input
   - Add a call to `/api/protect` before sending text to the LLM
   - Optionally add another check after the LLM response
   - See examples in [Step 6](#step-6-connect-your-own-application)

### 4. **Deploy to Production**
   - This guide uses "localhost" (your computer)
   - To use this system in production, you'll need to deploy it to a server
   - See [Deploy Options](#production-deployment-quick-reference) below

### 5. **Read More Details**
   - Backend details: See [backend/Deploy&Integrate.md](backend/Deploy&Integrate.md)
   - Policy creation: See [backend/CreatePolicy.md](backend/CreatePolicy.md)
   - API documentation: Visit http://localhost:8000/docs (interactive)

### 6. **Enable Governance Ledger (Advanced)**
   - This creates a tamper-evident record of all decisions
   - Great for compliance and auditing
   - Documentation: See the main [README.md](README.md)

---

## Production Deployment Quick Reference

When you're ready to move beyond your computer, here are the quickest ways to deploy:

### Option A: Docker (Recommended)

```bash
# Build the container
docker build -t policy-backend -f backend/Dockerfile .

# Run it
docker run -d --name policy-backend \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/policydb \
  -e ALLOW_ORIGINS=https://your-frontend.com \
  policy-backend
```

### Option B: Cloud Platforms

**Render, Fly.io, or Heroku:**
- Push to GitHub
- Connect your repository to the platform
- Set environment variables in the dashboard
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

**Azure App Service, AWS Lambda, or Google Cloud Run:**
- Similar process—each has its own deployment wizard
- Follow the platform's documentation

### Option C: On Your Server

```bash
# SSH into your server
ssh user@your-server.com

# Clone the repo
git clone https://github.com/your-org/multimodel-policy-mgmt.git
cd multimodel-policy-mgmt/backend

# Setup (as before)
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Use a production WSGI server
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app.main:app
```

---

## FAQ

**Q: Can I use this system with multiple different LLM providers (OpenAI, Claude, etc.)?**

A: Yes! The system is provider-agnostic. You check text before sending it to any LLM. The backend doesn't call the LLM directly unless you use the `/api/protect-generate` endpoint.

**Q: What if I want to block text but not tell the user why?**

A: You control the response. The API returns a `reasons` list—you can show it, hide it, or show a generic message like "This request cannot be processed."

**Q: Can I have different policies for different users or teams?**

A: Yes! That's where "tenants" come in. Each organization or department is a tenant. Policies are tenant-specific. Create multiple policies and assign them to different tenants.

**Q: Is my data stored locally?**

A: By default, yes—in a SQLite database on your computer. In production, you can use PostgreSQL or other databases by changing the `DATABASE_URL` environment variable.

**Q: Can I export the audit logs?**

A: Yes! The Audit page in the dashboard has an export feature. You can also use the API endpoint `/api/audit/export`.

**Q: What if the backend is down? Does my app break?**

A: That depends on how you implement it. You can:
- Add error handling to gracefully degrade (warn user, continue without checks)
- Use a circuit breaker pattern (fall back after N failures)
- Set up backup/redundancy for the backend itself

**Q: How do I update a policy without affecting current users?**

A: Create a new version of the policy. The old version stays active until you explicitly switch to the new one. You can even run both in parallel for testing.

---

## Getting Help

- **Stuck?** Check the [Troubleshooting](#troubleshooting) section above
- **API Questions?** Visit http://localhost:8000/docs for interactive documentation
- **Found a bug?** Open an issue on GitHub
- **Want to contribute?** See the main [README.md](README.md) for contribution guidelines

---

## Summary

You now have:
1. ✓ A working backend (policy engine) running on port 8000
2. ✓ A working frontend dashboard running on port 5173
3. ✓ Created your first policy
4. ✓ Tested the policy with sample text
5. ✓ Examples of how to integrate into your own applications

The system is ready to protect your AI applications! Start integrating it into your apps using the examples in [Step 6](#step-6-connect-your-own-application).

---

**Happy policy management! 🚀**
