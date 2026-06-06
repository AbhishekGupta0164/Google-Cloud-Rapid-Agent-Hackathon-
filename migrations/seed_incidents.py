"""
DevSentinel — Seed Past Incidents
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Seeds MongoDB Atlas with realistic past incidents for Vector Search demo.
Run once to populate the past_incidents collection.

Usage:
  python migrations/seed_incidents.py
"""

import os
import sys
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from config.database import get_db
from tools.embedding_tool import get_embeddings_batch

PAST_INCIDENTS = [
    {
        "title": "Payment Status Field Rename Cascade Failure",
        "description": (
            "Engineer renamed payment_status to payment_state in the orders collection "
            "without updating downstream services. The checkout service, analytics pipeline, "
            "and refund processor all read payment_status and began returning null values. "
            "This caused 100% of payment status checks to fail silently."
        ),
        "field_changed": "payment_status",
        "collections_affected": ["orders", "refunds", "analytics"],
        "services_affected": ["checkout-service", "analytics-pipeline", "refund-processor"],
        "fix_applied": "Dual-write migration: wrote to both payment_status and payment_state for 48h, then deprecated old field",
        "recovery_time_hours": 6,
        "severity": "P0",
        "date": (datetime.utcnow() - timedelta(days=90)).strftime("%Y-%m-%d"),
        "root_cause": "No backward compatibility window, immediate hard cutover",
        "lesson_learned": "Always use dual-write for field renames. Never hard-cut."
    },
    {
        "title": "Missing Compound Index Caused Orders Page Timeout",
        "description": (
            "New feature added db.orders.find({customerId, status}).sort({createdAt:-1}) "
            "query without a compound index. On dev (1,200 docs) response was 20ms. "
            "In production (800,000 docs) query took 14 seconds and caused request timeouts."
        ),
        "field_changed": "customerId",
        "collections_affected": ["orders"],
        "services_affected": ["order-service", "customer-portal"],
        "fix_applied": "db.orders.createIndex({customerId:1, status:1, createdAt:-1}) — immediate relief",
        "recovery_time_hours": 2,
        "severity": "P1",
        "date": (datetime.utcnow() - timedelta(days=45)).strftime("%Y-%m-%d"),
        "root_cause": "Collection scan on high-cardinality field without index",
        "lesson_learned": "All queries on orders collection require compound index review before deploy"
    },
    {
        "title": "Schema Migration Without Backfill Broke Analytics",
        "description": (
            "Added new required field 'region' to the users collection. "
            "Existing 2.3M user documents did not have this field. "
            "Analytics dashboards showing user segmentation by region returned empty data "
            "for all records created before the migration."
        ),
        "field_changed": "region",
        "collections_affected": ["users", "analytics"],
        "services_affected": ["analytics-service", "reporting-dashboard"],
        "fix_applied": "Backfill script to add region='unknown' to all existing documents, then re-run analytics",
        "recovery_time_hours": 4,
        "severity": "P1",
        "date": (datetime.utcnow() - timedelta(days=120)).strftime("%Y-%m-%d"),
        "root_cause": "New field added without default value or backfill for existing documents",
        "lesson_learned": "Schema changes must include migration script for existing data"
    },
    {
        "title": "Index Drop Caused Full Collection Scan in Prod",
        "description": (
            "PR to 'clean up indexes' removed the email_1 index from users collection, "
            "believing it was unused. Login queries (find by email) went from 2ms to 8 seconds. "
            "User login failure rate hit 34%."
        ),
        "field_changed": "email",
        "collections_affected": ["users"],
        "services_affected": ["auth-service", "user-service"],
        "fix_applied": "Recreated db.users.createIndex({email:1}, {unique:true}) — query time back to 2ms",
        "recovery_time_hours": 1,
        "severity": "P0",
        "date": (datetime.utcnow() - timedelta(days=60)).strftime("%Y-%m-%d"),
        "root_cause": "Index usage was not checked before removal (Atlas Performance Advisor not consulted)",
        "lesson_learned": "Always check Atlas Performance Advisor before dropping any index"
    },
    {
        "title": "Aggregation Pipeline $lookup Without Index Timed Out",
        "description": (
            "New reporting feature added $lookup from orders to products without an index "
            "on the foreign key. Pipeline took 45 seconds on 500K orders, "
            "causing gateway timeout on the reporting endpoint."
        ),
        "field_changed": "productId",
        "collections_affected": ["orders", "products"],
        "services_affected": ["reporting-service"],
        "fix_applied": "Added {productId:1} index to products collection. Pipeline time: 45s → 0.3s",
        "recovery_time_hours": 1,
        "severity": "P2",
        "date": (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d"),
        "root_cause": "$lookup foreign field not indexed",
        "lesson_learned": "All $lookup foreign fields must have indexes"
    },
    {
        "title": "Unindexed Sort Caused Memory Limit Exceeded Error",
        "description": (
            "Reporting query sorted 2M documents without an index on the sort field. "
            "MongoDB threw 'Executor error: OperationFailed: Sort exceeded memory limit of 100MB'."
        ),
        "field_changed": "createdAt",
        "collections_affected": ["transactions"],
        "services_affected": ["finance-reporting"],
        "fix_applied": "Added {createdAt:-1} index. Added allowDiskUse:true as temporary workaround",
        "recovery_time_hours": 3,
        "severity": "P1",
        "date": (datetime.utcnow() - timedelta(days=75)).strftime("%Y-%m-%d"),
        "root_cause": "In-memory sort limit hit on unindexed field with large result set",
        "lesson_learned": "Always index sort fields. Use allowDiskUse as emergency fallback only."
    }
]


async def seed():
    """Seeds the past_incidents collection with embeddings."""
    db = get_db()
    collection = db["past_incidents"]

    # Check if already seeded
    existing = collection.count_documents({})
    if existing > 0:
        print(f"[Seed] past_incidents already has {existing} documents. Skipping.")
        return

    print(f"[Seed] Generating embeddings for {len(PAST_INCIDENTS)} incidents...")

    # Generate embeddings for all descriptions
    descriptions = [inc["description"] for inc in PAST_INCIDENTS]
    embeddings = await get_embeddings_batch(descriptions)

    # Attach embeddings to documents
    for i, incident in enumerate(PAST_INCIDENTS):
        incident["embedding"] = embeddings[i]
        incident["created_at"] = datetime.utcnow()

    # Insert all
    result = collection.insert_many(PAST_INCIDENTS)
    print(f"[Seed] ✅ Inserted {len(result.inserted_ids)} incidents into past_incidents")
    print("[Seed] Now create the Atlas Vector Search index on 'embedding' field (1024 dims)")


if __name__ == "__main__":
    asyncio.run(seed())
