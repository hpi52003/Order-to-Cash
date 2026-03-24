
import sqlite3
import json
import os
import networkx as nx # type: ignore

DB_PATH        = os.path.join(os.path.dirname(__file__), "..", "data", "o2c.db")
GRAPH_JSON_OUT = os.path.join(os.path.dirname(__file__), "..", "data", "graph_data.json")

# Node type → color (for frontend)
TYPE_COLORS = {
    "SalesOrder":       "#378ADD",
    "Delivery":         "#1D9E75",
    "BillingDocument":  "#534AB7",
    "JournalEntry":     "#BA7517",
    "Payment":          "#639922",
    "Customer":         "#D85A30",
    "Product":          "#D4537E",
    "Plant":            "#888780",
    "Cancellation":     "#E24B4A",
}

G: nx.DiGraph = nx.DiGraph()


def _add_node(node_id: str, node_type: str, label: str, meta: dict):
    G.add_node(node_id, type=node_type, label=label, color=TYPE_COLORS.get(node_type, "#888"), meta=meta)


def _add_edge(src: str, dst: str, relation: str):
    if G.has_node(src) and G.has_node(dst):
        G.add_edge(src, dst, relation=relation)


def build_graph(conn: sqlite3.Connection):
    cur = conn.cursor()

    # Sales Orders
    for row in cur.execute("""
        SELECT salesOrder, salesOrganization, soldToParty,
               totalNetAmount, transactionCurrency,
               overallDeliveryStatus, overallOrdReltdBillgStatus
        FROM sales_order_headers
    """):
        nid = f"SO:{row[0]}"
        _add_node(nid, "SalesOrder", f"SO {row[0]}", {
            "salesOrder": row[0], "salesOrg": row[1],
            "soldToParty": row[2], "netAmount": row[3],
            "currency": row[4], "deliveryStatus": row[5],
            "billingStatus": row[6],
        })

    for row in cur.execute("SELECT salesOrder, salesOrderItem, material FROM sales_order_items"):
        so_nid   = f"SO:{row[0]}"
        item_nid = f"SOI:{row[0]}:{row[1]}"
        _add_node(item_nid, "SalesOrder", f"SO Item {row[1]}", {
            "salesOrder": row[0], "item": row[1], "material": row[2]
        })
        _add_edge(item_nid, so_nid, "BELONGS_TO")

    # Deliveries
    for row in cur.execute("""
        SELECT deliveryDocument, shippingPoint,
               overallGoodsMovementStatus, overallPickingStatus
        FROM outbound_delivery_headers
    """):
        nid = f"DEL:{row[0]}"
        _add_node(nid, "Delivery", f"Delivery {row[0]}", {
            "deliveryDoc": row[0], "shippingPoint": row[1],
            "goodsMovement": row[2], "pickingStatus": row[3],
        })

    # Delivery Items → SO Item + Delivery
    for row in cur.execute("""
        SELECT deliveryDocument, deliveryDocumentItem,
               referenceSdDocument, referenceSdDocumentItem, plant
        FROM outbound_delivery_items
    """):
        del_nid  = f"DEL:{row[0]}"
        so_item  = f"SOI:{row[2]}:{row[3]}"
        _add_edge(del_nid, so_item, "FULFILLS")
        # plant edge
        if row[4]:
            plant_nid = f"PLT:{row[4]}"
            if not G.has_node(plant_nid):
                _add_node(plant_nid, "Plant", f"Plant {row[4]}", {"plant": row[4]})
            _add_edge(del_nid, plant_nid, "SHIPS_FROM")

    # Billing Document Headers 
    for row in cur.execute("""
        SELECT billingDocument, billingDocumentType, soldToParty,
               totalNetAmount, transactionCurrency,
               accountingDocument, billingDocumentIsCancelled
        FROM billing_document_headers
    """):
        nid = f"BD:{row[0]}"
        _add_node(nid, "BillingDocument", f"Billing {row[0]}", {
            "billingDoc": row[0], "type": row[1],
            "soldToParty": row[2], "netAmount": row[3],
            "currency": row[4], "accountingDoc": row[5],
            "isCancelled": row[6],
        })

    # Billing Items → SO Item + Billing Header 
    for row in cur.execute("""
        SELECT billingDocument, referenceSdDocument,
               referenceSdDocumentItem, material
        FROM billing_document_items
    """):
        bd_nid   = f"BD:{row[0]}"
        so_item  = f"SOI:{row[1]}:{row[2]}"
        _add_edge(bd_nid, so_item, "BILLS")

    # Journal Entries
    for row in cur.execute("""
        SELECT accountingDocument, companyCode, fiscalYear,
               referenceDocument, amountInTransactionCurrency,
               transactionCurrency, postingDate
        FROM journal_entries
    """):
        nid = f"JE:{row[0]}"
        if not G.has_node(nid):
            _add_node(nid, "JournalEntry", f"JE {row[0]}", {
                "accountingDoc": row[0], "companyCode": row[1],
                "fiscalYear": row[2], "refDoc": row[3],
                "amount": row[4], "currency": row[5], "date": row[6],
            })
        # Link billing → journal via accountingDocument
        bd_nid = f"BD:{row[3]}"
        if G.has_node(bd_nid):
            _add_edge(bd_nid, nid, "HAS_JOURNAL")

    # Payments
    for row in cur.execute("""
        SELECT accountingDocument, invoiceReference, salesDocument,
               amountInTransactionCurrency, transactionCurrency,
               clearingDate
        FROM payments
    """):
        nid = f"PAY:{row[0]}"
        if not G.has_node(nid):
            _add_node(nid, "Payment", f"Payment {row[0]}", {
                "accountingDoc": row[0], "invoiceRef": row[1],
                "salesDoc": row[2], "amount": row[3],
                "currency": row[4], "clearingDate": row[5],
            })
        # Link billing → payment
        bd_nid = f"BD:{row[1]}"
        if G.has_node(bd_nid):
            _add_edge(bd_nid, nid, "PAID_BY")
        # Also link payment → journal entry if same accountingDocument
        je_nid = f"JE:{row[0]}"
        if G.has_node(je_nid):
            _add_edge(nid, je_nid, "RECORDED_IN")

    # Customers 
    for row in cur.execute("""
        SELECT businessPartner, customer, businessPartnerFullName, industry
        FROM business_partners WHERE customer IS NOT NULL AND customer != ''
    """):
        nid = f"CUS:{row[1]}"
        _add_node(nid, "Customer", row[2] or f"Customer {row[1]}", {
            "partnerId": row[0], "customerId": row[1],
            "name": row[2], "industry": row[3],
        })

    # Link Customer → SalesOrder (soldToParty)
    for row in cur.execute("SELECT salesOrder, soldToParty FROM sales_order_headers WHERE soldToParty IS NOT NULL"):
        so_nid  = f"SO:{row[0]}"
        cus_nid = f"CUS:{row[1]}"
        if G.has_node(cus_nid):
            _add_edge(cus_nid, so_nid, "PLACED")

    # Link Customer → BillingDocument
    for row in cur.execute("SELECT billingDocument, soldToParty FROM billing_document_headers WHERE soldToParty IS NOT NULL"):
        bd_nid  = f"BD:{row[0]}"
        cus_nid = f"CUS:{row[1]}"
        if G.has_node(cus_nid):
            _add_edge(cus_nid, bd_nid, "BILLED_TO")

    # Products
    for row in cur.execute("SELECT product, productType, productGroup, division FROM products"):
        nid = f"PRD:{row[0]}"
        # Get description if available
        _add_node(nid, "Product", f"Product {row[0]}", {
            "product": row[0], "type": row[1],
            "group": row[2], "division": row[3],
        })

    # Link Product → SalesOrderItem
    for row in cur.execute("SELECT salesOrder, salesOrderItem, material FROM sales_order_items WHERE material IS NOT NULL"):
        prd_nid  = f"PRD:{row[2]}"
        item_nid = f"SOI:{row[0]}:{row[1]}"
        if G.has_node(prd_nid) and G.has_node(item_nid):
            _add_edge(prd_nid, item_nid, "ORDERED_IN")

    # Cancellations
    for row in cur.execute("""
        SELECT billingDocument, cancelledBillingDocument
        FROM billing_document_cancellations
        WHERE cancelledBillingDocument IS NOT NULL
    """):
        bd_nid    = f"BD:{row[1]}"
        canc_nid  = f"CANC:{row[0]}"
        if not G.has_node(canc_nid):
            _add_node(canc_nid, "Cancellation", f"Cancellation {row[0]}", {
                "cancellationDoc": row[0], "cancelledDoc": row[1],
            })
        if G.has_node(bd_nid):
            _add_edge(canc_nid, bd_nid, "CANCELS")


