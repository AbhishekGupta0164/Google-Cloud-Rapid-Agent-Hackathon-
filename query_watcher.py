"""
DevSentinel — Atlas Change Stream Query Watcher
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Watches the query_patterns collection for new documents and triggers
the ScaleTester pipeline via the FastAPI /trigger/query endpoint.

Run alongside the main API:
  python query_watcher.py

HOW IT WORKS:
  MongoDB Atlas Change Streams watch for insert/update events on the
  query_patterns collection. When a new pattern is detected, this script
  POSTs to the DevSentinel API to run ScaleTester analysis on it.

PRODUCTION SETUP:
  Deploy this as a separate Cloud Run Job or Cloud Run Service alongside
  the main FastAPI app. Both connect to the same MongoDB Atlas cluster.
"""

import os
import asyncio
import httpx
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

import pymongo
from pymongo import MongoClient


API_BASE_URL = os.environ.get("DEVSENTIINEL_API_URL", "http://localhost:8080")
MONGODB_URI  = os.environ.get("MONGODB_URI", "")
DB_NAME      = os.environ.get("MONGODB_DB_NAME", "devsentiinel")


def watch_query_patterns():
    """
    Watches the query_patterns collection using a MongoDB Change Stream.
    Fires the ScaleTester pipeline whenever a new query pattern is inserted.

    EXAMPLE CHANGE STREAM EVENT:
      {
        "operationType": "insert",
        "fullDocument": {
          "collection": "orders",
          "operation": "find",
          "query_text": "db.orders.find({customerId, status}...)",
          "description": "Query on orders collection...",
          "risk_level": "CRITICAL"
        }
      }
    """
    if not MONGODB_URI:
        print("[Watcher] ERROR: MONGODB_URI not set. Cannot start change stream.")
        return

    client = MongoClient(MONGODB_URI)
    db = client[DB_NAME]
    collection = db["query_patterns"]

    print(f"[Watcher] Watching query_patterns collection on {DB_NAME}...")
    print(f"[Watcher] Will POST new patterns to {API_BASE_URL}/trigger/query")

    # Pipeline: only watch INSERT operations
    pipeline = [{"$match": {"operationType": "insert"}}]

    with collection.watch(pipeline, full_document="updateLookup") as stream:
        for change in stream:
            doc = change.get("fullDocument", {})
            print(f"[Watcher] New query pattern detected: {doc.get('collection')}.{doc.get('operation')}")

            # Trigger ScaleTester via API
            try:
                with httpx.Client(timeout=10) as http:
                    response = http.post(
                        f"{API_BASE_URL}/trigger/query",
                        json={
                            "collection": doc.get("collection", ""),
                            "operation": doc.get("operation", "find"),
                            "query_text": doc.get("query_text", ""),
                            "args_preview": "",
                            "source": "atlas_change_stream",
                            "detected_at": datetime.utcnow().isoformat(),
                        }
                    )
                    print(f"[Watcher] API response: {response.status_code} — {response.json()}")
            except Exception as e:
                print(f"[Watcher] Failed to notify API: {e}")


if __name__ == "__main__":
    watch_query_patterns()
