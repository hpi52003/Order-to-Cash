"""
ingest.py — Load all SAP O2C JSONL files into SQLite
Run: python -m backend.ingest
"""
import sqlite3
import pandas as pd
import os
import glob

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "sap-o2c-data")
DB_PATH  = os.path.join(os.path.dirname(__file__), "..", "data", "o2c.db")

# Map folder name → table name
ENTITY_MAP = {
    "sales_order_headers":                       "sales_order_headers",
    "sales_order_items":                         "sales_order_items",
    "sales_order_schedule_lines":                "sales_order_schedule_lines",
    "outbound_delivery_headers":                 "outbound_delivery_headers",
    "outbound_delivery_items":                   "outbound_delivery_items",
    "billing_document_headers":                  "billing_document_headers",
    "billing_document_items":                    "billing_document_items",
    "billing_document_cancellations":            "billing_document_cancellations",
    "journal_entry_items_accounts_receivable":   "journal_entries",
    "payments_accounts_receivable":              "payments",
    "business_partners":                         "business_partners",
    "business_partner_addresses":                "business_partner_addresses",
    "customer_company_assignments":              "customer_company_assignments",
    "customer_sales_area_assignments":           "customer_sales_area_assignments",
    "products":                                  "products",
    "product_descriptions":                      "product_descriptions",
    "product_plants":                            "product_plants",
    "plants":                                    "plants",
}

# Indexes to create: (table, column)
INDEXES = [
    ("sales_order_headers",   "salesOrder"),
    ("sales_order_items",     "salesOrder"),
    ("sales_order_items",     "material"),
    ("outbound_delivery_headers", "deliveryDocument"),
    ("outbound_delivery_items",   "deliveryDocument"),
    ("outbound_delivery_items",   "referenceSdDocument"),
    ("billing_document_headers",  "billingDocument"),
    ("billing_document_headers",  "accountingDocument"),
    ("billing_document_headers",  "soldToParty"),
    ("billing_document_items",    "billingDocument"),
    ("billing_document_items",    "referenceSdDocument"),
    ("billing_document_items",    "material"),
    ("journal_entries",           "accountingDocument"),
    ("journal_entries",           "referenceDocument"),
    ("payments",                  "invoiceReference"),
    ("payments",                  "salesDocument"),
    ("business_partners",         "businessPartner"),
    ("business_partners",         "customer"),
    ("products",                  "product"),
]


def load_entity(folder_name: str, table_name: str, conn: sqlite3.Connection):
    folder = os.path.join(DATA_DIR, folder_name)
    files  = glob.glob(os.path.join(folder, "part-*.jsonl"))
    if not files:
        print(f"  ⚠  No files found for {folder_name}")
        return 0

    frames = []
    for f in files:
        try:
            df = pd.read_json(f, lines=True)
            if not df.empty:
                frames.append(df)
        except Exception as e:
            print(f"  ⚠  Error reading {f}: {e}")

    if not frames:
        return 0

    df = pd.concat(frames, ignore_index=True)
    # Convert any dict/list columns to strings so dedup works
    for col in df.columns:
        if df[col].dtype == object:
            sample = df[col].dropna().head(5).tolist()
            if any(isinstance(v, (dict, list)) for v in sample):
                df[col] = df[col].astype(str)
    df = df.drop_duplicates()

    # Sanitise column names (no spaces)
    df.columns = [c.replace(" ", "_") for c in df.columns]

    # Write to SQLite — replace avoids schema conflicts on re-run
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    return len(df)


def create_indexes(conn: sqlite3.Connection):
    cur = conn.cursor()
    for table, col in INDEXES:
        # Check the column actually exists before indexing
        cur.execute(f"PRAGMA table_info({table})")
        cols = [r[1] for r in cur.fetchall()]
        if col in cols:
            idx = f"idx_{table}_{col}"
            cur.execute(f"CREATE INDEX IF NOT EXISTS {idx} ON {table}({col})")
    conn.commit()


def main():
    # Remove stale DB
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    print("Loading entities into SQLite …\n")

    total = 0
    for folder, table in ENTITY_MAP.items():
        n = load_entity(folder, table, conn)
        print(f"  {table:<50} {n:>6} rows")
        total += n

    print(f"\nTotal rows: {total}")
    print("Creating indexes …")
    create_indexes(conn)
    conn.close()
    print(f"\nDone. Database saved to {DB_PATH}")


if __name__ == "__main__":
    main()
