"""
llm_engine.py — Two-pass LLM query engine:
  Pass 1: user question → SQL
  Pass 2: SQL results → natural language answer
"""
import os
import json
import sqlite3
import re
from groq import Groq # type: ignore
from dotenv import load_dotenv # type: ignore

load_dotenv()

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "o2c.db")
MODEL   = "llama-3.3-70b-versatile"

SCHEMA = """
AVAILABLE SQLITE TABLES AND COLUMNS:

sales_order_headers:
  salesOrder, salesOrderType, salesOrganization, distributionChannel,
  soldToParty, creationDate, totalNetAmount, transactionCurrency,
  overallDeliveryStatus, overallOrdReltdBillgStatus

sales_order_items:
  salesOrder, salesOrderItem, material, requestedQuantity,
  requestedQuantityUnit, netAmount, transactionCurrency,
  productionPlant, storageLocation

outbound_delivery_headers:
  deliveryDocument, shippingPoint, overallGoodsMovementStatus,
  overallPickingStatus, actualGoodsMovementDate

outbound_delivery_items:
  deliveryDocument, deliveryDocumentItem, referenceSdDocument,
  referenceSdDocumentItem, plant, actualDeliveryQuantity

billing_document_headers:
  billingDocument, billingDocumentType, soldToParty,
  totalNetAmount, transactionCurrency, accountingDocument,
  billingDocumentIsCancelled, billingDocumentDate, companyCode, fiscalYear

billing_document_items:
  billingDocument, billingDocumentItem, material,
  billingQuantity, netAmount, referenceSdDocument, referenceSdDocumentItem

billing_document_cancellations:
  billingDocument, cancelledBillingDocument, billingDocumentType

journal_entries:
  accountingDocument, companyCode, fiscalYear, glAccount,
  referenceDocument, amountInTransactionCurrency, transactionCurrency,
  amountInCompanyCodeCurrency, postingDate, documentDate,
  accountingDocumentType, clearingDate

payments:
  accountingDocument, invoiceReference, salesDocument, salesDocumentItem,
  amountInTransactionCurrency, transactionCurrency, clearingDate,
  customer, postingDate

business_partners:
  businessPartner, customer, businessPartnerFullName,
  businessPartnerName, industry

products:
  product, productType, productGroup, division, grossWeight, baseUnit

product_descriptions:
  product, language, productDescription

plants:
  plant, companyCode, plantName

KEY JOIN PATHS:
- sales_order_items.salesOrder → sales_order_headers.salesOrder
- outbound_delivery_items.referenceSdDocument → sales_order_items.salesOrder
- outbound_delivery_items.referenceSdDocumentItem → sales_order_items.salesOrderItem
- billing_document_items.referenceSdDocument → sales_order_items.salesOrder
- billing_document_headers.accountingDocument → journal_entries.accountingDocument
- billing_document_headers.accountingDocument → payments.invoiceReference
- billing_document_headers.billingDocument → billing_document_cancellations.cancelledBillingDocument
- business_partners.customer → sales_order_headers.soldToParty
- products.product → sales_order_items.material
"""

SYSTEM_PROMPT_SQL = f"""You are a precise SQL analyst for a SAP Order-to-Cash (O2C) dataset.
You ONLY answer questions about this dataset. If a question is not related to orders, deliveries, billing, payments, products, or customers in this dataset, set intent to "off_topic".

{SCHEMA}

Rules:
- Return ONLY valid JSON, no markdown, no explanation outside the JSON.
- Format: {{"intent": "query|trace|anomaly|off_topic", "sql": "SELECT ...", "explanation": "one sentence"}}
- For off_topic, set sql to null.
- Use only the tables and columns listed above.
- Never use columns not listed in the schema.
- For tracing a document, JOIN across the key paths above.
- LIMIT results to 50 rows unless the user asks for all.
- Use DISTINCT where appropriate to avoid duplicates.
"""

SYSTEM_PROMPT_SUMMARIZE = """You are a helpful business analyst. You received query results from a SAP Order-to-Cash database.
Summarize the results clearly and concisely in 2-4 sentences. Be specific — mention actual values, counts, or document numbers from the data.
Do not say "based on the data" — just state the findings directly.
If results are empty, say what that implies (e.g. no incomplete flows found)."""

