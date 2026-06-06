"""
DevSentinel — Pytest Configuration & Shared Fixtures
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Shared fixtures available to ALL test files automatically.
No imports needed — pytest discovers conftest.py automatically.
"""

import os
import sys
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# ── Ensure project root is on sys.path ────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# ── Set test environment variables BEFORE any imports ─────────────
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGODB_DB_NAME", "devsentiinel_test")
os.environ.setdefault("GEMINI_API_KEY", "test_gemini_key")
os.environ.setdefault("GITHUB_TOKEN", "test_github_token")
os.environ.setdefault("VOYAGE_API_KEY", "test_voyage_key")
os.environ.setdefault("GITHUB_WEBHOOK_SECRET", "test_webhook_secret")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SHARED FIXTURES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@pytest.fixture(scope="session")
def settings():
    """Shared Settings instance for all tests."""
    from config.settings import Settings
    return Settings()


@pytest.fixture
def mock_db():
    """
    Full mock MongoDB database.
    Each collection call returns a mock with pre-configured methods.
    """
    db = MagicMock()
    collection_mock = MagicMock()
    collection_mock.insert_one.return_value = MagicMock(inserted_id="507f1f77bcf86cd799439011")
    collection_mock.insert_many.return_value = MagicMock(inserted_ids=["id1", "id2"])
    collection_mock.update_one.return_value = MagicMock(matched_count=1, modified_count=1)
    collection_mock.find.return_value = iter([])
    collection_mock.aggregate.return_value = iter([])
    collection_mock.count_documents.return_value = 0
    collection_mock.index_information.return_value = {}
    db.__getitem__ = MagicMock(return_value=collection_mock)
    db.command.return_value = {"count": 0}
    return db


@pytest.fixture
def sample_pr_data():
    """Realistic GitHub PR data dict (mirrors what the webhook delivers)."""
    return {
        "number": 142,
        "title": "Rename payment_status to payment_state in orders collection",
        "body": "This change standardises our field naming convention.",
        "html_url": "https://github.com/myorg/myrepo/pull/142",
        "state": "open",
        "user": {"login": "developer_name", "id": 12345678},
        "head": {
            "sha": "abc123def456abc123def456abc123def456abc1",
            "ref": "feature/rename-payment-field",
        },
        "base": {"ref": "main"},
        "created_at": "2026-06-05T10:30:00Z",
        "additions": 47,
        "deletions": 47,
        "changed_files": 4,
    }


@pytest.fixture
def sample_files_changed():
    """Sample list of changed files for a schema-rename PR."""
    return [
        {
            "filename": "services/checkout.js",
            "status": "modified",
            "additions": 12,
            "deletions": 12,
            "patch": (
                "-  const status = order.payment_status;\n"
                "+  const status = order.payment_state;\n"
                "-  if (order.payment_status === 'completed') {\n"
                "+  if (order.payment_state === 'completed') {\n"
            ),
        },
        {
            "filename": "models/order.js",
            "status": "modified",
            "additions": 3,
            "deletions": 3,
            "patch": (
                "-  payment_status: { type: String },\n"
                "+  payment_state: { type: String },\n"
            ),
        },
        {
            "filename": "migrations/rename_payment_field.js",
            "status": "added",
            "additions": 20,
            "deletions": 0,
            "patch": (
                "+db.orders.updateMany({}, [{$rename: {'payment_status': 'payment_state'}}])\n"
            ),
        },
    ]


@pytest.fixture
def sample_query_files():
    """Sample changed files containing a MongoDB query (for ScaleTester)."""
    return [
        {
            "filename": "services/orders.js",
            "status": "modified",
            "additions": 8,
            "deletions": 0,
            "patch": (
                "+  const orders = await db.orders.find({\n"
                "+    customerId: customerId,\n"
                "+    status: 'active'\n"
                "+  }).sort({ createdAt: -1 }).toArray();\n"
            ),
        }
    ]


@pytest.fixture
def sample_pr_summary(sample_pr_data, sample_files_changed):
    """Full pr_summary dict as produced by HarvesterAgent."""
    return {
        "pr_id": 142,
        "pr_title": "Rename payment_status to payment_state in orders collection",
        "pr_url": "https://github.com/myorg/myrepo/pull/142",
        "pr_author": "developer_name",
        "pr_branch": "feature/rename-payment-field",
        "repo": "myorg/myrepo",
        "description": (
            "PR 142 titled 'Rename payment_status to payment_state in orders collection' "
            "modifies 3 files including services/checkout.js, models/order.js. "
            "This change involves MongoDB schema modification affecting fields: payment_status "
            "in collections: orders. Risk signals detected: rename, field, schema."
        ),
        "files_changed": sample_files_changed,
        "mongo_fields_changed": ["payment_status", "payment_state"],
        "collections_mentioned": ["orders"],
        "risk_keywords": ["rename", "field", "schema"],
        "has_schema_change": True,
        "has_query_change": False,
        "status": "pending_analysis",
        "risk_score": None,
        "matched_incidents": [],
    }


@pytest.fixture
def sample_analysis_result():
    """Sample output from AnalystAgent — CRITICAL risk with matched incident."""
    return {
        "risk_score": 0.91,
        "risk_level": "CRITICAL",
        "matched_incidents": [
            {
                "title": "Payment Status Field Rename Cascade Failure",
                "description": "Engineer renamed payment_status without updating downstream services.",
                "field_changed": "payment_status",
                "collections_affected": ["orders", "refunds", "analytics"],
                "fix_applied": "Dual-write migration",
                "recovery_time_hours": 6,
                "severity": "P0",
                "date": "2026-03-08",
                "score": 0.94,
            }
        ],
        "index_warnings": [
            "WARNING: 'payment_status' has active index 'payment_status_1' "
            "on 'orders' collection — index rebuild required after rename"
        ],
        "affected_collections": ["orders"],
        "confidence_breakdown": {
            "confidence": 0.91,
            "reference_count": 847,
            "criticality": 1.0,
            "similarity_bonus": 0.188,
        },
    }


@pytest.fixture
def sample_scale_result():
    """Sample output from ScaleTesterAgent — CRITICAL query risk."""
    return {
        "queries_found": 1,
        "overall_query_risk": "CRITICAL",
        "scale_results": [
            {
                "collection": "orders",
                "query_text": "db.orders.find({customerId: id, status: active}...)",
                "operation": "find",
                "is_collection_scan": True,
                "has_covering_index": False,
                "current_docs": 200000,
                "current_ms": 180,
                "projected_docs": 2000000,
                "projected_ms": 11400,
                "risk_level": "CRITICAL",
                "missing_index": "{customerId: 1, status: 1}",
                "recommendation": (
                    "BLOCK: This query will timeout in production. "
                    "Create compound index {customerId: 1, status: 1} BEFORE deploying."
                ),
            }
        ],
    }


@pytest.fixture
def webhook_payload_bytes():
    """Raw bytes of a GitHub webhook payload for HMAC testing."""
    payload_path = ROOT / "data" / "sample_webhook_payload.json"
    with open(payload_path, "rb") as f:
        return f.read()


@pytest.fixture
def api_client():
    """FastAPI test client with lifespan events skipped (mocked DB)."""
    from fastapi.testclient import TestClient
    from main import app

    with patch("main.get_db", return_value=MagicMock()), \
         patch("main.ping", return_value=True):
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client
