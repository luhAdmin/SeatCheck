"""
SeatCheck configuration.

Edit this file to match your actual per-seat costs. Prices below are US list
price (monthly, USD). If you're on CSP or EA with a discount, put your actual
prices here for accurate savings numbers.

SKU reference:
https://learn.microsoft.com/en-us/entra/identity/users/licensing-service-plan-reference
"""

# Days of inactivity before we flag a user
INACTIVITY_DAYS = 90

# Per-seat monthly prices (USD, US list price). Anything not in this dict is
# treated as "unknown cost" — we still count it, just don't include in $ math.
SKU_PRICES = {
    # ── Microsoft 365 (Windows + EMS + Office) ──
    "SPE_E5": 57.00,
    "SPE_E3": 36.00,
    "SPE_F3": 8.00,
    "SPE_F1": 2.25,

    # ── Office 365 (no Windows/EMS) ──
    "ENTERPRISEPREMIUM": 38.00,   # O365 E5
    "ENTERPRISEPACK": 23.00,      # O365 E3
    "STANDARDPACK": 10.00,        # O365 E1

    # ── Business (SMB, up to 300 seats) ──
    "SPB": 22.00,                     # Business Premium
    "O365_BUSINESS_PREMIUM": 12.50,   # Business Standard
    "O365_BUSINESS_ESSENTIALS": 6.00, # Business Basic
    "O365_BUSINESS": 8.25,            # Apps for Business

    # ── Exchange standalone ──
    "EXCHANGESTANDARD": 4.00,
    "EXCHANGEENTERPRISE": 8.00,

    # ── Teams add-ons ──
    "MCOEV": 8.00,
    "MCOMEETADV": 4.00,
    "MCOPSTN1": 12.00,
    "MCOPSTN2": 24.00,
    "MCOTEAMS_ESSENTIALS": 4.00,

    # ── Entra ID ──
    "AAD_PREMIUM": 6.00,        # P1 (often bundled)
    "AAD_PREMIUM_P2": 9.00,     # P2 (often bundled)

    # ── Intune / Defender / Security ──
    "INTUNE_A": 8.00,           # Intune standalone (bundled in M365)
    "ATP_ENTERPRISE": 3.00,     # Defender for O365 P1
    "THREAT_INTELLIGENCE": 5.00, # Defender for O365 P2

    # ── Power Platform (per-user plans, NOT the free viral SKUs) ──
    "POWER_BI_PRO": 10.00,
    "POWER_BI_PREMIUM_PER_USER": 20.00,
    "POWERAPPS_PER_USER": 20.00,
    "FLOW_PER_USER": 15.00,
    "POWERAPPS_PER_APP": 5.00,

    # ── Copilot ──
    "Microsoft_365_Copilot": 30.00,

    # ── Project / Visio ──
    "PROJECTPROFESSIONAL": 30.00,
    "PROJECTPREMIUM": 55.00,
    "PROJECT_P1": 10.00,
    "VISIOCLIENT": 15.00,
    "VISIO_PLAN2_DEPT": 15.00,

    # ── Dynamics 365 — Business Central ──
    "DYN365_BUSCENTRAL_ESSENTIAL": 70.00,
    "DYN365_BUSCENTRAL_ESSENTIALS": 70.00,
    "DYN365_BUSCENTRAL_PREMIUM": 100.00,
    "DYN365_BUSCENTRAL_TEAM_MEMBER": 8.00,

    # ── Dynamics 365 — CE / Sales / Service ──
    "DYN365_ENTERPRISE_SALES": 95.00,
    "DYN365_SALES_PREMIUM": 135.00,
    "DYN365_ENTERPRISE_CUSTOMER_SERVICE": 95.00,
    "DYN365_CUSTOMER_SERVICE_ENTERPRISE": 95.00,
    "DYN365_ENTERPRISE_FIELD_SERVICE": 95.00,
    "DYN365_ENTERPRISE_TEAM_MEMBERS": 8.00,
    "DYN365_TEAM_MEMBERS": 8.00,
    "DYN365_ENTERPRISE_P1_IW": 0.00,   # trial

    # ── Free / preview / self-service — DO NOT display in inventory ──
    # These auto-provision with silly quotas (10k–1M seats) and cost nothing.
    "POWER_BI_STANDARD": 0.00,
    "FLOW_FREE": 0.00,
    "POWERAPPS_VIRAL": 0.00,
    "POWERAPPS_DEV": 0.00,
    "SPZA_IW": 0.00,
    "CCIBOTS_PRIVPREV_VIRAL": 0.00,
    "WINDOWS_STORE": 0.00,
    "Microsoft_Teams_Exploratory_Dept": 0.00,
    "TEAMS_EXPLORATORY": 0.00,
    "RMSBASIC": 0.00,
    "DYN365_FINANCIALS_ACCOUNTANT_SKU": 0.00,  # free for accountants
    "DYN365_BUSCENTRAL_EXTERNAL_ACCOUNTANT": 0.00,
    "TEAMS_FREE": 0.00,
    "WHITEBOARD_FIRSTLINE1": 0.00,
    "STREAM": 0.00,
    "MCOFREE": 0.00,
    "MEETUP_ACCOUNT": 0.00,
    "MEE_FACULTY": 0.00,
    "MEE_STUDENT": 0.00,
    "M365_LIGHTHOUSE_CUSTOMER_PLAN1": 0.00,   # MSP tool, free
    "M365_LIGHTHOUSE_PARTNER_PLAN1": 0.00,
}

