"""
DevSentinel — Dashboard
━━━━━━━━━━━━━━━━━━━━━━━
FastAPI routes for the monitoring dashboard.
Shows live PR analyses, risk trends, and cluster health.
"""

from datetime import datetime, timedelta
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def register_dashboard(app, db, settings):
    """Registers dashboard routes on the main FastAPI app."""

    @app.get("/dashboard/stats")
    async def dashboard_stats():
        """
        Returns aggregate statistics for the dashboard UI.

        OUTPUT EXAMPLE:
          {
            "total_prs_analysed": 47,
            "critical_count": 8,
            "high_count": 15,
            "low_count": 24,
            "avg_risk_score": 0.61,
            "incidents_in_db": 6,
            "last_24h": {"prs": 3, "critical": 1}
          }
        """
        try:
            pr_col = db[settings.COLLECTION_PR_ANALYSES]
            incidents_col = db[settings.COLLECTION_PAST_INCIDENTS]

            # Aggregate PR stats
            pipeline = [
                {
                    "$group": {
                        "_id": "$risk_level",
                        "count": {"$sum": 1},
                        "avg_score": {"$avg": "$risk_score"}
                    }
                }
            ]
            risk_groups = {r["_id"]: r for r in pr_col.aggregate(pipeline)}

            # Last 24h
            since = datetime.utcnow() - timedelta(hours=24)
            recent_prs = pr_col.count_documents({"timestamp": {"$gte": since}})
            recent_critical = pr_col.count_documents({
                "timestamp": {"$gte": since},
                "risk_level": "CRITICAL"
            })

            return {
                "total_prs_analysed": pr_col.count_documents({}),
                "critical_count": risk_groups.get("CRITICAL", {}).get("count", 0),
                "high_count": risk_groups.get("HIGH", {}).get("count", 0),
                "low_count": risk_groups.get("LOW", {}).get("count", 0),
                "avg_risk_score": round(
                    sum(r.get("avg_score", 0) or 0 for r in risk_groups.values()) /
                    max(len(risk_groups), 1), 2
                ),
                "incidents_in_db": incidents_col.count_documents({}),
                "last_24h": {"prs": recent_prs, "critical": recent_critical}
            }
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    @app.get("/dashboard/recent")
    async def recent_analyses(limit: int = 10):
        """Returns the most recent PR analyses."""
        try:
            col = db[settings.COLLECTION_PR_ANALYSES]
            docs = list(
                col.find({}, {"embedding": 0})
                   .sort("timestamp", -1)
                   .limit(limit)
            )
            for d in docs:
                d["_id"] = str(d["_id"])
                if isinstance(d.get("timestamp"), datetime):
                    d["timestamp"] = d["timestamp"].isoformat()
            return {"analyses": docs}
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    @app.get("/dashboard/audit")
    async def audit_log(limit: int = 20):
        """Returns the most recent audit log entries."""
        try:
            col = db[settings.COLLECTION_AUDIT_LOG]
            docs = list(col.find({}).sort("timestamp", -1).limit(limit))
            for d in docs:
                d["_id"] = str(d["_id"])
                if isinstance(d.get("timestamp"), datetime):
                    d["timestamp"] = d["timestamp"].isoformat()
            return {"audit_log": docs}
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)
