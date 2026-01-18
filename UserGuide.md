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
  - [Add Evidence via the API](#add-evidence-via-the-api)
  - [Link Evidence with Policies](#link-evidence-with-policies)
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
  - Tenant is fixed to 1 in the UI (single-tenant mode)
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

### What is Evidence and Why It Matters

Think of evidence like showing your work in math class. When your AI system gives an answer, you want to prove:
- **Where the information came from** (like citing sources in a research paper)
- **What data was used** to generate the response
- **That the response is grounded in real facts**, not made up

**Why this matters:**
- Your policy can require certain types of evidence (for example: url, document, text)
- If evidence is missing, the request may be blocked or flagged as high-risk
- For compliance (like EU AI Act), you need to show auditors that your AI's answers are backed by real sources

**Important:** Evidence is NOT automatically collected. You must provide it yourself—either through the web dashboard, command-line tools, or by calling the API directly.

---

### Three Ways to Provide Evidence

There are three methods, from simplest to most powerful:

#### **Method 1: Evidence Types (Simplest—Just Tags)**

This is like checking boxes: "I have a URL" or "I have a document." You're just telling the system what **kinds** of evidence you have, without providing the actual content.

**When to use this:**
- Quick testing
- Your policy just needs to know evidence exists (not the actual content)
- You're getting started and want something simple

**Example using the Web Dashboard:**

1. Go to the **Protect** page in the dashboard (http://localhost:5173/protect)
2. Fill in:
   - **Policy:** Select your policy from the dropdown
   - **Input Text:** Type or paste your text (e.g., "What is the capital of France?")
3. Scroll down to **Advanced Options** and click to expand
4. In the **Evidence Types (CSV)** field, type: `url,text`
5. Click **Check Protection**

This tells the system: "I have evidence of type 'url' and 'text' available."

**Example using curl (command-line):**

```bash
curl -X POST http://localhost:8000/api/protect \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": 1,
    "policy_id": 1,
    "input_text": "What is the capital of France?",
    "evidence_types": ["url", "text"]
  }'
```

**Example using the Python test script:**

```bash
# Make sure you're in the backend folder
cd backend

# Activate your environment first
.\.venv\Scripts\Activate.ps1  # Windows
# source .venv/bin/activate    # macOS/Linux

# Run with evidence types
python SampleAppIntegration_v2.py \
  --mode sandwich \
  --tenant-id 1 \
  --policy-id 1 \
  --prompt "What is the capital of France?" \
  --evidence-types "url,text"
```

---

#### **Method 2: Evidence IDs (Reference Pre-Stored Evidence)**

This is like referencing footnotes in a book. You first save evidence records in the database, then later you can reference them by ID number.

**When to use this:**
- You want to reuse the same evidence multiple times
- You need to track exactly what documents/sources were used
- You want a permanent audit trail of your evidence

**Step 1: Create an evidence record**

Using the Evidence API (curl):
```bash
curl -X POST "http://localhost:8000/api/evidence?tenant_id=1" \
  -H "Content-Type: application/json" \
  -d '{
    "evidence_type": "url",
    "source": "https://en.wikipedia.org/wiki/Paris",
    "description": "Wikipedia article about Paris",
    "content": "Paris is the capital and largest city of France.",
    "metadata": {"topic": "geography", "verified": true}
  }'
```

This returns something like:
```json
{
  "id": 42,
  "evidence_type": "url",
  "source": "https://en.wikipedia.org/wiki/Paris",
  ...
}
```

**Step 2: Use the evidence ID when calling Protect**

Now you can reference this evidence by its ID (42):

```bash
python SampleAppIntegration_v2.py \
  --mode sandwich \
  --tenant-id 1 \
  --policy-id 1 \
  --prompt "What is the capital of France?" \
  --evidence-ids "42"
```

You can reference multiple IDs: `--evidence-ids "42,43,44"`

**Note:** This method requires using the test script—the web dashboard doesn't currently support evidence IDs directly.

---

#### **Method 3: Evidence Payloads (Most Powerful—Inline Sources)**

This is the most complete method. You provide the actual text content AND the source information all at once. This is perfect for:
- Showing exactly what text was used to generate an answer
- Providing multiple sources that back up a response
- RAG (Retrieval-Augmented Generation) systems where you retrieve documents and want to prove what was retrieved

**When to use this:**
- You're using RAG (retrieving documents from a database)
- You want to show the exact text snippets used
- You need complete evidence for compliance audits
- You want to see "grounded claims" analysis (which parts of the response are supported by evidence)

**Example using the Web Dashboard:**

1. Go to the **Protect** page
2. Fill in your **Policy** and **Input Text**
3. Scroll to **Advanced Options** → **Evidence Sources**
4. Click **Show Evidence Sources**
5. Click **Add Source**
6. Fill in:
   - **Source Text:** The actual content (e.g., "Paris is the capital of France, located on the Seine River.")
   - **Source URI:** Where it came from (e.g., "https://en.wikipedia.org/wiki/Paris")
7. Click **Add Source** again if you have more sources
8. Click **Check Protection**

Now the system will:
- Check if your response is supported by these sources
- Show you which claims are grounded (backed by evidence) and which aren't
- Store the evidence trail for audit purposes

**Example using curl:**

```bash
curl -X POST http://localhost:8000/api/protect \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": 1,
    "policy_id": 1,
    "input_text": "What is the capital of France?",
    "evidence_payloads": [
      {
        "text": "Paris is the capital and largest city of France.",
        "source_uri": "https://en.wikipedia.org/wiki/Paris",
        "metadata": {"retrieval_score": 0.95}
      },
      {
        "text": "The city of Paris is located on the Seine River in northern France.",
        "source_uri": "https://britannica.com/place/Paris",
        "metadata": {"retrieval_score": 0.89}
      }
    ]
  }'
```

**Example using the Python test script:**

```bash
python SampleAppIntegration_v2.py \
  --mode sandwich \
  --tenant-id 1 \
  --policy-id 1 \
  --prompt "What is the capital of France?" \
  --evidence-source "Paris is the capital of France|https://en.wikipedia.org/wiki/Paris" \
  --evidence-source "Paris is on the Seine River|https://britannica.com/place/Paris"
```

The format for `--evidence-source` is: `"actual text content|source URL"`

You can add as many `--evidence-source` arguments as you want—each one adds another piece of evidence.

---

### Viewing Evidence in Audit Logs

After you provide evidence and run a protection check, you can see the evidence in the **Audit** page:

1. Go to **Audit** (http://localhost:5173/audit)
2. Find your recent decision in the list
3. Click on it to see the details
4. Scroll down to the **Evidence Sources** section

You'll see a table showing:
- **Source #**: The number of each evidence source
- **URI**: Where it came from (clickable link)
- **Text Preview**: The first 100 characters of the evidence text

This is your audit trail—proof of what evidence was used to support the AI's response.

---

### Quick Reference Comparison

| Method | Complexity | What You Provide | Use Case |
|--------|-----------|------------------|----------|
| **Evidence Types** | Simple | Just tags like "url", "text" | Quick checks, policy compliance testing |
| **Evidence IDs** | Medium | Reference numbers to pre-stored evidence | Reusable evidence, permanent records |
| **Evidence Payloads** | Advanced | Full text + source URLs | RAG systems, compliance audits, grounded claims |

---

### Troubleshooting

**"Missing evidence" error:**
- Check if your policy has `required_evidence_types` set (e.g., `["url"]`)
- Make sure you're providing matching evidence types
- Example: If policy requires `["url", "document"]`, provide `--evidence-types "url,document"`

**"Evidence not showing in Audit page:"**
- Make sure you used **Method 3 (Evidence Payloads)**—only payloads are displayed in the audit UI
- Evidence types and IDs are stored but not shown in the sources table

**"How do I know what evidence my policy requires?"**
- Go to the Policies page
- Click on your policy to see details
- Look for the `required_evidence_types` field
- If it's empty (`[]`), no evidence is required

### Add Evidence via the API

Evidence ingestion is available via the API today. Use the curl examples above to store and fetch evidence.

Tip: When evaluating in Protect, type the matching tags into "Evidence Types (CSV)" (e.g., url,document). This signals to the policy engine that the required kinds of evidence are present.


---

## Step 4B: Advanced Policy Configuration (For Regulatory Compliance)

So far, we've created simple policies with basic rules like blocked terms and risk thresholds. But what if you need to meet regulatory requirements like the EU AI Act, NIST AI Risk Management Framework, or privacy regulations?

This section shows you how to configure **comprehensive policies** that help your organization stay compliant. Don't worry—we'll explain everything in simple terms!

### Why Regulatory Compliance Configuration Matters

Think of it this way:
- **Basic policy** = A simple checklist ("Don't say bad words")
- **Compliance-ready policy** = A complete audit trail ("Here's how we tested our AI, what data we use, how we protect privacy, and who's responsible")

When regulators or auditors ask questions like "How do you ensure your AI is safe?" or "What personal data does your system process?", you'll have documented answers.

### What You're Configuring

When you create an advanced policy, you'll fill in information across four main areas:

1. **EU AI Act Configuration**: Requirements for AI systems used in the European Union
2. **NIST AI Risk Management Framework**: Best practices for identifying and managing AI risks
3. **NIST Privacy Framework**: How you protect personal information
4. **PII (Personal Information) Rules**: Automatically detect and protect sensitive data like emails, phone numbers, and credit cards

### How to Create an Advanced Policy

There are two ways to create a comprehensive policy:

#### Option 1: Using the Sample Script (Easiest!)

We've created a ready-to-use script that sets up a complete compliance-ready policy:

```bash
# Make sure you're in the backend folder
cd backend

# Activate your Python environment
# Windows: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate

# Run the script
python create_sample_policy.py
```

This creates a policy (ID=1, Version=2) with **all** compliance fields already filled in. You can then customize it through the API or by editing the script.

#### Option 2: Creating via API (For Custom Policies)

If you want to create your own policy from scratch, use the `/api/policies/{policy_id}/versions` endpoint. Below, we'll explain each section so you know what to include.

### Understanding PII Rules

**What is PII?** PII stands for "Personally Identifiable Information"—things like:
- Email addresses (test@example.com)
- Social Security Numbers (123-45-6789)
- Credit card numbers
- Phone numbers

**Why configure PII rules?** You can automatically protect this sensitive information by:
- **Blocking** the request entirely if PII is detected
- **Masking** the PII (turn "test@example.com" into "t***@example.com")
- **Redacting** the PII (remove it completely)

**Example PII Rules Configuration:**

```json
{
  "pii_rules": {
    "email": {
      "action": "mask",
      "enabled": true,
      "description": "Email addresses are masked (partially hidden)"
    },
    "ssn": {
      "action": "block",
      "enabled": true,
      "description": "Social Security Numbers completely block the request"
    },
    "credit_card": {
      "action": "block",
      "enabled": true,
      "description": "Credit card numbers completely block the request"
    },
    "phone": {
      "action": "mask",
      "enabled": true,
      "description": "Phone numbers are masked"
    }
  }
}
```

**What this means in plain English:**
- If someone types "My email is john@example.com", the system will mask it to "My email is j***@example.com"
- If someone types "My SSN is 123-45-6789", the request is **blocked** immediately for security
- You stay in control: enable/disable rules or change actions as needed

### Understanding EU AI Act Configuration

The EU AI Act requires organizations using AI in Europe to document how their systems work and ensure they're safe. Here's what you need to configure:

**1. Risk Management System**
*What it is:* How you identify and reduce risks in your AI system.
*Example:* "We test our AI monthly, review decisions quarterly, and maintain a risk register."

**2. Data Quality Measures**
*What it is:* How you ensure the data you use is accurate and appropriate.
*Example:* "We validate training data for accuracy, remove duplicates, and check for bias monthly."

**3. Technical Documentation**
*What it is:* A description of how your AI system works.
*Example:* "GPT-4-based chatbot for customer support; uses company knowledge base; filters harmful content."

**4. Record-Keeping Practices**
*What it is:* How you log and store AI decisions for auditing.
*Example:* "All decisions logged to secure database; retained for 3 years; accessible to compliance team."

**5. Transparency Measures**
*What it is:* How you inform users they're interacting with AI.
*Example:* "Chat interface displays 'AI Assistant' badge; users can request human agent anytime."

**6. Human Oversight Mechanisms**
*What it is:* How humans monitor and can override the AI.
*Example:* "Support manager reviews flagged decisions daily; emergency stop button available."

**7. Accuracy and Robustness Testing**
*What it is:* How you test that your AI works correctly and handles errors gracefully.
*Example:* "Monthly accuracy tests against 1000 sample queries; 95% accuracy threshold; error handling for network failures."

**Example EU AI Act Configuration:**

```json
{
  "eu_ai_act_config": {
    "risk_management_system": "Quarterly risk assessments; incident tracking; monthly policy reviews",
    "data_quality_measures": "Data validation pipelines; bias detection; monthly quality audits",
    "technical_documentation": "GPT-4 chatbot with RAG; content filtering; evidence-based responses",
    "record_keeping_practices": "All decisions logged with tamper-evident hashing; 3-year retention",
    "transparency_measures": "AI disclosure badges; user notification; opt-out available",
    "human_oversight_mechanisms": "Daily review queue; escalation paths; emergency stop procedures",
    "accuracy_robustness_testing": "Monthly accuracy tests (95% threshold); error handling; fallback mechanisms"
  }
}
```

### Understanding NIST AI Risk Management Framework

The NIST AI RMF organizes AI risk management into four functions: **GOVERN**, **MAP**, **MEASURE**, and **MANAGE**. Here's what each means:

**GOVERN Function** (Who's in charge and what are the rules?)

1. **Governance Structures**: Who makes decisions about AI safety?
   - *Example:* "AI Safety Board meets monthly; CTO has final approval; documented in AI charter"

2. **Risk Management Policies**: What are your organization's AI risk policies?
   - *Example:* "Zero tolerance for bias; monthly risk reviews; escalation for high-risk decisions"

3. **Accountability Mechanisms**: Who's responsible when something goes wrong?
   - *Example:* "VP of Engineering accountable for AI safety; incident response team on call 24/7"

**MAP Function** (Understanding your AI system and its context)

1. **System Context Documentation**: Where and how is the AI used?
   - *Example:* "Customer support chat; processes 10K queries/day; integrates with CRM"

2. **Risk Identification Process**: How do you find potential risks?
   - *Example:* "Monthly threat modeling; user feedback analysis; incident reviews"

3. **Impact Assessment**: What could go wrong and how bad would it be?
   - *Example:* "Low impact: unhelpful response; High impact: biased decision; Critical: data leak"

**MEASURE Function** (How do you know it's working?)

1. **Performance Metrics**: What numbers tell you the AI is doing well?
   - *Example:* "95% accuracy; <2% harmful content; <1% PII leaks; 98% user satisfaction"

2. **Testing Validation Methods**: How do you test the AI?
   - *Example:* "1000-query test suite monthly; red team testing quarterly; A/B testing for changes"

3. **Monitoring Continuous Assessment**: How do you keep watching it?
   - *Example:* "Real-time dashboards; daily reports; alerts for anomalies; weekly team reviews"

**MANAGE Function** (What do you do about risks?)

1. **Risk Response Plans**: What's your plan when you find a risk?
   - *Example:* "Low risk: Log and review; Medium: Immediate investigation; High: Disable feature"

2. **Incident Management**: What happens when something goes wrong?
   - *Example:* "24/7 on-call; incident playbooks; post-mortem required; user notification protocols"

3. **Continuous Improvement**: How do you get better over time?
   - *Example:* "Monthly retrospectives; policy updates based on incidents; quarterly training for team"

**Example NIST AI RMF Configuration:**

```json
{
  "nist_ai_rmf_config": {
    "governance_structures": "AI Safety Board (monthly); CTO approval required; documented charter",
    "risk_management_policies": "Zero-tolerance for bias; monthly risk reviews; high-risk escalation",
    "accountability_mechanisms": "VP Engineering accountable; 24/7 incident response; clear escalation paths",
    "system_context_documentation": "Customer support chatbot; 10K queries/day; CRM integration",
    "risk_identification_process": "Monthly threat modeling; user feedback analysis; incident post-mortems",
    "impact_assessment": "Low: unhelpful response; High: biased decision; Critical: data breach",
    "performance_metrics": "95% accuracy; <2% harmful content; <1% PII leaks; 98% satisfaction",
    "testing_validation_methods": "1K-query test suite monthly; quarterly red team; A/B testing",
    "monitoring_continuous_assessment": "Real-time dashboards; daily reports; anomaly alerts; weekly reviews",
    "risk_response_plans": "Low: log; Medium: investigate; High: disable; Critical: full shutdown",
    "incident_management": "24/7 on-call; playbooks ready; post-mortems required; user notifications",
    "continuous_improvement": "Monthly retros; policy updates; quarterly team training; feedback loops"
  }
}
```

### Understanding NIST Privacy Framework

The NIST Privacy Framework helps you protect personal information. It's organized into five functions:

**IDENTIFY-P** (What personal data do you handle?)

1. **Data Processing Inventory**: What personal data does your system use?
   - *Example:*
     ```json
     {
       "data_types": ["email", "name", "chat_history"],
       "purposes": ["customer support", "analytics"],
       "retention": "3 years"
     }
     ```

2. **Privacy Governance Policies**: What are your privacy rules?
   - *Example:* "GDPR compliant; data minimization; user consent required; privacy-by-design"

3. **Risk Assessment Process**: How do you find privacy risks?
   - *Example:* "Quarterly privacy impact assessments; automated PII scanning; user rights reviews"

**GOVERN-P** (Who manages privacy?)

1. **Privacy Oversight Roles**: Who's in charge of privacy?
   - *Example:* "Data Protection Officer (DPO); Privacy team; quarterly board reports"

2. **Compliance Frameworks**: What privacy laws do you follow?
   - *Example:* "GDPR (EU); CCPA (California); HIPAA (healthcare); regular compliance audits"

**CONTROL-P** (How do you protect the data?)

1. **Data Minimization Practices**: Do you only collect what you need?
   - *Example:* "Only collect email for support tickets; automatic chat deletion after 90 days"

2. **Access Controls**: Who can see personal data?
   - *Example:* "Role-based access; encrypted at rest; audit logs; annual access reviews"

3. **PII Protection Mechanisms**: How do you keep personal data safe?
   - *Example:* "AES-256 encryption; automatic masking; PII detection in queries; secure deletion"

**PROTECT-P** (Preventing privacy problems)

1. **Data Security Measures**: How do you prevent data breaches?
   - *Example:* "End-to-end encryption; regular pen testing; intrusion detection; backups encrypted"

2. **Breach Response Plans**: What happens if data leaks?
   - *Example:* "72-hour notification; incident response team; user notification; regulatory reporting"

**RESPOND-P** (Handling privacy incidents)

1. **Incident Management Procedures**: What's your privacy incident plan?
   - *Example:* "24/7 hotline; investigation within 24h; containment procedures; affected user notification"

**Example NIST Privacy Configuration:**

```json
{
  "nist_privacy_config": {
    "data_processing_inventory": {
      "data_types": ["email", "name", "chat_history", "session_data"],
      "purposes": ["customer_support", "quality_improvement", "compliance"],
      "retention": "3 years for audit; then secure deletion"
    },
    "privacy_governance_policies": "GDPR compliant; data minimization; explicit consent; privacy-by-design",
    "privacy_risk_assessment": "Quarterly PIAs; automated PII detection; user rights impact analysis",
    "privacy_oversight_roles": "Data Protection Officer; Privacy Team; quarterly board reviews",
    "compliance_frameworks": "GDPR (EU); CCPA (California); annual compliance audits",
    "data_minimization_practices": "Collect only necessary data; 90-day auto-delete for chat; no tracking",
    "access_controls": "Role-based access; encrypted at rest/transit; annual access reviews; audit logs",
    "pii_protection_mechanisms": "AES-256 encryption; automatic PII masking; detection in queries; secure deletion",
    "data_security_measures": "End-to-end encryption; quarterly pen tests; IDS/IPS; encrypted backups",
    "breach_response_plans": "72h GDPR notification; incident response team; user alerts; regulatory filings",
    "incident_management_procedures": "24/7 hotline; 24h investigation SLA; containment playbooks; user notification"
  }
}
```

### Putting It All Together: Complete Policy Example

Here's what a full compliance-ready policy looks like when you send it to the API:

```json
{
  "policy_id": 1,
  "version": 2,
  "document": {
    "description": "Comprehensive compliance-ready policy",
    "blocked_terms": ["weapon", "violence", "illegal"],
    "risk_threshold": 75,
    "required_evidence_types": ["url", "document"],
    
    "pii_rules": {
      "email": {"action": "mask", "enabled": true},
      "ssn": {"action": "block", "enabled": true},
      "credit_card": {"action": "block", "enabled": true},
      "phone": {"action": "mask", "enabled": true}
    },
    
    "eu_ai_act_config": {
      "risk_management_system": "Quarterly risk assessments with documented mitigation strategies",
      "data_quality_measures": "Automated data validation and monthly bias audits",
      "technical_documentation": "GPT-4 with content filtering and evidence-based retrieval",
      "record_keeping_practices": "Tamper-evident logging with 3-year retention",
      "transparency_measures": "Clear AI disclosure and user notification",
      "human_oversight_mechanisms": "Daily review queue with escalation procedures",
      "accuracy_robustness_testing": "Monthly accuracy tests with 95% threshold"
    },
    
    "nist_ai_rmf_config": {
      "governance_structures": "AI Safety Board with monthly meetings",
      "risk_management_policies": "Zero-tolerance for bias; documented escalation",
      "accountability_mechanisms": "VP Engineering accountable; 24/7 response",
      "system_context_documentation": "Customer support chatbot processing 10K queries/day",
      "risk_identification_process": "Monthly threat modeling and user feedback analysis",
      "impact_assessment": "Tiered impact levels from low to critical",
      "performance_metrics": "95% accuracy, <2% harmful content, 98% satisfaction",
      "testing_validation_methods": "1K-query test suite monthly, quarterly red team",
      "monitoring_continuous_assessment": "Real-time dashboards with anomaly detection",
      "risk_response_plans": "Tiered response from logging to full shutdown",
      "incident_management": "24/7 on-call with documented playbooks",
      "continuous_improvement": "Monthly retrospectives and quarterly training"
    },
    
    "nist_privacy_config": {
      "data_processing_inventory": {
        "data_types": ["email", "name", "chat_history"],
        "purposes": ["customer_support", "quality_improvement"],
        "retention": "3 years then secure deletion"
      },
      "privacy_governance_policies": "GDPR compliant with data minimization",
      "privacy_risk_assessment": "Quarterly privacy impact assessments",
      "privacy_oversight_roles": "Data Protection Officer with board reporting",
      "compliance_frameworks": "GDPR, CCPA with annual audits",
      "data_minimization_practices": "90-day auto-delete for non-essential data",
      "access_controls": "Role-based access with annual reviews",
      "pii_protection_mechanisms": "AES-256 encryption and automatic masking",
      "data_security_measures": "End-to-end encryption with quarterly pen tests",
      "breach_response_plans": "72-hour notification with incident response team",
      "incident_management_procedures": "24/7 hotline with 24-hour investigation SLA"
    }
  }
}
```

### Testing Your Compliance-Ready Policy

After creating your advanced policy, test it to ensure PII protection works:

```bash
curl -X POST "http://localhost:8000/api/protect" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": 1,
    "policy_id": 1,
    "input_text": "My email is test@example.com and my SSN is 123-45-6789",
    "evidence_types": []
  }'
```

**Expected result:** The request should be **BLOCKED** because SSN detection is enabled with action "block".

### Generating Compliance Reports

Once your policy is configured, you can generate compliance reports:

```bash
# Generate EU AI Act compliance report
curl "http://localhost:8000/api/reports/regulatory/eu-ai-act?tenant_id=1&start_date=2024-01-01&format=html" > eu_compliance.html

# Generate NIST AI RMF report
curl "http://localhost:8000/api/reports/regulatory/nist-ai-rmf?tenant_id=1&start_date=2024-01-01&format=html" > nist_rmf.html

# Generate NIST Privacy report
curl "http://localhost:8000/api/reports/regulatory/nist-privacy?tenant_id=1&start_date=2024-01-01&format=html" > nist_privacy.html
```

Open the HTML files in your browser to see your compliance scores and detailed assessments.

### Tips for Maintaining Compliance

1. **Start with the sample policy**: Run `python create_sample_policy.py` to get a working template
2. **Customize gradually**: Don't try to fill everything at once; start with what's most relevant to your organization
3. **Review quarterly**: Set calendar reminders to update your documentation every 3 months
4. **Test regularly**: Run compliance reports monthly to catch gaps early
5. **Document everything**: The more detail you provide, the better your compliance scores

---

### Link Evidence with Policies

Linking helps audits and reporting. There are two ways:

1) From your own app or scripts:
   - Enter Policy ID (see Policies page for the ID)
   - Optionally enter the active Policy Version ID (see the Versions panel under the policy)

2) Via the API (explicit linking):
```bash
curl -X POST "http://localhost:8000/api/evidence?tenant_id=1" \
  -H "Content-Type: application/json" \
  -d '{
    "evidence_type": "document",
    "description": "Return policy PDF",
    "content": "...optional text...",
    "policy_id": 1,
    "policy_version_id": 3,
    "metadata": {"source": "internal"}
  }'
```

Important:
- Linking an evidence record to a policy does not automatically attach it to /api/protect calls. Today, Protect uses evidence_types to verify presence by kind.
- Storing evidence records still helps your audits; you can point reviewers to the saved items and their IDs.

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

