from __future__ import annotations
import json, os, re
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from langchain_groq import ChatGroq
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_core.prompts import PromptTemplate

load_dotenv()

class AskRequest(BaseModel):
    question: str

class AskResponse(BaseModel):
    answer: str
    affected_node_ids: List[str]
    cypher: Optional[str] = None

app = FastAPI(title="SAP O2C Graph AI")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

GRAPH = Neo4jGraph(
    url=os.getenv("NEO4J_URI"),
    username=os.getenv("NEO4J_USER"),
    password=os.getenv("NEO4J_PASSWORD"),
    database=os.getenv("NEO4J_DATABASE")
)

def build_chain():
    llm = ChatGroq(
        api_key=os.getenv("GROQ_API_KEY"),
        model="llama-3.3-70b-versatile",
        temperature=0
    )

    cypher_t = (
        "Task: Generate Cypher for SAP O2C Graph.\n"
        "Schema: (:Order)-[:HAS_ITEM]->(:OrderItem)-[:DELIVERED_AS]->(:DeliveryItem)\n"
        "Properties:\n"
        "- Order(salesOrder, createdByUser)\n"
        "- OrderItem(material)\n"
        "- DeliveryItem(deliveryDocument)\n"
        "\n"
        "RULES:\n"
        "1. salesOrder is a STRING property on Order nodes.\n"
        "2. Use direct string literals in WHERE clauses.\n"
        "   Example: WHERE n.salesOrder = '740512'\n"
        "3. DO NOT use parameters like $salesOrder.\n"
        "4. To find the creator, read n.createdByUser.\n"
        "5. ALWAYS RETURN n, elementId(n) AS affected_node_ids.\n"
        "6. Return ONLY valid Cypher. No markdown. No backticks.\n"
        "\n"
        "Question: {question}"
    )

    qa_t = (
        "You are an SAP Analyst.\n"
        "Context: {context}\n"
        "Question: {question}\n\n"
        "Answer naturally based only on the context.\n"
        "Do not mention JSON, Cypher, or technical IDs.\n"
        "If context is empty, say: I could not find that record in the system.\n"
    )

    return GraphCypherQAChain.from_llm(
        llm=llm,
        graph=GRAPH,
        cypher_prompt=PromptTemplate(
            template=cypher_t,
            input_variables=["schema", "question"]
        ),
        qa_prompt=PromptTemplate(
            template=qa_t,
            input_variables=["context", "question"]
        ),
        allow_dangerous_requests=True,
        return_intermediate_steps=True
    )

CHAIN = build_chain()

@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    # Guardrail check
    if any(x in req.question.lower() for x in ['cake', 'recipe', 'poem']):
        return AskResponse(
            answer="This system is restricted to SAP analysis.",
            affected_node_ids=[]
        )

    try:
        out = CHAIN.invoke({"query": req.question})
        res_text = out.get("result", "")

        cypher = ""
        if out.get("intermediate_steps") and len(out["intermediate_steps"]) > 0:
            first_step = out["intermediate_steps"][0]
            if isinstance(first_step, dict):
                cypher = first_step.get("query", "")

        # Clean final answer
        final_answer = res_text
        try:
            parsed = json.loads(re.sub(r'```json|```', '', res_text).strip())
            final_answer = parsed.get("answer", res_text)
        except:
            final_answer = res_text.strip()

        # Direct highlight lookup from user question
        real_ids = []
        match = re.search(r'(\d{6,})', req.question)

        if match:
            order_id = match.group(1)

            id_query = """
            MATCH (o:Order)
            WHERE o.salesOrder = $order_id
            RETURN elementId(o) AS node_id
            """

            rows = GRAPH.query(id_query, params={"order_id": order_id})
            real_ids = [row["node_id"] for row in rows if row.get("node_id")]

        print("QUESTION:", req.question)
        print("CYPHER:", cypher)
        print("HIGHLIGHT IDS:", real_ids)

        return AskResponse(
            answer=final_answer,
            affected_node_ids=list(set(real_ids)),
            cypher=cypher
        )

    except Exception as e:
        print(f"CRITICAL ASK ERROR: {e}")
        return AskResponse(
            answer=f"Error analyzing graph: {str(e)}",
            affected_node_ids=[]
        )

@app.get("/graph-data")
async def get_graph():
    query = """
    MATCH (o:Order)-[:HAS_ITEM]->(oi:OrderItem)
    OPTIONAL MATCH (oi)-[:DELIVERED_AS]->(di:DeliveryItem)
    OPTIONAL MATCH (di)-[:BILLED_AS]->(ii:InvoiceItem)
    WITH o, oi, di, ii LIMIT 80
    UNWIND [
        {s:o, t:oi, r:'HAS_ITEM', sl:'Order', tl:'Order'}, 
        {s:oi, t:di, r:'DELIVERED_AS', sl:'Order', tl:'Delivery'}, 
        {s:di, t:ii, r:'BILLED_AS', sl:'Delivery', tl:'Invoice'}
    ] AS link
    WITH link WHERE link.t IS NOT NULL
    RETURN 
        elementId(link.s) as source_id, link.sl as source_label, properties(link.s) as source_props,
        link.r as rel_type,
        elementId(link.t) as target_id, link.tl as target_label, properties(link.t) as target_props
    """
    return GRAPH.query(query)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)