# SKUs to completely HIDE from the inventory table (viral / free / infra SKUs)
# that just add noise to the report.
HIDDEN_SKUS = {
    "POWER_BI_STANDARD", "FLOW_FREE", "POWERAPPS_VIRAL", "POWERAPPS_DEV",
    "SPZA_IW", "CCIBOTS_PRIVPREV_VIRAL", "WINDOWS_STORE",
    "Microsoft_Teams_Exploratory_Dept", "TEAMS_EXPLORATORY",
    "RMSBASIC", "TEAMS_FREE", "WHITEBOARD_FIRSTLINE1", "STREAM", "MCOFREE",
    "M365_LIGHTHOUSE_CUSTOMER_PLAN1", "M365_LIGHTHOUSE_PARTNER_PLAN1",
    "DYN365_FINANCIALS_ACCOUNTANT_SKU", "DYN365_BUSCENTRAL_EXTERNAL_ACCOUNTANT",
}

# High-value SKUs worth flagging on the "watchlist" — anything expensive
# where "does this user actually need this?" is a good question to ask.
HIGH_VALUE_SKUS = {
    "SPE_E5", "ENTERPRISEPREMIUM",
    "DYN365_BUSCENTRAL_PREMIUM", "DYN365_BUSCENTRAL_ESSENTIAL",
    "DYN365_BUSCENTRAL_ESSENTIALS",
    "DYN365_ENTERPRISE_SALES", "DYN365_SALES_PREMIUM",
    "DYN365_ENTERPRISE_CUSTOMER_SERVICE", "DYN365_CUSTOMER_SERVICE_ENTERPRISE",
    "DYN365_ENTERPRISE_FIELD_SERVICE",
    "Microsoft_365_Copilot",
    "POWERAPPS_PER_USER", "POWER_BI_PREMIUM_PER_USER",
    "PROJECTPROFESSIONAL", "PROJECTPREMIUM",
}

