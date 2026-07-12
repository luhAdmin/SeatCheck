"""
SeatCheck — M365 License Optimizer (Phase 1)

Pulls license and usage data from Microsoft Graph, identifies over-licensed and
inactive users, and generates a PDF report showing potential savings.

Read-only. Never modifies anything in the tenant.

Usage:
    python seatcheck.py

Config comes from .env (see .env.example) and config.py (pricing + rules).
"""

import os
import sys
import io
import csv
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
import msal
from dotenv import load_dotenv
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)

from config import (
    SKU_PRICES, SKU_FRIENDLY_NAMES, HIDDEN_SKUS, HIGH_VALUE_SKUS,
    INACTIVITY_DAYS,
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. AUTH — get an access token using the app registration credentials
# ─────────────────────────────────────────────────────────────────────────────

def get_access_token(tenant_id: str, client_id: str, client_secret: str) -> str:
    """Get an app-only access token for Microsoft Graph."""
    app = msal.ConfidentialClientApplication(
        client_id=client_id,
        client_credential=client_secret,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
    )
    result = app.acquire_token_for_client(
        scopes=["https://graph.microsoft.com/.default"]
    )
    if "access_token" not in result:
        raise RuntimeError(
            f"Auth failed: {result.get('error_description', result)}"
        )
    return result["access_token"]


# ─────────────────────────────────────────────────────────────────────────────
# 2. GRAPH FETCHERS
# ─────────────────────────────────────────────────────────────────────────────

GRAPH = "https://graph.microsoft.com/v1.0"


def graph_get(url: str, token: str) -> dict:
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"})
    r.raise_for_status()
    return r.json()


def graph_get_all(url: str, token: str) -> list:
    """Follow @odata.nextLink pagination."""
    items = []
    while url:
        data = graph_get(url, token)
        items.extend(data.get("value", []))
        url = data.get("@odata.nextLink")
    return items


def fetch_report_csv(endpoint: str, token: str) -> list[dict]:
    """
    Reports endpoints return a 302 redirect to a CSV download.
    Returns list of dicts, one per row. Returns [] on failure (some reports
    aren't available in all tenants or need history to populate).
    """
    # These endpoints only accept a fixed set of periods: D7, D30, D90, D180.
    valid_periods = [7, 30, 90, 180]
    period = min(valid_periods, key=lambda p: abs(p - INACTIVITY_DAYS))

    # Try both URL styles — some endpoints prefer one, some the other.
    urls_to_try = [
        f"{GRAPH}/reports/{endpoint}(period='D{period}')",
        f"{GRAPH}/reports/{endpoint}?period=D{period}",
    ]
    last_err = None
    for url in urls_to_try:
        try:
            r = requests.get(
                url, headers={"Authorization": f"Bearer {token}"}, timeout=60
            )
            if r.status_code == 400:
                last_err = f"400 Bad Request — {r.text[:150]}"
                continue
            r.raise_for_status()
            text = r.content.decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
            return list(reader)
        except requests.RequestException as e:
            last_err = str(e)[:150]
            continue

    print(f"    ⚠  Skipping {endpoint}: {last_err}")
    print(f"       (analysis will continue without this data source)")
    return []


def fetch_tenant_data(token: str) -> dict:
    print("  → Fetching tenant licenses (subscribedSkus)...")
    skus = graph_get_all(f"{GRAPH}/subscribedSkus", token)

    print("  → Fetching users (this can take a minute on large tenants)...")
    users_url = (
        f"{GRAPH}/users?$select=id,userPrincipalName,displayName,"
        f"accountEnabled,assignedLicenses,signInActivity,userType,createdDateTime"
        f"&$top=999"
    )
    users = graph_get_all(users_url, token)

    print(f"  → Fetching {INACTIVITY_DAYS}-day active user detail...")
    active_users = fetch_report_csv("getOffice365ActiveUserDetail", token)

    print(f"  → Fetching {INACTIVITY_DAYS}-day M365 apps usage...")
    apps_usage = fetch_report_csv("getMicrosoft365AppsUserDetail", token)

    print(f"  → Fetching {INACTIVITY_DAYS}-day Teams activity...")
    teams_usage = fetch_report_csv("getTeamsUserActivityUserDetail", token)

    return {
        "skus": skus,
        "users": users,
        "active_users": active_users,
        "apps_usage": apps_usage,
        "teams_usage": teams_usage,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def is_anonymized(active_users: list[dict]) -> bool:
    """
    If tenant has concealment on, UPNs look like hex strings not emails.
    Detect by checking if any UPN contains an '@'.
    """
    if not active_users:
        return False
    sample = active_users[:20]
    has_at = any("@" in (row.get("User Principal Name") or "") for row in sample)
    return not has_at


def parse_date(s: str):
    if not s:
        return None
    try:
        # Handles both "2024-11-15" and full ISO timestamps
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def days_since(dt) -> int | None:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).days


def build_user_index(data: dict) -> dict:
    """
    Merge users + all usage reports into one dict keyed by lowercased UPN.
    """
    index = {}

    # Base user records
    for u in data["users"]:
        upn = (u.get("userPrincipalName") or "").lower()
        if not upn:
            continue
        last_signin_raw = (u.get("signInActivity") or {}).get(
            "lastSignInDateTime"
        )
        index[upn] = {
            "upn": u.get("userPrincipalName"),
            "display_name": u.get("displayName"),
            "enabled": u.get("accountEnabled", True),
            "user_type": u.get("userType", "Member"),
            "created": parse_date(u.get("createdDateTime")),
            "last_signin": parse_date(last_signin_raw),
            "assigned_skus": [
                lic["skuId"] for lic in (u.get("assignedLicenses") or [])
            ],
            "activity": {},
        }

    # Merge Office 365 activity (per-workload last activity dates)
    for row in data["active_users"]:
        upn = (row.get("User Principal Name") or "").lower()
        if upn not in index:
            continue
        index[upn]["activity"]["exchange"] = parse_date(
            row.get("Exchange Last Activity Date")
        )
        index[upn]["activity"]["onedrive"] = parse_date(
            row.get("OneDrive Last Activity Date")
        )
        index[upn]["activity"]["sharepoint"] = parse_date(
            row.get("SharePoint Last Activity Date")
        )
        index[upn]["activity"]["teams"] = parse_date(
            row.get("Teams Last Activity Date")
        )

    # Merge M365 apps activity (Word/Excel/PowerPoint/Outlook desktop+mobile+web)
    for row in data["apps_usage"]:
        upn = (row.get("User Principal Name") or "").lower()
        if upn not in index:
            continue
        index[upn]["activity"]["apps"] = parse_date(
            row.get("Last Activity Date")
        )

    # Merge Teams-specific
    for row in data["teams_usage"]:
        upn = (row.get("User Principal Name") or "").lower()
        if upn not in index:
            continue
        index[upn]["activity"]["teams_detail"] = parse_date(
            row.get("Last Activity Date")
        )

    return index


def sku_map(skus: list[dict]) -> dict:
    """Map skuId → skuPartNumber (e.g. 'SPE_E5', 'ENTERPRISEPACK')."""
    return {s["skuId"]: s["skuPartNumber"] for s in skus}


def classify_user(user: dict, sku_lookup: dict) -> dict | None:
    """
    Decide whether this user is a savings candidate. Returns None if fine,
    or a dict describing the recommendation.
    """
    sku_names = [sku_lookup.get(sid, sid) for sid in user["assigned_skus"]]
    # Filter out free/viral SKUs for cost math
    priced_skus = [s for s in sku_names if s not in HIDDEN_SKUS]
    total_monthly_cost = sum(SKU_PRICES.get(s, 0) for s in priced_skus)

    # If they hold literally no priced licenses, nothing to save.
    if total_monthly_cost == 0:
        return None

    days_signin = days_since(user["last_signin"])
    activity_dates = [d for d in user["activity"].values() if d]
    days_any_activity = min(
        (days_since(d) for d in activity_dates if d), default=None
    )

    # Skip very new accounts (< 30 days) — probably just provisioned
    if user["created"] and days_since(user["created"]) < 30:
        return None

    # ── Rule 1: DISABLED users still holding licenses ──
    if not user["enabled"]:
        return {
            "category": "Reclaim — disabled account",
            "action": f"Remove all licenses ({', '.join(priced_skus)})",
            "monthly_savings": total_monthly_cost,
            "confidence": "High",
        }

    # ── Rule 2: INACTIVE — no sign-in AND no workload activity in window ──
    # Both signals must be stale (or missing) to flag.
    inactive_signin = days_signin is None or days_signin > INACTIVITY_DAYS
    inactive_workload = (
        days_any_activity is None or days_any_activity > INACTIVITY_DAYS
    )
    if inactive_signin and inactive_workload:
        return {
            "category": f"Reclaim — no activity in {INACTIVITY_DAYS} days",
            "action": f"Remove all licenses ({', '.join(priced_skus)})",
            "monthly_savings": total_monthly_cost,
            "confidence": "High",
        }

    # ── Rule 3: E5 → E3 downgrade candidates ──
    has_e5 = "SPE_E5" in sku_names or "ENTERPRISEPREMIUM" in sku_names
    if has_e5:
        used_apps = user["activity"].get("apps")
        used_od_sp = (
            user["activity"].get("onedrive") or user["activity"].get("sharepoint")
        )
        used_teams = (
            user["activity"].get("teams") or user["activity"].get("teams_detail")
        )
        used_exchange = user["activity"].get("exchange")

        only_teams_exchange = (
            (used_teams or used_exchange) and not used_apps and not used_od_sp
        )
        if only_teams_exchange:
            e5_price = SKU_PRICES.get("SPE_E5", 57)
            e3_price = SKU_PRICES.get("SPE_E3", 36)
            return {
                "category": "Downgrade — E5 not utilized",
                "action": "Downgrade from Microsoft 365 E5 to E3",
                "monthly_savings": e5_price - e3_price,
                "confidence": "Medium",
            }

    # ── Rule 4: Business Premium light usage → review for Standard ──
    # We can't automatically detect Intune/Defender usage from Graph reports,
    # so this is a "review" flag, not a hard downgrade.
    if "SPB" in sku_names:
        # If they haven't signed in in 30+ days, worth reviewing
        if days_signin is not None and days_signin > 30 and days_signin <= INACTIVITY_DAYS:
            savings = SKU_PRICES.get("SPB", 22) - SKU_PRICES.get(
                "O365_BUSINESS_PREMIUM", 12.50
            )
            return {
                "category": "Review — light Business Premium usage",
                "action": "Consider downgrade to Business Standard (verify Intune/Defender not needed)",
                "monthly_savings": savings,
                "confidence": "Low",
            }

    return None


def analyze(data: dict) -> dict:
    """Run all analysis, return a dict of findings for the report."""
    sku_lookup = sku_map(data["skus"])
    user_index = build_user_index(data)

    # Tenant summary — licenses purchased vs assigned
    # Filter out hidden SKUs (viral / free / infra noise)
    license_summary = []
    for sku in data["skus"]:
        part = sku["skuPartNumber"]
        if part in HIDDEN_SKUS:
            continue
        name = SKU_FRIENDLY_NAMES.get(part, part)
        purchased = sku["prepaidUnits"]["enabled"]
        assigned = sku["consumedUnits"]
        unassigned = purchased - assigned
        unit_price = SKU_PRICES.get(part)  # None if unknown
        # Skip SKUs with silly quotas (>1000 purchased and unknown price =
        # almost certainly a self-service viral SKU we haven't catalogued yet)
        if unit_price is None and purchased > 1000:
            continue
        wasted_monthly = unassigned * (unit_price or 0)
        license_summary.append({
            "sku": part,
            "name": name,
            "purchased": purchased,
            "assigned": assigned,
            "unassigned": unassigned,
            "unit_price": unit_price,
            "wasted_monthly": wasted_monthly,
            "known_price": unit_price is not None,
        })

    # Sort inventory: idle-cost desc, then by name
    license_summary.sort(key=lambda r: (-r["wasted_monthly"], r["name"]))

    # Per-user recommendations
    findings = []
    for upn, user in user_index.items():
        rec = classify_user(user, sku_lookup)
        if rec:
            # Attach license list & last sign-in for the report
            user_skus = [sku_lookup.get(sid, sid) for sid in user["assigned_skus"]]
            findings.append({
                "upn": user["upn"],
                "display_name": user["display_name"],
                "enabled": user["enabled"],
                "last_signin_days": days_since(user["last_signin"]),
                "licenses": user_skus,
                **rec,
            })

    findings.sort(key=lambda f: f["monthly_savings"], reverse=True)

    # ── High-value seat watchlist ──
    # Every user holding an expensive SKU + their last activity — so the
    # customer can eyeball "does each of these people really need this?"
    watchlist = []
    for upn, user in user_index.items():
        user_skus = [sku_lookup.get(sid, sid) for sid in user["assigned_skus"]]
        high_value = [s for s in user_skus if s in HIGH_VALUE_SKUS]
        if not high_value:
            continue
        activity_dates = [d for d in user["activity"].values() if d]
        days_activity = min(
            (days_since(d) for d in activity_dates if d), default=None
        )
        watchlist.append({
            "display_name": user["display_name"],
            "upn": user["upn"],
            "high_value_skus": high_value,
            "monthly_cost": sum(SKU_PRICES.get(s, 0) for s in high_value),
            "last_signin_days": days_since(user["last_signin"]),
            "last_activity_days": days_activity,
            "enabled": user["enabled"],
        })
    watchlist.sort(key=lambda w: -w["monthly_cost"])

    # Totals
    unassigned_savings = sum(row["wasted_monthly"] for row in license_summary)
    reclaim_savings = sum(
        f["monthly_savings"] for f in findings
        if f["category"].startswith("Reclaim")
    )
    downgrade_savings = sum(
        f["monthly_savings"] for f in findings
        if f["category"].startswith("Downgrade")
    )
    review_savings = sum(
        f["monthly_savings"] for f in findings
        if f["category"].startswith("Review")
    )
    total_monthly = unassigned_savings + reclaim_savings + downgrade_savings

    return {
        "license_summary": license_summary,
        "findings": findings,
        "watchlist": watchlist,
        "totals": {
            "unassigned_monthly": unassigned_savings,
            "reclaim_monthly": reclaim_savings,
            "downgrade_monthly": downgrade_savings,
            "review_monthly": review_savings,
            "total_monthly": total_monthly,
            "total_annual": total_monthly * 12,
        },
        "anonymized": is_anonymized(data["active_users"]),
        "total_users": len(user_index),
        "licensed_users": sum(
            1 for u in user_index.values() if u["assigned_skus"]
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 4. PDF REPORT
# ─────────────────────────────────────────────────────────────────────────────

def fmt_money(n: float) -> str:
    return f"${n:,.2f}"


def build_pdf(report: dict, tenant_name: str, out_path: str):
    doc = SimpleDocTemplate(
        out_path, pagesize=letter,
        leftMargin=0.6 * inch, rightMargin=0.6 * inch,
        topMargin=0.6 * inch, bottomMargin=0.6 * inch,
    )
    styles = getSampleStyleSheet()
    story = []

    # Custom styles
    h1 = ParagraphStyle(
        "h1", parent=styles["Heading1"],
        fontSize=22, spaceAfter=6, textColor=colors.HexColor("#0F172A"),
    )
    h2 = ParagraphStyle(
        "h2", parent=styles["Heading2"],
        fontSize=13, spaceBefore=14, spaceAfter=6,
        textColor=colors.HexColor("#0F172A"),
    )
    body = ParagraphStyle(
        "body", parent=styles["Normal"], fontSize=10, leading=14,
    )
    small = ParagraphStyle(
        "small", parent=styles["Normal"], fontSize=8, leading=11,
        textColor=colors.HexColor("#64748B"),
    )
    hero_num = ParagraphStyle(
        "hero", parent=styles["Normal"], fontSize=36, leading=42,
        textColor=colors.HexColor("#059669"), alignment=0,
    )

    # ── Header ──
    story.append(Paragraph("SeatCheck License Report", h1))
    story.append(Paragraph(
        f"{tenant_name} &nbsp;·&nbsp; "
        f"Generated {datetime.now().strftime('%B %d, %Y')}",
        small,
    ))
    story.append(Spacer(1, 18))

    # ── Anonymization warning ──
    if report["anonymized"]:
        story.append(Paragraph(
            "<b>⚠ User names are anonymized in this report.</b> To see real names, "
            "an admin needs to turn off report concealment: Microsoft 365 admin "
            "center → Settings → Org settings → Reports → uncheck "
            "\"Display concealed user, group, and site names in all reports\".",
            body,
        ))
        story.append(Spacer(1, 12))

    # ── Hero savings number ──
    t = report["totals"]
    story.append(Paragraph("Estimated annual savings", body))
    story.append(Paragraph(fmt_money(t["total_annual"]), hero_num))
    story.append(Paragraph(
        f"{fmt_money(t['total_monthly'])} per month · "
        f"across {report['licensed_users']} licensed users of "
        f"{report['total_users']} total",
        small,
    ))
    story.append(Spacer(1, 18))

    # ── Breakdown ──
    breakdown_data = [
        ["Category", "Monthly", "Annual"],
        ["Unassigned licenses sitting idle",
         fmt_money(t["unassigned_monthly"]),
         fmt_money(t["unassigned_monthly"] * 12)],
        ["Inactive / disabled users to reclaim",
         fmt_money(t["reclaim_monthly"]),
         fmt_money(t["reclaim_monthly"] * 12)],
        ["Over-licensed users to downgrade",
         fmt_money(t["downgrade_monthly"]),
         fmt_money(t["downgrade_monthly"] * 12)],
        ["Total",
         fmt_money(t["total_monthly"]),
         fmt_money(t["total_annual"])],
    ]
    tbl = Table(breakdown_data, colWidths=[3.6 * inch, 1.6 * inch, 1.6 * inch])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2),
         [colors.white, colors.HexColor("#F8FAFC")]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#ECFDF5")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(tbl)

    # ── License inventory ──
    story.append(Paragraph("License inventory", h2))
    story.append(Paragraph(
        "Free viral/self-service SKUs (Power BI Free, POWERAPPS_VIRAL, etc.) "
        "are hidden. Rows without a $ figure are licenses SeatCheck doesn't "
        "have a price for — verify with your CSP invoice.",
        small,
    ))
    story.append(Spacer(1, 6))
    inv_data = [["License", "Purchased", "Assigned", "Idle", "Idle cost/mo"]]
    for row in report["license_summary"]:
        if row["known_price"]:
            idle_cost = fmt_money(row["wasted_monthly"]) if row["unassigned"] else "—"
        else:
            idle_cost = "unknown price" if row["unassigned"] else "—"
        inv_data.append([
            row["name"],
            str(row["purchased"]),
            str(row["assigned"]),
            str(row["unassigned"]),
            idle_cost,
        ])
    inv_tbl = Table(
        inv_data,
        colWidths=[2.6 * inch, 0.9 * inch, 0.9 * inch, 0.7 * inch, 1.7 * inch],
    )
    inv_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#F8FAFC")]),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(inv_tbl)

    story.append(PageBreak())

    # ── Per-user findings ──
    story.append(Paragraph("Recommendations by user", h2))
    story.append(Paragraph(
        f"{len(report['findings'])} users flagged. Sorted by monthly savings. "
        f"'High' confidence = safe to act on; 'Medium'/'Low' = review with the "
        f"user first. \"Last sign-in\" shows days since interactive sign-in "
        f"(requires AuditLog.Read.All permission).",
        small,
    ))
    story.append(Spacer(1, 8))

    if not report["findings"]:
        story.append(Paragraph(
            "No individual users flagged. Any savings above come from "
            "unassigned licenses sitting in your tenant.",
            body,
        ))
    else:
        finding_data = [[
            "User", "Last sign-in", "Recommendation", "$/mo", "Confidence"
        ]]
        for f in report["findings"][:80]:
            name = f["display_name"] or f["upn"] or "—"
            if len(name) > 28:
                name = name[:25] + "…"
            action = f["action"]
            if len(action) > 50:
                action = action[:47] + "…"
            signin = (
                f"{f['last_signin_days']}d ago"
                if f["last_signin_days"] is not None
                else "never"
            )
            finding_data.append([
                name,
                signin,
                Paragraph(action, body),
                fmt_money(f["monthly_savings"]),
                f["confidence"],
            ])
        find_tbl = Table(
            finding_data,
            colWidths=[1.8 * inch, 0.9 * inch, 2.5 * inch, 0.8 * inch, 0.8 * inch],
            repeatRows=1,
        )
        find_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#F8FAFC")]),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("ALIGN", (3, 0), (3, -1), "RIGHT"),
            ("ALIGN", (4, 0), (4, -1), "CENTER"),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(find_tbl)

        if len(report["findings"]) > 80:
            story.append(Spacer(1, 8))
            story.append(Paragraph(
                f"Showing top 80 of {len(report['findings'])} findings. "
                f"Full list available in the CSV export.",
                small,
            ))

    # ── High-value seat watchlist ──
    watchlist = report.get("watchlist", [])
    if watchlist:
        story.append(PageBreak())
        story.append(Paragraph("High-value seat watchlist", h2))
        story.append(Paragraph(
            "Every user holding an expensive license (E5, Business Central, "
            "Dynamics 365, Copilot, Power Apps per-user, etc.). Not necessarily "
            "waste — but each is worth asking \"does this person actually need "
            "this?\" during a renewal review. Sorted by monthly cost.",
            small,
        ))
        story.append(Spacer(1, 8))
        wl_data = [["User", "License(s)", "$/mo", "Last sign-in", "Last activity"]]
        for w in watchlist[:60]:
            name = w["display_name"] or w["upn"] or "—"
            if not w["enabled"]:
                name = f"{name} (disabled)"
            if len(name) > 28:
                name = name[:25] + "…"
            skus_display = ", ".join(
                SKU_FRIENDLY_NAMES.get(s, s) for s in w["high_value_skus"]
            )
            if len(skus_display) > 42:
                skus_display = skus_display[:39] + "…"
            signin = (
                f"{w['last_signin_days']}d ago"
                if w["last_signin_days"] is not None
                else "never"
            )
            activity = (
                f"{w['last_activity_days']}d ago"
                if w["last_activity_days"] is not None
                else "none"
            )
            wl_data.append([
                name,
                Paragraph(skus_display, body),
                fmt_money(w["monthly_cost"]) if w["monthly_cost"] else "?",
                signin,
                activity,
            ])
        wl_tbl = Table(
            wl_data,
            colWidths=[1.8 * inch, 2.4 * inch, 0.7 * inch, 0.9 * inch, 1.0 * inch],
            repeatRows=1,
        )
        wl_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#F8FAFC")]),
            ("ALIGN", (2, 0), (2, -1), "RIGHT"),
            ("ALIGN", (3, 0), (4, -1), "CENTER"),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(wl_tbl)
        if len(watchlist) > 60:
            story.append(Spacer(1, 6))
            story.append(Paragraph(
                f"Showing top 60 of {len(watchlist)} high-value seats.",
                small,
            ))

    # ── Footer / methodology ──
    story.append(Spacer(1, 20))
    story.append(Paragraph("How this was calculated", h2))
    story.append(Paragraph(
        f"<b>Data source:</b> Microsoft Graph usage reports, "
        f"{INACTIVITY_DAYS}-day window. Data has a 2–7 day lag inside Microsoft's "
        f"reporting pipeline — recent activity may not appear.<br/><br/>"
        f"<b>Pricing:</b> US list price. Actual savings depend on your CSP/EA "
        f"discount. Update <i>config.py</i> with your real per-seat costs for "
        f"accurate numbers.<br/><br/>"
        f"<b>Recommendation logic:</b> Users flagged only if licensed with E3, "
        f"E5, Office 365 E3/E5, or Business Premium. Downgrades assume the user's "
        f"observed usage fits the smaller SKU. Manual review recommended before "
        f"acting on Medium/Low confidence items.",
        body,
    ))

    doc.build(story)


# ─────────────────────────────────────────────────────────────────────────────
# 5. CSV EXPORT (raw findings, for whoever wants the spreadsheet)
# ─────────────────────────────────────────────────────────────────────────────

def write_findings_csv(report: dict, path: str):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "User", "UPN", "Enabled", "Last Sign-In (days ago)",
            "Category", "Recommended Action", "Monthly Savings", "Confidence",
        ])
        for r in report["findings"]:
            w.writerow([
                r["display_name"] or "",
                r["upn"] or "",
                "Yes" if r["enabled"] else "No",
                r["last_signin_days"] if r["last_signin_days"] is not None else "never",
                r["category"],
                r["action"],
                f"{r['monthly_savings']:.2f}",
                r["confidence"],
            ])


