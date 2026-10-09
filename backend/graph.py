import sqlite3
from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

from backend.config import DB_PATH
from backend.state import GraphState
from backend.nodes.extract_text import extract_text
from backend.nodes.profile_and_queries import profile_and_queries
from backend.nodes.human_review import human_review
from backend.nodes.search_dispatcher import search_dispatcher, dispatch_search_queries
from backend.nodes.search_one import search_one
from backend.nodes.rule_filter import rule_filter
from backend.nodes.batch_builder import batch_builder
from backend.nodes.extract_jobs import extract_jobs
from backend.nodes.score_jobs import score_jobs
from backend.nodes.ranker import ranker
from backend.nodes.quality_gate import quality_gate, route_quality_gate
from backend.nodes.query_refiner import query_refiner
from backend.nodes.error_end import error_end

def check_extracted_text(state: GraphState) -> Literal["profile_and_queries", "error_end"]:
    text = state.get("resume_text", "")
    if len(text.strip()) >= 200:
        return "profile_and_queries"
    return "error_end"

def check_candidates(state: GraphState) -> Literal["batch_builder", "quality_gate"]:
    candidates = state.get("candidates", [])
    if candidates and len(candidates) > 0:
        return "batch_builder"
    return "quality_gate"

def build_graph(checkpointer=None):
    builder = StateGraph(GraphState)

    # Add all nodes
    builder.add_node("extract_text", extract_text)
    builder.add_node("profile_and_queries", profile_and_queries)
    builder.add_node("human_review", human_review)
    builder.add_node("search_dispatcher", search_dispatcher)
    builder.add_node("search_one", search_one)
    builder.add_node("rule_filter", rule_filter)
    builder.add_node("batch_builder", batch_builder)
    builder.add_node("extract_jobs", extract_jobs)
    builder.add_node("score_jobs", score_jobs)
    builder.add_node("ranker", ranker)
    builder.add_node("quality_gate", quality_gate)
    builder.add_node("query_refiner", query_refiner)
    builder.add_node("error_end", error_end)

    # START -> extract_text
    builder.add_edge(START, "extract_text")

    # Conditional after extract_text
    builder.add_conditional_edges(
        "extract_text",
        check_extracted_text,
        {
            "profile_and_queries": "profile_and_queries",
            "error_end": "error_end",
        }
    )

    # profile_and_queries -> human_review
    builder.add_edge("profile_and_queries", "human_review")

    # human_review -> search_dispatcher
    builder.add_edge("human_review", "search_dispatcher")

    # Fan-out: search_dispatcher -> Send per query -> search_one
    builder.add_conditional_edges(
        "search_dispatcher",
        dispatch_search_queries,
        ["search_one"]
    )

    # Fan-in: search_one -> rule_filter
    builder.add_edge("search_one", "rule_filter")

    # Conditional after rule_filter
    builder.add_conditional_edges(
        "rule_filter",
        check_candidates,
        {
            "batch_builder": "batch_builder",
            "quality_gate": "quality_gate",
        }
    )

    # Processing pipeline
    builder.add_edge("batch_builder", "extract_jobs")
    builder.add_edge("extract_jobs", "score_jobs")
    builder.add_edge("score_jobs", "ranker")
    builder.add_edge("ranker", "quality_gate")

    # Conditional after quality_gate
    builder.add_conditional_edges(
        "quality_gate",
        route_quality_gate,
        {
            "END": END,
            "query_refiner": "query_refiner",
        }
    )

    # Query refiner loops back to search_dispatcher
    builder.add_edge("query_refiner", "search_dispatcher")

    # error_end -> END
    builder.add_edge("error_end", END)

    if checkpointer is not None:
        return builder.compile(checkpointer=checkpointer)

    # Default synchronous checkpointer
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    sync_checkpointer = SqliteSaver(conn)
    return builder.compile(checkpointer=sync_checkpointer)

# Graph instance compiled with default checkpointer
graph = build_graph()

