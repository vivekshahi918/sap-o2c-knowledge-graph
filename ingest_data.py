import os
import json
import pandas as pd
from neo4j import GraphDatabase
from dotenv import load_dotenv

base_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(base_dir, "backend", ".env")
load_dotenv(dotenv_path)

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE")

DATA_ROOT = "./"

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def pad_item(value):
    """Normalization: Ensures SAP item IDs are 6-digit strings (e.g., '10' -> '000010')"""
    if value is None: return None
    return str(value).zfill(6)

def load_jsonl_folder(folder_name):
    """Helper to read partitioned .jsonl files into a list of dicts"""
    data = []
    folder_path = os.path.join(DATA_ROOT, folder_name)
    if not os.path.exists(folder_path):
        print(f"Warning: Folder {folder_name} not found.")
        return []
    
    for file in os.listdir(folder_path):
        if file.endswith(".jsonl"):
            with open(os.path.join(folder_path, file), 'r') as f:
                for line in f:
                    data.append(json.loads(line))
    return data

def run_ingestion():
    with driver.session(database=NEO4J_DATABASE) as session:
        print("Starting Ingestion...")

        print("Loading Orders...")
        orders = load_jsonl_folder("sales_order_headers")
        session.run("""
            UNWIND $rows AS row
            MERGE (o:Order {salesOrder: str(row.salesOrder)})
            SET o += row
        """, rows=orders)

        print("Loading Order Items...")
        order_items = load_jsonl_folder("sales_order_items")
        for item in order_items:
            item['salesOrderItem'] = pad_item(item.get('salesOrderItem'))
        
        session.run("""
            UNWIND $rows AS row
            MERGE (oi:OrderItem {salesOrder: str(row.salesOrder), salesOrderItem: row.salesOrderItem})
            SET oi += row
            WITH oi, row
            MATCH (o:Order {salesOrder: str(row.salesOrder)})
            MERGE (o)-[:HAS_ITEM]->(oi)
        """, rows=order_items)

        print("Loading Delivery Items and linking to Orders...")
        delivery_items = load_jsonl_folder("outbound_delivery_items")
        for di in delivery_items:
            di['deliveryDocumentItem'] = pad_item(di.get('deliveryDocumentItem'))
            di['referenceSdDocumentItem'] = pad_item(di.get('referenceSdDocumentItem'))

        session.run("""
            UNWIND $rows AS row
            MERGE (di:DeliveryItem {deliveryDocument: str(row.deliveryDocument), deliveryDocumentItem: row.deliveryDocumentItem})
            SET di += row
            WITH di, row
            MATCH (oi:OrderItem {salesOrder: str(row.referenceSdDocument), salesOrderItem: row.referenceSdDocumentItem})
            MERGE (oi)-[:DELIVERED_AS]->(di)
        """, rows=delivery_items)

        print("Loading Invoice Items and linking to Deliveries...")
        billing_items = load_jsonl_folder("billing_document_items")
        for bi in billing_items:
            bi['billingDocumentItem'] = pad_item(bi.get('billingDocumentItem'))
            bi['referenceSdDocumentItem'] = pad_item(bi.get('referenceSdDocumentItem'))

        session.run("""
            UNWIND $rows AS row
            MERGE (ii:InvoiceItem {billingDocument: str(row.billingDocument), billingDocumentItem: row.billingDocumentItem})
            SET ii += row
            WITH ii, row
            MATCH (di:DeliveryItem {deliveryDocument: str(row.referenceSdDocument), deliveryDocumentItem: row.referenceSdDocumentItem})
            MERGE (di)-[:BILLED_AS]->(ii)
        """, rows=billing_items)

        print("Ingestion Complete Success!")

if __name__ == "__main__":
    run_ingestion()
    driver.close()