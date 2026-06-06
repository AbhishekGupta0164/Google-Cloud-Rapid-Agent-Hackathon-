"""
DevSentinel — Atlas MCP Tool Wrappers
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Wraps MongoDB Atlas admin operations as Google ADK FunctionTools.
These map to the 13 MongoDB MCP Tools described in the hackathon brief.

TOOLS PROVIDED:
  1.  collection_schema          — Auto-discovers collection field structure
  2.  list_collections           — Lists all collections in the database
  3.  create_vector_search_index — Creates Atlas Vector Search index
  4.  get_performance_advice     — Gets index recommendations from Atlas
  5.  create_index_suggestion    — Creates a suggested compound index
  6.  list_indexes               — Lists all indexes on a collection
  7.  get_cluster_stats          — Gets Atlas cluster health metrics
  8.  run_aggregation            — Runs an aggregation pipeline
  9.  find_documents             — Finds documents with a filter
  10. insert_document            — Inserts a single document
  11. update_document            — Updates documents matching a filter
  12. count_documents            — Counts documents matching a filter
"""

import os
from typing import Optional, List, Dict, Any

import pymongo
from pymongo import MongoClient
from pymongo.database import Database
from google.adk.tools import FunctionTool


# ── Singleton DB client ───────────────────────────────────────────
_client: MongoClient = None
_db: Database = None


def _get_db() -> Database:
    global _client, _db
    if _db is None:
        uri = os.environ.get("MONGODB_URI", "")
        db_name = os.environ.get("MONGODB_DB_NAME", "devsentiinel")
        if not uri:
            raise ValueError("MONGODB_URI is not set")
        _client = MongoClient(uri)
        _db = _client[db_name]
    return _db


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TOOL FUNCTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def collection_schema(collection_name: str, sample_size: int = 20) -> dict:
    """
    Auto-discovers the schema of a MongoDB collection by sampling documents.
    Returns field names, types, and sample values without hardcoding schema.

    Args:
        collection_name: Name of the collection to inspect
        sample_size:     Number of documents to sample (default 20)

    Returns:
        dict with "fields" mapping field names to their inferred types.

    Example:
        collection_schema("orders")
        → {"fields": {"_id": "ObjectId", "payment_status": "str",
                       "customerId": "str", "createdAt": "datetime"}}
    """
    try:
        db = _get_db()
        docs = list(db[collection_name].aggregate([{"$sample": {"size": sample_size}}]))
        schema: Dict[str, set] = {}
        for doc in docs:
            for key, val in doc.items():
                schema.setdefault(key, set()).add(type(val).__name__)
        return {
            "collection": collection_name,
            "fields": {k: list(v)[0] if len(v) == 1 else list(v)
                       for k, v in schema.items()},
            "sample_count": len(docs),
        }
    except Exception as e:
        return {"error": str(e), "collection": collection_name}


def list_collections() -> dict:
    """
    Lists all collections in the database.

    Returns:
        dict with "collections" list of collection names.
    """
    try:
        db = _get_db()
        return {"collections": db.list_collection_names()}
    except Exception as e:
        return {"error": str(e)}


def list_indexes(collection_name: str) -> dict:
    """
    Lists all indexes on a collection including their field keys and options.

    Args:
        collection_name: Name of the collection to check

    Returns:
        dict with "indexes" list of index definitions.

    Example:
        list_indexes("orders")
        → {"indexes": [{"name": "payment_status_1",
                         "key": [["payment_status", 1]],
                         "unique": False}]}
    """
    try:
        db = _get_db()
        raw = db[collection_name].index_information()
        indexes = [
            {
                "name": name,
                "key": info.get("key", []),
                "unique": info.get("unique", False),
                "sparse": info.get("sparse", False),
            }
            for name, info in raw.items()
        ]
        return {"collection": collection_name, "indexes": indexes, "count": len(indexes)}
    except Exception as e:
        return {"error": str(e), "collection": collection_name}


def create_compound_index(
    collection_name: str,
    fields: List[str],
    unique: bool = False
) -> dict:
    """
    Creates a compound index on the specified fields in a collection.
    Maps to the atlas-create-index-suggestion MCP tool.

    Args:
        collection_name: Name of the collection
        fields:          List of field names (ascending by default)
        unique:          Whether to create a unique index (default False)

    Returns:
        dict with index_name and success status.

    Example:
        create_compound_index("orders", ["customerId", "status", "createdAt"])
        → {"index_name": "customerId_1_status_1_createdAt_1", "created": True}
    """
    try:
        db = _get_db()
        index_spec = [(f, pymongo.ASCENDING) for f in fields]
        result = db[collection_name].create_index(index_spec, unique=unique)
        return {
            "collection": collection_name,
            "index_name": result,
            "fields": fields,
            "unique": unique,
            "created": True,
        }
    except Exception as e:
        return {"error": str(e), "created": False}