# Human-readable names for the report
SKU_FRIENDLY_NAMES = {
    "SPE_E5": "Microsoft 365 E5",
    "SPE_E3": "Microsoft 365 E3",
    "SPE_F3": "Microsoft 365 F3",
    "SPE_F1": "Microsoft 365 F1",
    "ENTERPRISEPREMIUM": "Office 365 E5",
    "ENTERPRISEPACK": "Office 365 E3",
    "STANDARDPACK": "Office 365 E1",
    "SPB": "Microsoft 365 Business Premium",
    "O365_BUSINESS_PREMIUM": "Microsoft 365 Business Standard",
    "O365_BUSINESS_ESSENTIALS": "Microsoft 365 Business Basic",
    "O365_BUSINESS": "Microsoft 365 Apps for Business",
    "EXCHANGESTANDARD": "Exchange Online (Plan 1)",
    "EXCHANGEENTERPRISE": "Exchange Online (Plan 2)",
    "MCOEV": "Teams Phone Standard",
    "MCOMEETADV": "Audio Conferencing",
    "MCOPSTN1": "Domestic Calling Plan",
    "MCOPSTN2": "Domestic & Intl Calling",
    "MCOTEAMS_ESSENTIALS": "Teams Essentials",
    "AAD_PREMIUM": "Entra ID P1",
    "AAD_PREMIUM_P2": "Entra ID P2",
    "INTUNE_A": "Intune",
    "ATP_ENTERPRISE": "Defender for Office 365 P1",
    "THREAT_INTELLIGENCE": "Defender for Office 365 P2",
    "POWER_BI_PRO": "Power BI Pro",
    "POWER_BI_PREMIUM_PER_USER": "Power BI Premium (per user)",
    "POWERAPPS_PER_USER": "Power Apps per user",
    "FLOW_PER_USER": "Power Automate per user",
    "POWERAPPS_PER_APP": "Power Apps per app",
    "Microsoft_365_Copilot": "Microsoft 365 Copilot",
    "PROJECTPROFESSIONAL": "Project Plan 3",
    "PROJECTPREMIUM": "Project Plan 5",
    "PROJECT_P1": "Project Plan 1",
    "VISIOCLIENT": "Visio Plan 2",
    "VISIO_PLAN2_DEPT": "Visio Plan 2",
    "DYN365_BUSCENTRAL_ESSENTIAL": "Business Central Essentials",
    "DYN365_BUSCENTRAL_ESSENTIALS": "Business Central Essentials",
    "DYN365_BUSCENTRAL_PREMIUM": "Business Central Premium",
    "DYN365_BUSCENTRAL_TEAM_MEMBER": "Business Central Team Member",
    "DYN365_FINANCIALS_ACCOUNTANT_SKU": "Business Central Accountant",
    "DYN365_ENTERPRISE_SALES": "Dynamics 365 Sales Enterprise",
    "DYN365_SALES_PREMIUM": "Dynamics 365 Sales Premium",
    "DYN365_ENTERPRISE_CUSTOMER_SERVICE": "Dynamics 365 Customer Service",
    "DYN365_CUSTOMER_SERVICE_ENTERPRISE": "Dynamics 365 Customer Service",
    "DYN365_ENTERPRISE_FIELD_SERVICE": "Dynamics 365 Field Service",
    "DYN365_ENTERPRISE_TEAM_MEMBERS": "Dynamics 365 Team Members",
    "DYN365_TEAM_MEMBERS": "Dynamics 365 Team Members",
}


# ─────────────────────────────────────────────────────────────────────────────
# Downgrade suggestions per high-value SKU — what to consider instead.
# Empty string = no straightforward downgrade path (just review necessity).
# ─────────────────────────────────────────────────────────────────────────────
SKU_DOWNGRADE_SUGGESTIONS = {
    "SPE_E5": "Consider Microsoft 365 E3 (−$21/mo/user) if user doesn't need "
              "Defender for O365 P2, Power BI Pro, Audio Conferencing, or "
              "advanced security/compliance features.",
    "ENTERPRISEPREMIUM": "Consider Office 365 E3 (−$15/mo/user) if user "
                        "doesn't need Defender for O365 P2 or Power BI Pro.",
    "DYN365_BUSCENTRAL_PREMIUM": "Consider Business Central Essentials "
                                 "(−$30/mo/user) if user doesn't use "
                                 "manufacturing, service management, or "
                                 "advanced warehouse features.",
    "DYN365_BUSCENTRAL_ESSENTIAL": "Consider Business Central Team Member "
                                   "(−$62/mo/user) if user only reads data or "
                                   "does light approvals (no full transactions).",
    "DYN365_BUSCENTRAL_ESSENTIALS": "Consider Business Central Team Member "
                                    "(−$62/mo/user) if user only reads data "
                                    "or does light approvals.",
    "DYN365_ENTERPRISE_SALES": "Consider Sales Professional (−$30/mo/user) if "
                              "user doesn't need forecasting, territory "
                              "management, or advanced sales automation.",
    "DYN365_SALES_PREMIUM": "Consider Sales Enterprise (−$40/mo/user) if user "
                           "doesn't use AI-powered sales insights or "
                           "conversation intelligence.",
    "DYN365_ENTERPRISE_CUSTOMER_SERVICE": "Consider Customer Service "
                                          "Professional (−$45/mo/user) if user "
                                          "doesn't need unified routing, "
                                          "knowledge management, or SLAs.",
    "DYN365_CUSTOMER_SERVICE_ENTERPRISE": "Consider Customer Service "
                                          "Professional (−$45/mo/user) if user "
                                          "doesn't need unified routing or SLAs.",
    "DYN365_ENTERPRISE_FIELD_SERVICE": "Confirm this user is a field technician "
                                       "or dispatcher — if they only view "
                                       "records, a Team Member seat may suffice.",
    "Microsoft_365_Copilot": "Verify sustained usage — pilot Copilot seats "
                             "often go unused after 60–90 days. If usage is "
                             "occasional, consider reassigning to a heavier user.",
    "POWERAPPS_PER_USER": "If user only runs 1–2 apps, Power Apps per-app "
                          "(−$15/mo/user) is cheaper.",
    "POWER_BI_PREMIUM_PER_USER": "If user only consumes reports (doesn't "
                                 "author), Power BI Pro (−$10/mo/user) suffices.",
    "PROJECTPROFESSIONAL": "Consider Project Plan 1 (−$20/mo/user) if user "
                          "doesn't author project plans (only views/updates).",
    "PROJECTPREMIUM": "Consider Project Plan 3 (−$25/mo/user) if user doesn't "
                     "use portfolio management or demand management.",
}

