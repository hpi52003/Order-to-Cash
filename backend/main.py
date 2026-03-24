

"""
main.py — FastAPI backend for O2C Graph Explorer
Run: uvicorn backend.main:app --reload --port 8000
"""
import os
import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException # type: ignore
from fastapi.middleware.cors import CORSMiddleware # type: ignore
from fastapi.staticfiles import StaticFiles # type: ignore   ← ADD THIS
from pydantic import BaseModel # type: ignore

from backend.graph_builder import load_graph, get_neighbors, G
from backend.llm_engine import ask

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Building graph from SQLite …")
    load_graph()
    print("Graph ready.")
    yield

app = FastAPI(title="O2C Graph API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    history: list = []

@app.get("/health")
def health():
    return {"status": "ok", "nodes": G.number_of_nodes(), "edges": G.number_of_edges()}

@app.get("/api/counts")
def get_counts():
    db_path = os.path.join(os.path.dirname(__file__), "..", "data", "o2c.db")
    conn    = sqlite3.connect(db_path)
    cur     = conn.cursor()
    counts  = {
        "Customer":        cur.execute("SELECT COUNT(*) FROM business_partners WHERE customer IS NOT NULL AND customer != ''").fetchone()[0],
        "SalesOrder":      cur.execute("SELECT COUNT(*) FROM sales_order_headers").fetchone()[0],
        "Delivery":        cur.execute("SELECT COUNT(*) FROM outbound_delivery_headers").fetchone()[0],
        "BillingDocument": cur.execute("SELECT COUNT(*) FROM billing_document_headers").fetchone()[0],
        "JournalEntry":    cur.execute("SELECT COUNT(*) FROM journal_entries").fetchone()[0],
        "Payment":         cur.execute("SELECT COUNT(*) FROM payments").fetchone()[0],
        "Product":         cur.execute("SELECT COUNT(*) FROM products").fetchone()[0],
        "Plant":           cur.execute("SELECT COUNT(*) FROM plants").fetchone()[0],
        "Cancellation":    cur.execute("SELECT COUNT(*) FROM billing_document_cancellations").fetchone()[0],
    }
    conn.close()
    return counts

@app.get("/api/graph/node/{node_id:path}")
def get_node(node_id: str):
    result = get_neighbors(node_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")
    return result

@app.post("/api/chat")
def chat(req: ChatRequest):
    result = ask(req.message, req.history)
    return result

# Serve frontend 
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")  