# ─────────────────────────────────────────────────────────────────────────────
# 6. MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    load_dotenv()
    tenant_id = os.getenv("TENANT_ID")
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    tenant_name = os.getenv("TENANT_NAME", "Your Tenant")

    missing = [k for k, v in {
        "TENANT_ID": tenant_id,
        "CLIENT_ID": client_id,
        "CLIENT_SECRET": client_secret,
    }.items() if not v]
    if missing:
        print(f"❌ Missing in .env: {', '.join(missing)}")
        print("   See .env.example and APP_REGISTRATION_GUIDE.md")
        sys.exit(1)

    print(f"🔐 Authenticating to tenant {tenant_id[:8]}…")
    token = get_access_token(tenant_id, client_id, client_secret)
    print("✅ Authenticated\n")

    print("📥 Pulling data from Microsoft Graph…")
    data = fetch_tenant_data(token)
    print("✅ Data pulled\n")

    print("🧮 Analyzing…")
    report = analyze(data)
    print(f"✅ Analysis complete — {len(report['findings'])} findings\n")

    # Outputs
    Path("output").mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    safe_name = "".join(c if c.isalnum() else "-" for c in tenant_name)
    pdf_path = f"output/SeatCheck-{safe_name}-{stamp}.pdf"
    csv_path = f"output/SeatCheck-{safe_name}-{stamp}.csv"

    print(f"📄 Building PDF: {pdf_path}")
    build_pdf(report, tenant_name, pdf_path)

    print(f"📊 Writing CSV: {csv_path}")
    write_findings_csv(report, csv_path)

    t = report["totals"]
    print(f"\n{'─' * 50}")
    print(f"  Estimated annual savings: ${t['total_annual']:,.2f}")
    print(f"  Monthly: ${t['total_monthly']:,.2f}")
    print(f"{'─' * 50}\n")
    print(f"✅ Done. Open {pdf_path}")


if __name__ == "__main__":
    main()
