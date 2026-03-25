# O2C Graph Explorer

A graph-based explorer for SAP Order-to-Cash data with a natural language chat interface powered by Groq.

## Live Demo



## What it does

The app ingests the SAP O2C dataset, builds a graph of interconnected business entities, and lets you ask questions about it in plain English. The system translates those questions into SQL, runs them against the database, and returns a readable answer.

## Why SQLite and not Neo4j

LLMs generate SQL reliably. Cypher (Neo4j's query language) is less common in training data and produces more errors in practice. Since the dataset fits comfortably in SQLite, there was no reason to add the overhead of a graph database. NetworkX handles the in-memory graph structure for visualization.

## How the LLM works

Two calls per question. The first call takes the user's question and returns a SQL query with an intent label — query, trace, anomaly, or off_topic. The second call takes the SQL results and writes a plain English summary. If the first SQL query throws an error it gets sent back to the model once for a correction attempt before failing.

Model used: llama-3.3-70b-versatile via Groq free tier.

## Guardrails

Off-topic questions are filtered in two stages. First a keyword check rejects obvious non-dataset questions before making any API call. If something slips through, the LLM intent classification catches it and returns a standard rejection message.

## Graph Model

Nodes: SalesOrder, Delivery, BillingDocument, JournalEntry, Payment, Customer, Product, Plant, Cancellation

Key relationships:
- Customer → PLACED → SalesOrder
- Delivery → FULFILLS → SalesOrderItem
- BillingDocument → BILLS → SalesOrderItem
- BillingDocument → HAS_JOURNAL → JournalEntry
- BillingDocument → PAID_BY → Payment

## Run locally

-pip install -r requirements.txt
-add your LLM API key to .env file (GROQ_API_KEY in this case)
-place sap-o2c-data/ inside the data/ folder
-python -m backend.ingest
-uvicorn backend.main:app --reload --port 8000
-cd frontend && npm install && npm run dev

## Deployment
- Deployed on Render using a multi-stage Dockerfile
- Stage 1 builds the React frontend, Stage 2 sets up the Python backend and runs ingestion
- Both served from a single container via FastAPI StaticFiles
- LLM API key set as an environment variable in the Render dashboard