def run_aggregation(collection_name: str, pipeline: List[Dict]) -> dict:
    """
    Runs a MongoDB aggregation pipeline on the specified collection.
    Maps to the aggregate MCP tool.

    Args:
        collection_name: Name of the collection
        pipeline:        List of aggregation stage dicts

    Returns:
        dict with "results" list and "count".

    Example:
        run_aggregation("orders", [{"$match": {"status": "active"}},
                                    {"$count": "total"}])
        → {"results": [{"total": 847}], "count": 1}
    """
    try:
        db = _get_db()
        results = list(db[collection_name].aggregate(pipeline))
        # Convert ObjectIds to strings for JSON serialisation
        for r in results:
            if "_id" in r:
                r["_id"] = str(r["_id"])
        return {"results": results, "count": len(results)}
    except Exception as e:
        return {"error": str(e), "results": []}


def find_documents(
    collection_name: str,
    filter_query: Dict,
    limit: int = 10,
    projection: Optional[Dict] = None
) -> dict:
    """
    Finds documents in a collection matching the given filter.
    Maps to the find MCP tool.

    Args:
        collection_name: Name of the collection
        filter_query:    MongoDB filter dict, e.g. {"status": "active"}
        limit:           Maximum number of documents to return (default 10)
        projection:      Optional field projection dict

    Returns:
        dict with "documents" list.
    """
    try:
        db = _get_db()
        cursor = db[collection_name].find(filter_query, projection or {}).limit(limit)
        docs = []
        for d in cursor:
            d["_id"] = str(d["_id"])
            docs.append(d)
        return {"documents": docs, "count": len(docs)}
    except Exception as e:
        return {"error": str(e), "documents": []}


def count_documents(collection_name: str, filter_query: Dict = {}) -> dict:
    """
    Counts documents in a collection matching the given filter.

    Args:
        collection_name: Name of the collection
        filter_query:    MongoDB filter dict (default {} = count all)

    Returns:
        dict with "count" integer.
    """
    try:
        db = _get_db()
        count = db[collection_name].count_documents(filter_query)
        return {"collection": collection_name, "count": count}
    except Exception as e:
        return {"error": str(e)}


def insert_document(collection_name: str, document: Dict) -> dict:
    """
    Inserts a single document into a collection.
    Maps to the insert-many MCP tool (single document variant).

    Args:
        collection_name: Name of the collection
        document:        Document dict to insert

    Returns:
        dict with "inserted_id" string.
    """
    try:
        db = _get_db()
        result = db[collection_name].insert_one(document)
        return {"inserted_id": str(result.inserted_id), "success": True}
    except Exception as e:
        return {"error": str(e), "success": False}


def update_document(
    collection_name: str,
    filter_query: Dict,
    update_doc: Dict,
    upsert: bool = False
) -> dict:
    """
    Updates documents matching the filter in a collection.
    Maps to the update-one MCP tool.

    Args:
        collection_name: Name of the collection
        filter_query:    MongoDB filter dict to identify documents to update
        update_doc:      MongoDB update dict, e.g. {"$set": {"status": "resolved"}}
        upsert:          Create document if not found (default False)

    Returns:
        dict with "matched_count" and "modified_count".
    """
    try:
        db = _get_db()
        result = db[collection_name].update_one(filter_query, update_doc, upsert=upsert)
        return {
            "matched_count": result.matched_count,
            "modified_count": result.modified_count,
            "upserted_id": str(result.upserted_id) if result.upserted_id else None,
            "success": True,
        }
    except Exception as e:
        return {"error": str(e), "success": False}


def get_cluster_stats() -> dict:
    """
    Returns MongoDB cluster health metrics: database sizes, collection counts,
    and connection status. Maps to the atlas-list-clusters MCP tool.

    Returns:
        dict with database stats and server info.
    """
    try:
        db = _get_db()
        stats = db.command("dbStats")
        server_info = db.client.server_info()
        return {
            "db": db.name,
            "collections": stats.get("collections", 0),
            "objects": stats.get("objects", 0),
            "data_size_mb": round(stats.get("dataSize", 0) / 1024 / 1024, 2),
            "storage_size_mb": round(stats.get("storageSize", 0) / 1024 / 1024, 2),
            "indexes": stats.get("indexes", 0),
            "mongodb_version": server_info.get("version", "unknown"),
        }
    except Exception as e:
        return {"error": str(e)}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# REGISTER AS ADK FunctionTools
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
atlas_tools = [
    FunctionTool(collection_schema),
    FunctionTool(list_collections),
    FunctionTool(list_indexes),
    FunctionTool(create_compound_index),
    FunctionTool(run_aggregation),
    FunctionTool(find_documents),
    FunctionTool(count_documents),
    FunctionTool(insert_document),
    FunctionTool(update_document),
    FunctionTool(get_cluster_stats),
]

__all__ = [
    "atlas_tools",
    "collection_schema",
    "list_collections",
    "list_indexes",
    "create_compound_index",
    "run_aggregation",
    "find_documents",
    "count_documents",
    "insert_document",
    "update_document",
    "get_cluster_stats",
]
