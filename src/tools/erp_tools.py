"""
NILA-V2 Custom ERP Integration Tools
------------------------------------
Provides real-time voice tools for Nila to interact with your Robuverse Custom ERP:
- Query leads & status summaries (e.g. "Is there any new lead in enquiry stage?")
- Create new ERP leads by voice
- Update lead stages (e.g. "Move Rahul's lead to WON")
"""

import json
import logging
import os
import urllib.request
import urllib.parse
from typing import Any, Dict, Optional

from src.tools.registry import register_tool

logger = logging.getLogger(__name__)

# Configurable ERP Base URL (default: http://localhost:3000 for local Next.js ERP)
ERP_API_BASE_URL = os.getenv("ERP_API_BASE_URL", "http://localhost:3000/api/nila")


# ---------------------------------------------------------------------------
# Tool 1: Check ERP Leads & Status Summary
# ---------------------------------------------------------------------------
@register_tool(
    name="check_erp_leads",
    description="Check recent leads or enquiry status in the custom ERP database (e.g., 'Is there any new lead?', 'Show leads in NEW_ENQUIRY stage').",
    parameters={
        "type": "OBJECT",
        "properties": {
            "status": {
                "type": "STRING",
                "description": "Optional filter for lead status: 'NEW_ENQUIRY', 'CONTACTED', 'REQUIREMENT_GATHERED', 'QUOTATION_SENT', 'NEGOTIATION', 'WON', 'LOST'. Default is all stages or 'NEW_ENQUIRY'.",
            },
            "limit": {
                "type": "INTEGER",
                "description": "Maximum number of recent leads to retrieve (default: 5).",
            }
        },
        "required": [],
    },
)
def check_erp_leads(status: Optional[str] = None, limit: int = 5) -> str:
    """Query ERP leads via HTTP API"""
    try:
        query_params = {}
        if status:
            query_params["status"] = status
        if limit:
            query_params["limit"] = str(limit)

        url = f"{ERP_API_BASE_URL}/leads"
        if query_params:
            url += "?" + urllib.parse.urlencode(query_params)

        req = urllib.request.Request(url, headers={"User-Agent": "Nila-V2-Robot"})
        
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                
                status_summary = data.get("statusSummary", {})
                leads = data.get("leads", [])
                
                # Format friendly summary
                summary_parts = []
                if status_summary:
                    stages = [f"{st}: {count}" for st, count in status_summary.items()]
                    summary_parts.append(f"ERP Lead Breakdown: {', '.join(stages)}.")
                
                if not leads:
                    summary_parts.append(f"No leads currently found in '{status or 'ALL'}' stage.")
                else:
                    lead_details = []
                    for l in leads:
                        val_str = f" (Value: ₹{l['estimatedValue']:,})" if l.get('estimatedValue') else ""
                        comp_str = f" from {l['company']}" if l.get('company') else ""
                        lead_details.append(f"- #{l['leadNumber']}: {l['name']}{comp_str} [{l['status']}]{val_str}")
                    summary_parts.append("Recent Leads:\n" + "\n".join(lead_details))

                res_text = "\n".join(summary_parts)
                logger.info(f"📊 [ERP LEADS QUERY SUCCESS] {len(leads)} leads returned")
                return json.dumps({
                    "status": "success",
                    "filter": status or "ALL",
                    "count": len(leads),
                    "summary": res_text,
                    "leads": leads
                }, ensure_ascii=False)
            else:
                return json.dumps({"status": "error", "message": f"ERP HTTP status {response.status}"})

    except Exception as e:
        logger.warning(f"⚠️ Could not reach ERP API at {ERP_API_BASE_URL}: {e}")
        return json.dumps({
            "status": "error",
            "message": f"ERP server offline or unreachable at {ERP_API_BASE_URL}. Ensure Next.js ERP app is running on port 3000."
        })


