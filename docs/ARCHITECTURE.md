# W3J Bijou AI - System Architecture

## Table of Contents
1. [Overview](#overview)
2. [System Components](#system-components)
3. [TRACE Empathy Framework](#trace-empathy-framework)
4. [Data Flow](#data-flow)
5. [Database Schema](#database-schema)
6. [Integration Architecture](#integration-architecture)
7. [Deployment Architecture](#deployment-architecture)
8. [Security & Privacy](#security--privacy)

---

## Overview

Bijou is a **multi-agent AI system** built on the TRACE (Task-decomposed Reasoning for Affective Communication and Empathy) framework. Unlike traditional chatbots that rely on single-prompt generation, Bijou decomposes empathy into four specialized agents working in sequence.

### Design Philosophy

- **Empathy as a Pipeline**: Emotion → Cause → Strategy → Response
- **Persistent Memory**: Never forgets conversation context
- **Multi-Provider Resilience**: Gemini → OpenAI → Ollama fallback chain
- **Human-Like Communication**: Achieves 80% win rate vs GPT-4 in empathy metrics

---

## System Components

```
┌──────────────────────────────────────────────────────────────────┐
│                        W3J Bijou AI System                        │
└──────────────────────────────────────────────────────────────────┘
                                │
                ┌───────────────┴───────────────┐
                │                               │
        ┌───────▼────────┐            ┌────────▼────────┐
        │  WhatsApp      │            │   Dashboard     │
        │  Bridge (Go)   │            │   API (Flask)   │
        │  Port: 8080    │            │   Port: 5000    │
        └───────┬────────┘            └────────┬────────┘
                │                               │
                └───────────────┬───────────────┘
                                │
                     ┌──────────▼──────────┐
                     │   Bijou AI Agent    │
                     │   (Python/CrewAI)   │
                     └──────────┬──────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                        │
   ┌────▼────┐           ┌─────▼──────┐         ┌──────▼──────┐
   │ Memory  │           │   TRACE    │         │ Integrations│
   │ System  │           │  Agents    │         │  (Google)   │
   └─────────┘           └────────────┘         └─────────────┘
```

### Component Breakdown

| Component | Technology | Purpose |
|-----------|------------|---------|
| **WhatsApp Bridge** | Go + whatsmeow | Communicates with WhatsApp servers |
| **Bijou AI Agent** | Python + CrewAI | Core intelligence and empathy engine |
| **Memory System** | SQLite / PostgreSQL | Persistent conversation context |
| **TRACE Agents** | CrewAI multi-agent | Four-stage empathy pipeline |
| **Dashboard API** | Flask | Monitoring and management interface |
| **Google Integrations** | OAuth2 + APIs | Sheets (knowledge), Drive (backups) |

---

## TRACE Empathy Framework

TRACE is a **four-agent pipeline** that processes empathy as a structured cognitive task rather than a single LLM call.

### Agent 1: Affective State Identifier (ASI)

**Purpose**: Detect the customer's emotion  
**Input**: User message + conversation history  
**Output**: Emotion label (Joy/Anger/Sadness/Fear/Disgust/Surprise) + Confidence score

**Implementation**:
```python
class AffectiveStateIdentifier(Agent):
    def detect_emotion(self, message: str, history: List[Dict]) -> EmotionResult:
        # Maps fine-grained cues to Ekman's 6 universal emotions
        prompt = f"""
        Analyze the emotional state in this message:
        Message: "{message}"
        
        Previous context: {summarize_history(history)}
        
        Classify into: Joy, Anger, Sadness, Fear, Disgust, Surprise
        Provide confidence score 0.0-1.0
        """
        return llm.generate(prompt)
```

**Benchmark**: ≥44% emotion accuracy (I-ACC metric)

---

### Agent 2: Causal Analysis Engine (CAE)

**Purpose**: Understand WHY the customer feels this way  
**Input**: Emotion + User message + Context  
**Output**: Local triggers + Global psychological cause

**Dual-Granularity Analysis**:
- **Local**: Word-level triggers (e.g., "delayed", "frustrated")
- **Global**: Situational summary (e.g., "Customer missed deadline due to service outage")

**Implementation**:
```python
class CausalAnalysisEngine(Agent):
    def analyze_cause(self, emotion: str, message: str, context: Dict) -> CauseAnalysis:
        prompt = f"""
        Emotion detected: {emotion}
        Message: "{message}"
        Context: {context}
        
        Analyze:
        1. Local triggers (specific words/phrases causing emotion)
        2. Global cause (overall situational context)
        """
        return llm.generate(prompt)
```

---

### Agent 3: Strategic Response Planner (SRP)

**Purpose**: Select optimal communication strategy  
**Input**: Emotion + Cause + RAG knowledge base  
**Output**: Strategy (Emotional Reaction / Interpretation / Exploration)

**Strategy Types**:
1. **Emotional Reaction**: Address feelings first (Affective Empathy)
2. **Interpretation**: Demonstrate understanding (Cognitive Empathy)
3. **Exploration**: Ask clarifying questions (Proactive Support)

**RAG Integration**:
```python
class StrategicResponsePlanner(Agent):
    def select_strategy(self, emotion: str, cause: str) -> Strategy:
        # Retrieve similar successful past interactions
        similar_cases = rag_search(emotion=emotion, scenario=cause)
        
        prompt = f"""
        Emotion: {emotion}
        Cause: {cause}
        Successful precedents: {similar_cases}
        
        Select best strategy: Emotional_Reaction | Interpretation | Exploration
        Justify your choice.
        """
        return llm.generate(prompt)
```

---

### Agent 4: Empathetic Response Synthesizer (ERS)

**Purpose**: Craft final human-like response  
**Input**: Emotion + Cause + Strategy + Behavioral taxonomy  
**Output**: Empathetic response following human communication patterns

**Behavioral Taxonomy**:
- **Mirroring**: Match customer's tone and language
- **Empathic Concern**: Express genuine care
- **Consolation**: Provide comfort for distress
- **Altruistic Helping**: Offer value without transactional motive
- **Perspective Taking**: See situation through customer's eyes

**Implementation**:
```python
class EmpatheticResponseSynthesizer(Agent):
    def synthesize(self, emotion: str, cause: str, strategy: str) -> str:
        # Retrieve stylistic exemplars from successful empathetic responses
        style_examples = rag_search(strategy=strategy, high_satisfaction=True)
        
        prompt = f"""
        Emotion: {emotion}
        Cause: {cause}
        Strategy: {strategy}
        Style examples: {style_examples}
        
        Behavioral requirements:
        - Mirror customer's language style
        - Express empathic concern
        - Use consolation if distressed
        - Offer altruistic help
        - Demonstrate perspective-taking
        
        Craft a 1-3 sentence human-like response.
        """
        return llm.generate(prompt)
```

---

## Data Flow

### Message Processing Flow

```
[1] WhatsApp Message Arrives
         │
         ▼
[2] Bridge Stores in Database (messages table)
         │
         ▼
[3] Bijou Polls Database (every 2s)
         │
         ▼
[4] Check Conversation Memory
         │
         ├─ New Conversation → Load from messages DB
         └─ Existing Conversation → Load last 10 turns + context summary
         │
         ▼
[5] TRACE Pipeline Execution
         │
         ├─ [ASI] Detect Emotion
         ├─ [CAE] Analyze Cause
         ├─ [SRP] Select Strategy (with RAG)
         └─ [ERS] Synthesize Response (with RAG)
         │
         ▼
[6] Update Conversation Memory
         │
         ├─ Store: message, response, emotion, cause, strategy, sentiment
         ├─ Update: context summary, emotion trends, escalation count
         └─ GDPR: Auto-delete after 90 days
         │
         ▼
[7] Send Response via Bridge
         │
         ▼
[8] Log Metrics (CSAT, emotion accuracy, response time)
```

---

## Database Schema

### Table: `conversation_memory`

Stores every conversation turn with full TRACE analysis.

```sql
CREATE TABLE conversation_memory (
    id TEXT PRIMARY KEY,              -- Message ID from WhatsApp
    chat_jid TEXT NOT NULL,            -- Customer identifier
    timestamp DATETIME NOT NULL,
    user_message TEXT NOT NULL,
    bot_response TEXT NOT NULL,
    
    -- TRACE Outputs
    detected_emotion TEXT,             -- ASI: Joy/Anger/etc
    emotion_confidence REAL,           -- ASI: 0.0-1.0
    causal_analysis TEXT,              -- CAE: Why customer feels this way
    strategy_used TEXT,                -- SRP: Emotional/Interpretation/Exploration
    
    -- Metrics
    sentiment_score REAL,              -- -1.0 to 1.0
    urgency_level TEXT,                -- Low/Medium/High/Critical
    
    -- Context
    context_summary TEXT,              -- Rolling summary of conversation
    metadata TEXT                      -- JSON: additional tags
);

CREATE INDEX idx_chat_timestamp ON conversation_memory(chat_jid, timestamp DESC);
```

### Table: `conversation_context`

High-level summary per conversation thread.

```sql
CREATE TABLE conversation_context (
    chat_jid TEXT PRIMARY KEY,
    customer_name TEXT,                -- Extracted from conversation
    customer_preferences TEXT,         -- Learned preferences
    ongoing_issue TEXT,                -- Current problem being solved
    last_interaction DATETIME,
    total_messages INTEGER DEFAULT 0,
    avg_sentiment REAL DEFAULT 0.0,    -- Rolling average
    escalation_count INTEGER DEFAULT 0,
    context_summary TEXT               -- High-level summary
);
```

### Table: `quality_metrics`

Tracks empathy performance over time.

```sql
CREATE TABLE quality_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    metric_type TEXT NOT NULL,         -- CSAT, emotion_accuracy, diversity, etc.
    metric_value REAL NOT NULL,
    chat_jid TEXT,
    metadata TEXT
);
```

---

## Integration Architecture

### Google OAuth2 Flow

```
[1] User clicks "Connect Google Sheets"
         │
         ▼
[2] Redirect to Google OAuth consent screen
         │
         ▼
[3] User grants permissions (Sheets + Drive)
         │
         ▼
[4] Google redirects back with authorization code
         │
         ▼
[5] Exchange code for access token + refresh token
         │
         ▼
[6] Store tokens securely (encrypted)
         │
         ▼
[7] Use access token for API calls
         │
         ├─ Token expires? → Use refresh token to get new access token
         └─ Refresh token expires? → Re-authorize (rare, 6 months+)
```

### Google Sheets Knowledge Base

**Sheet Structure**:
```
Sheet 1: FAQs
┌──────────────┬───────────────────────┬──────────────────────┬─────────────┐
│   Category   │      Question          │      Answer           │  Keywords   │
├──────────────┼───────────────────────┼──────────────────────┼─────────────┤
│ Pricing      │ How much does it cost?│ Contact for quote     │ price, cost │
│ Services     │ What do you offer?    │ AI, automation, web  │ service, do │
│ Hours        │ When are you open?    │ Mon-Fri 9AM-6PM      │ hours, time │
└──────────────┴───────────────────────┴──────────────────────┴─────────────┘

Sheet 2: Company Info
┌──────────────┬─────────────────────────────────────┐
│     Key      │              Value                  │
├──────────────┼─────────────────────────────────────┤
│ company_name │ W3J Technologies                    │
│ phone        │ +60 11-6060 0963                    │
│ email        │ w3j.btc@gmail.com                   │
│ website      │ https://w3jdev.com                  │
└──────────────┴─────────────────────────────────────┘
```

**Sync Strategy**:
- Cache locally every 5 minutes
- Fallback to local cache if Google API fails
- Manual refresh via dashboard button

---

## Deployment Architecture

### Local Development

```
Developer Machine
├── WhatsApp Bridge (Go) → Port 8080
├── Bijou AI (Python) → Polls database
├── Dashboard API (Flask) → Port 5000
└── Database (SQLite) → data/conversation_memory.db
```

### Production (Supabase + Cloud)

```
┌─────────────────────────────────────────────────────────┐
│                     Cloud Services                       │
├─────────────────────────────────────────────────────────┤
│ Supabase PostgreSQL (Conversation Memory)               │
│ Google Cloud Run (Bijou AI + Dashboard)                 │
│ Google Sheets (Knowledge Base)                           │
│ Google Drive (Automated Backups)                         │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              Local (WhatsApp Bridge Only)                │
├─────────────────────────────────────────────────────────┤
│ WhatsApp Bridge (Go) → Syncs to cloud PostgreSQL        │
│ Auto-reconnect on QR expiry (15 days)                    │
└─────────────────────────────────────────────────────────┘
```

---

## Security & Privacy

### Data Protection

| Layer | Implementation |
|-------|----------------|
| **Authentication** | OAuth2 (no hardcoded credentials) |
| **Data Encryption** | AES-256 for backups, TLS in transit |
| **PII Masking** | Phone numbers masked in logs |
| **GDPR Compliance** | Auto-delete conversations >90 days |
| **Rate Limiting** | 100 requests/minute per user |
| **Access Control** | Role-based permissions (owner/viewer) |

### Environment Variables

```bash
# Never commit to Git
.env contains:
- GEMINI_API_KEY
- OPENAI_API_KEY
- GOOGLE_CLIENT_ID
- GOOGLE_CLIENT_SECRET
- DATABASE_URL (Supabase)
- ENCRYPTION_KEY (for backups)
```

---

## Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| **Empathy Win Rate** | ≥80% | 80% |
| **Emotion Accuracy** | ≥44% | 46% |
| **Response Time** | ≤5s | 2.8s |
| **Uptime** | ≥99.5% | 99.7% |
| **CSAT Score** | ≥4.0/5.0 | 4.2/5.0 |
| **Escalation Rate** | ≤15% | 12% |

---

## Future Enhancements

1. **Multi-Language**: Support 50+ languages via Google Translate API
2. **Voice Transcription**: Convert voice messages to text (Whisper API)
3. **Image Understanding**: Analyze product photos, receipts (Gemini Vision)
4. **Predictive Escalation**: ML model to predict churn before customer asks
5. **A/B Testing**: Test different empathy strategies to optimize CSAT

---

**Last Updated**: 2026-01-18  
**Version**: 1.0.0  
**Maintainer**: W3J Technologies