# ─────────────────────────────────────────────────────────────────────────────
# Conversation prompts — what to ask this user during a renewal review.
# Kept practical and specific to the SKU.
# ─────────────────────────────────────────────────────────────────────────────
SKU_REVIEW_QUESTIONS = {
    "SPE_E5": "Do you regularly use Defender/security features, Power BI, "
              "or Audio Conferencing? If not, E3 is likely enough.",
    "ENTERPRISEPREMIUM": "Do you use Power BI Pro or advanced compliance "
                        "features? If not, Office 365 E3 is likely enough.",
    "DYN365_BUSCENTRAL_PREMIUM": "Do you use manufacturing, service management, "
                                 "or advanced warehouse features in Business "
                                 "Central? Or do you mainly work with finance, "
                                 "sales, purchasing, and basic inventory?",
    "DYN365_BUSCENTRAL_ESSENTIAL": "Do you enter transactions in Business "
                                   "Central, or mostly view reports and approve?",
    "DYN365_BUSCENTRAL_ESSENTIALS": "Do you enter transactions in Business "
                                    "Central, or mostly view reports and approve?",
    "DYN365_ENTERPRISE_SALES": "Do you use forecasting, territory management, "
                              "or advanced sales automation? Or is Dynamics "
                              "mostly a contact/deal tracker for you?",
    "DYN365_SALES_PREMIUM": "Do you actually use the AI sales insights and "
                           "conversation intelligence features?",
    "DYN365_ENTERPRISE_CUSTOMER_SERVICE": "Do you handle multi-channel cases "
                                          "with routing rules and SLAs? Or "
                                          "mostly simple ticket tracking?",
    "DYN365_CUSTOMER_SERVICE_ENTERPRISE": "Do you use unified routing and "
                                          "SLA management? Or simpler ticketing?",
    "DYN365_ENTERPRISE_FIELD_SERVICE": "Are you dispatching or performing "
                                       "field service work, or just viewing "
                                       "records?",
    "Microsoft_365_Copilot": "How often do you actually use Copilot in Word, "
                             "Excel, Outlook, or Teams? Weekly? Daily? "
                             "Occasionally?",
    "POWERAPPS_PER_USER": "How many Power Apps do you actively use? If just "
                          "1 or 2, per-app licensing is cheaper.",
    "POWER_BI_PREMIUM_PER_USER": "Do you build/publish reports, or mainly "
                                 "consume them?",
    "PROJECTPROFESSIONAL": "Do you author project plans in Project, or mainly "
                          "view timelines and update task status?",
    "PROJECTPREMIUM": "Do you use portfolio-level features (portfolio "
                     "management, demand management)?",
}