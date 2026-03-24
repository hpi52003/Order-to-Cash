# O2C Graph Explorer

A context graph system with LLM-powered natural language query interface for SAP Order-to-Cash data.

## Live Demo
> Add your Render/Railway URL here after deployment

## Architecture

Frontend (React + ReactFlow) → FastAPI Backend → SQLite DB + NetworkX + Anthropic API

## Database Choice: SQLite + NetworkX

SQLite is zero-infrastructure and LLMs generate reliable SQL far more consistently than Cypher (Neo4j query language). NetworkX handles in-memory graph traversal for the 921-node/1063-edge visualization layer without needing a separate graph DB.

## LLM Prompting Strategy

Two-pass architecture:
- Pass 1: NL question → structured JSON with SQL + intent classification (query/trace/anomaly/off_topic)
- Pass 2: SQL results → natural language business summary

Self-healing: SQL errors are fed back to the LLM for one correction attempt.
Model: claude-3-5-haiku-20241022 (fast, free-tier friendly)

## Guardrails

1. Keyword pre-filter: rejects clearly off-topic queries before any API call
2. LLM intent classification: returns off_topic intent for domain-irrelevant questions
Response: "This system only answers questions about the Order-to-Cash dataset."

## Graph Model

Nodes: SalesOrder, Delivery, BillingDocument, JournalEntry, Payment, Customer, Product, Plant, Cancellation

Key edges:
- Customer PLACED SalesOrder
- Delivery FULFILLS SalesOrderItem
- BillingDocument BILLS SalesOrderItem  
- BillingDocument HAS_JOURNAL JournalEntry
- BillingDocument PAID_BY Payment

## How to Run Locally

1. pip install -r requirements.txt
2. cp .env.example .env  (add ANTHROPIC_API_KEY)
3. Place sap-o2c-data/ in data/ folder
4. python -m backend.ingest
5. uvicorn backend.main:app --reload --port 8000
6. cd frontend && npm install && npm run dev

## AI Coding Session Logs
See /sessions/ folder - full Claude conversation transcript from building this system.