O2C_KEYWORDS = {
    "order", "sales", "delivery", "billing", "invoice", "payment",
    "product", "material", "customer", "shipment", "journal", "entry",
    "plant", "document", "o2c", "flow", "cash", "ar", "receivable",
    "cancellation", "billed", "delivered", "quantity", "amount",
    "currency", "fiscal", "clearing", "trace", "track", "find",
    "which", "list", "show", "count", "how many", "what", "who",
}


def is_on_topic(question: str) -> bool:
    q = question.lower()
    return any(kw in q for kw in O2C_KEYWORDS)


def extract_node_ids(text: str) -> list[str]:
    patterns = [
        r"\b(\d{8,12})\b",
        r"\b([A-Z]{1,3}-\d+)\b",
    ]
    ids = []
    for p in patterns:
        ids.extend(re.findall(p, text))
    return list(set(ids))[:10]


def run_sql(sql: str) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(sql)
        rows = [dict(r) for r in cur.fetchall()]
        return rows
    except Exception as e:
        return [{"error": str(e)}]
    finally:
        conn.close()


def ask(question: str, history: list = None) -> dict:
    if history is None:
        history = []

    if not is_on_topic(question):
        return {
            "answer": "This system only answers questions about the Order-to-Cash dataset. "
                      "Please ask about sales orders, deliveries, billing documents, payments, products, or customers.",
            "data":   [],
            "sql":    None,
            "nodes_referenced": [],
        }

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    # Pass 1: generate SQL
    messages_p1 = [{"role": "system", "content": SYSTEM_PROMPT_SQL}]
    for h in history[-6:]:
        messages_p1.append({"role": h["role"], "content": h["content"]})
    messages_p1.append({"role": "user", "content": question})

    resp1 = client.chat.completions.create(
        model=MODEL,
        max_tokens=1024,
        messages=messages_p1,
    )

    raw = resp1.choices[0].message.content.strip()
    raw = re.sub(r"^```json\s*|^```\s*|```$", "", raw, flags=re.MULTILINE).strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "answer": "I couldn't parse the query. Please rephrase your question.",
            "data": [], "sql": None, "nodes_referenced": [],
        }

    if parsed.get("intent") == "off_topic":
        return {
            "answer": "This system only answers questions about the Order-to-Cash dataset. "
                      "Please ask about orders, deliveries, billing, payments, products, or customers.",
            "data": [], "sql": None, "nodes_referenced": [],
        }

    sql = parsed.get("sql")
    if not sql:
        return {
            "answer": parsed.get("explanation", "No SQL generated."),
            "data": [], "sql": None, "nodes_referenced": [],
        }

    data = run_sql(sql)

    # Self-heal if SQL error
    if data and "error" in data[0]:
        error_msg = data[0]["error"]
        heal_msg  = f"The SQL you generated caused this error: {error_msg}\nSQL was: {sql}\nFix it and return corrected JSON only."
        resp_fix  = client.chat.completions.create(
            model=MODEL,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_SQL},
                {"role": "user",   "content": heal_msg},
            ],
        )
        raw2 = resp_fix.choices[0].message.content.strip()
        raw2 = re.sub(r"^```json\s*|^```\s*|```$", "", raw2, flags=re.MULTILINE).strip()
        try:
            parsed2 = json.loads(raw2)
            sql     = parsed2.get("sql", sql)
            data    = run_sql(sql)
        except Exception:
            pass

    # Pass 2: summarize
    data_snippet   = json.dumps(data[:20], default=str)
    summary_prompt = (
        f"Question: {question}\n"
        f"SQL used: {sql}\n"
        f"Results ({len(data)} rows, showing first 20): {data_snippet}\n\n"
        "Summarize the findings concisely."
    )
    resp2 = client.chat.completions.create(
        model=MODEL,
        max_tokens=512,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_SUMMARIZE},
            {"role": "user",   "content": summary_prompt},
        ],
    )
    answer = resp2.choices[0].message.content.strip()

    return {
        "answer":           answer,
        "data":             data,
        "sql":              sql,
        "nodes_referenced": extract_node_ids(answer + " " + json.dumps(data[:5], default=str)),
    }


if __name__ == "__main__":
    tests = [
        "Which products are associated with the highest number of billing documents?",
        "Find sales orders that were delivered but never billed",
        "Write me a poem about cats",
    ]
    for q in tests:
        print(f"\nQ: {q}")
        r = ask(q)
        print(f"SQL: {r['sql']}")
        print(f"Answer: {r['answer']}")
        print(f"Rows: {len(r['data'])}")
  
    

   



        