# ---------------------------------------------------------------------------
# Tool 2: Create New ERP Lead
# ---------------------------------------------------------------------------
@register_tool(
    name="create_erp_lead",
    description="Create a new client lead or customer enquiry directly into the custom ERP database.",
    parameters={
        "type": "OBJECT",
        "properties": {
            "name": {
                "type": "STRING",
                "description": "Client or contact person name",
            },
            "phone": {
                "type": "STRING",
                "description": "Client phone number",
            },
            "company": {
                "type": "STRING",
                "description": "Company name (optional)",
            },
            "status": {
                "type": "STRING",
                "description": "Lead stage: 'NEW_ENQUIRY', 'CONTACTED', 'REQUIREMENT_GATHERED', etc. Default: 'NEW_ENQUIRY'.",
            },
            "priority": {
                "type": "STRING",
                "description": "Priority: 'HOT', 'WARM', or 'COLD'. Default: 'WARM'.",
            },
            "estimated_value": {
                "type": "NUMBER",
                "description": "Estimated lead deal value in INR (e.g. 50000)",
            },
            "notes": {
                "type": "STRING",
                "description": "Notes or specific enquiry details",
            }
        },
        "required": ["name"],
    },
)
def create_erp_lead(
    name: str,
    phone: Optional[str] = None,
    company: Optional[str] = None,
    status: str = "NEW_ENQUIRY",
    priority: str = "WARM",
    estimated_value: float = 0.0,
    notes: Optional[str] = None
) -> str:
    """Create a new lead entry in ERP"""
    try:
        url = f"{ERP_API_BASE_URL}/leads"
        payload = {
            "name": name,
            "phone": phone,
            "company": company,
            "status": status,
            "priority": priority,
            "estimatedValue": estimated_value,
            "notes": notes
        }
        json_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=json_bytes, headers={"Content-Type": "application/json", "User-Agent": "Nila-V2-Robot"}, method="POST")

        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200 or response.status == 201:
                data = json.loads(response.read().decode("utf-8"))
                logger.info(f"✅ [ERP LEAD CREATED] {data.get('message')}")
                return json.dumps(data, ensure_ascii=False)
            else:
                return json.dumps({"status": "error", "message": f"ERP HTTP status {response.status}"})

    except Exception as e:
        logger.error(f"❌ Failed to create ERP lead: {e}")
        return json.dumps({"status": "error", "message": f"Failed to connect to ERP API: {str(e)}"})


# ---------------------------------------------------------------------------
# Tool 3: Update ERP Lead Stage / Status
# ---------------------------------------------------------------------------
@register_tool(
    name="update_erp_lead_status",
    description="Update the stage or status of an existing ERP lead (e.g. move lead to 'CONTACTED', 'WON', or 'LOST').",
    parameters={
        "type": "OBJECT",
        "properties": {
            "lead_identifier": {
                "type": "STRING",
                "description": "The lead number (e.g. 'LD-2026-001') or lead ID",
            },
            "new_status": {
                "type": "STRING",
                "description": "New lead status: 'NEW_ENQUIRY', 'CONTACTED', 'REQUIREMENT_GATHERED', 'QUOTATION_SENT', 'NEGOTIATION', 'WON', 'LOST'.",
            },
            "notes": {
                "type": "STRING",
                "description": "Optional update notes",
            }
        },
        "required": ["lead_identifier", "new_status"],
    },
)
def update_erp_lead_status(lead_identifier: str, new_status: str, notes: Optional[str] = None) -> str:
    """Update lead status in ERP"""
    try:
        url = f"{ERP_API_BASE_URL}/leads"
        payload = {
            "leadNumber": lead_identifier if lead_identifier.startswith("LD-") or not len(lead_identifier) > 20 else None,
            "leadId": lead_identifier if len(lead_identifier) > 20 and not lead_identifier.startswith("LD-") else None,
            "status": new_status,
            "notes": notes
        }
        json_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=json_bytes, headers={"Content-Type": "application/json", "User-Agent": "Nila-V2-Robot"}, method="PATCH")

        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                logger.info(f"✅ [ERP LEAD UPDATED] {data.get('message')}")
                return json.dumps(data, ensure_ascii=False)
            else:
                return json.dumps({"status": "error", "message": f"ERP HTTP status {response.status}"})

    except Exception as e:
        logger.error(f"❌ Failed to update ERP lead: {e}")
        return json.dumps({"status": "error", "message": f"Failed to connect to ERP API: {str(e)}"})