#def export_graph_json(max_nodes=800):
def export_graph_json(max_nodes=300):
    """Export a sample of the graph as JSON for frontend rendering."""
    # Priority: headers over items (shorter IDs first as proxy)
    '''priority_types = ["Customer", "SalesOrder", "Delivery",
                      "BillingDocument", "JournalEntry", "Payment",
                      "Product", "Plant", "Cancellation"]'''
    priority_types = ["Customer", "SalesOrder", "Delivery",
                  "BillingDocument", "JournalEntry", "Payment",
                  "Product", "Plant", "Cancellation"]

    selected = []
    for ptype in priority_types:
        nodes = [n for n, d in G.nodes(data=True) if d.get("type") == ptype]
        selected.extend(nodes)
        if len(selected) >= max_nodes:
            break
    selected = selected[:max_nodes]
    selected_set = set(selected)

    nodes_out = []
    for nid in selected:
        d = G.nodes[nid]
        nodes_out.append({
            "id":    nid,
            "type":  d.get("type"),
            "label": d.get("label"),
            "color": d.get("color", "#888"),
            "meta":  d.get("meta", {}),
        })

    edges_out = []
    for src, dst, data in G.edges(data=True):
        if src in selected_set and dst in selected_set:
            edges_out.append({
                "source":   src,
                "target":   dst,
                "relation": data.get("relation", ""),
            })

    with open(GRAPH_JSON_OUT, "w") as f:
        json.dump({"nodes": nodes_out, "edges": edges_out}, f)

    return len(nodes_out), len(edges_out)


def get_neighbors(node_id: str) -> dict:
    """Return a node and all its immediate neighbors."""
    if not G.has_node(node_id):
        return {}
    d = G.nodes[node_id]
    neighbors = []
    for nbr in list(G.successors(node_id)) + list(G.predecessors(node_id)):
        nd = G.nodes[nbr]
        relation = (G[node_id][nbr].get("relation") if G.has_edge(node_id, nbr)
                    else G[nbr][node_id].get("relation", ""))
        neighbors.append({
            "id": nbr, "type": nd.get("type"),
            "label": nd.get("label"), "color": nd.get("color"),
            "relation": relation, "meta": nd.get("meta", {}),
        })
    return {
        "id": node_id, "type": d.get("type"),
        "label": d.get("label"), "color": d.get("color"),
        "meta": d.get("meta", {}), "neighbors": neighbors,
    }


def load_graph():
    """Build graph from DB — called once at server startup."""
    conn = sqlite3.connect(DB_PATH)
    build_graph(conn)
    conn.close()
    n_nodes, n_edges = export_graph_json()
    print(f"Graph loaded: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    print(f"Exported sample: {n_nodes} nodes, {n_edges} edges → graph_data.json")
    return G


if __name__ == "__main__":
    load_graph()
