"""
Generate the Mirage CA Baseline v2026 JSON files from the
spreadsheet data at the repo root.

Source spreadsheets (kept under /reference):
  - CA_Baseline_-_Mirage.xlsx
  - CA_Baseline_Summary_-_Mirage.xlsx

Outputs:
  - baseline/manifest.json
  - baseline/groups/*.json
  - baseline/namedLocations/*.json
  - baseline/policies/*.json
  - POLICY_INVENTORY.md (at repo root)
  - docs/inventory.html (policy catalog for GitHub Pages)
  - README.md policy table & group lists (between HTML comment markers)
  - docs/baseline/** (mirror for GitHub Pages same-origin baseline JSON)

The output JSON is an *intent* description (not a raw Graph body).
The Deploy SPA (`docs/deploy.js`) translates intent -> Graph body at
deploy time so the same definition works against any tenant.

Run from the repo root:
    python scripts/generate-baseline.py
"""

from __future__ import annotations

import html
import json
import os
import shutil
import sys
import urllib.parse
from collections import OrderedDict
from pathlib import Path


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_BASELINE = os.path.join(REPO_ROOT, "baseline")
OUT_POLICIES = os.path.join(OUT_BASELINE, "policies")
OUT_GROUPS = os.path.join(OUT_BASELINE, "groups")
OUT_NAMED_LOCATIONS = os.path.join(OUT_BASELINE, "namedLocations")
OUT_DOCS = os.path.join(REPO_ROOT, "docs")
DOCS_BASELINE = os.path.join(OUT_DOCS, "baseline")

README_POLICY_CATALOG_START = "<!-- policy-catalog:start -->"
README_POLICY_CATALOG_END = "<!-- policy-catalog:end -->"
README_GROUP_CATALOG_START = "<!-- group-catalog:start -->"
README_GROUP_CATALOG_END = "<!-- group-catalog:end -->"

PERSONA_SECTION_ORDER = (
    "All users",
    "Admins",
    "Application",
    "Service",
    "Guest",
    "Agent",
)


# ---------------------------------------------------------------------------
# Source data: the v2026 baseline taken from `CA_Baseline_-_Mirage.xlsx`
# (sheet "CA Baseline") and the summary workbook. Order matters: it drives
# the deploy order in the manifest.
# ---------------------------------------------------------------------------

POLICIES: list[dict] = [
    # ----- Persona: All users (CA1xx) -----------------------------------
    {
        "id": "CA101",
        "displayName": "Require MFA",
        "description": "Foundation control for workforce users: requires multifactor authentication on every interactive sign-in to cloud applications. Applies broadly (all users) with exclusions for break-glass, CA-wide exclusions, service principals in CA_ServiceAccount, and external/guest identities (covered by guest policies).",
        "metadata": {"criticality": "Critical", "v2Status": "Updated", "persona": "All users", "j0eyvEquivalent": "CA000 / CA200"},
        "include": {"users": "all"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass", "CA_ServiceAccount"], "guestsAndExternals": True},
        "applications": {"include": "all"},
        "conditions": {"clientAppTypes": ["all"]},
        "grant": {"operator": "OR", "builtInControls": ["mfa"]},
    },
    {
        "id": "CA102",
        "displayName": "User Risk - Require MFA + Password Change",
        "description": "Identity Protection remediation for elevated user risk (medium or high): requires MFA and a secure password change during the session. Depends on Entra ID P2 (user risk evaluations). Honors standard exclusions including guests and externals disabled for this persona.",
        "metadata": {"criticality": "Critical", "v2Status": "Updated", "persona": "All users", "j0eyvEquivalent": "CA201"},
        "include": {"users": "all"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass", "CA_ServiceAccount"], "guestsAndExternals": True},
        "applications": {"include": "all"},
        "conditions": {"userRiskLevels": ["medium", "high"], "clientAppTypes": ["all"]},
        "grant": {"operator": "AND", "builtInControls": ["mfa", "passwordChange"]},
    },
    {
        "id": "CA103",
        "displayName": "Sign-In Risk - Require MFA",
        "description": "Identity Protection challenge for risky sign-ins (medium or high): requires MFA to continue the session when Entra evaluates elevated sign-in risk. Requires Entra ID P2. Excludes universal exclusions and separates guest traffic via policy construction.",
        "metadata": {"criticality": "Critical", "v2Status": "Updated", "persona": "All users"},
        "include": {"users": "all"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass", "CA_ServiceAccount"], "guestsAndExternals": True},
        "applications": {"include": "all"},
        "conditions": {"signInRiskLevels": ["medium", "high"], "clientAppTypes": ["all"]},
        "grant": {"operator": "OR", "builtInControls": ["mfa"]},
    },
    {
        "id": "CA104",
        "displayName": "Block Legacy Authentication",
        "description": "Tenant-wide legacy authentication hardening: blocks basic authentication and legacy client protocols (for example POP, IMAP, SMTP AUTH, authenticated SMTP, and broader legacy client application types aligned with Microsoft guidance). Enables a dependable modern-auth-only posture; pair with workload-specific disables.",
        "metadata": {"criticality": "Critical", "v2Status": "Retained", "persona": "All users", "j0eyvEquivalent": "CA002"},
        "include": {"users": "all"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass", "CA_ServiceAccount"], "guestsAndExternals": True},
        "applications": {"include": "all"},
        "conditions": {"clientAppTypes": ["exchangeActiveSync", "other"]},
        "grant": {"operator": "OR", "builtInControls": ["block"]},
    },
    {
        "id": "CA105",
        "displayName": "Block Unknown Platforms",
        "description": "Device-platform allow list: denies access when the client is not Windows, macOS, iOS, Android, or Linux. Mitigates access from unmanaged or unexpected operating systems across all workloads in scope.",
        "metadata": {"criticality": "Recommended", "v2Status": "Retained", "persona": "All users", "j0eyvEquivalent": "CA204"},
        "include": {"users": "all"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass", "CA_ServiceAccount"], "guestsAndExternals": True},
        "applications": {"include": "all"},
        "conditions": {
            "platforms": {"include": ["all"], "exclude": ["windowsPhone", "windows", "macOS", "iOS", "android", "linux"]},
            "clientAppTypes": ["all"],
        },
        "grant": {"operator": "OR", "builtInControls": ["block"]},
    },
    {
        "id": "CA106",
        "displayName": "Block Outside Trusted Countries",
        "description": "Geolocation control using the TRUSTED_COUNTRIES named location. Sign-ins originating outside trusted regions are blocked unless the user is exempted via CA_TravelException (time-bounded travel). Excludes the travel exception group from the country condition so legitimate trips still work.",
        "metadata": {"criticality": "Critical", "v2Status": "Retained", "persona": "All users", "j0eyvEquivalent": "CA001"},
        "include": {"users": "all"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass", "CA_ServiceAccount", "CA_TravelException"], "guestsAndExternals": True},
        "applications": {"include": "all"},
        "conditions": {"locations": {"include": ["All"], "exclude": ["TRUSTED_COUNTRIES"]}, "clientAppTypes": ["all"]},
        "grant": {"operator": "OR", "builtInControls": ["block"]},
    },
    {
        "id": "CA107",
        "displayName": "Session Controls",
        "description": "Session tightening for standard users: enforces recurring reauthentication (twelve-hour sign-in frequency) and disallows persistent browser sessions. Applies a device filter so compliant or hybrid Entra joined devices can be handled according to organizational exception rules.",
        "metadata": {"criticality": "Recommended", "v2Status": "Updated", "persona": "All users", "j0eyvEquivalent": "CA202 / CA206"},
        "include": {"users": "all"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass", "CA_ServiceAccount"], "guestsAndExternals": True},
        "applications": {"include": "all"},
        "conditions": {
            "deviceFilter": {
                "mode": "exclude",
                "rule": "device.trustType -eq \"ServerAD\" -or device.isCompliant -eq True",
            },
            "clientAppTypes": ["all"],
        },
        "session": {"signInFrequency": {"value": 12, "type": "hours"}, "persistentBrowser": "never"},
    },
    {
        "id": "CA108",
        "displayName": "Block Cross-Device Auth Flows",
        "description": "Blocks high-abuse OAuth flows tied to phishing: denies device-code authentication and OAuth authentication transfer where supported. Exempts freshly approved enterprise device registrations that still need onboarding.",
        "metadata": {"criticality": "Critical", "v2Status": "NEW", "persona": "All users", "j0eyvEquivalent": "CA004"},
        "include": {"users": "all"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass", "CA_ServiceAccount", "CA_DeviceCodeApproved"], "guestsAndExternals": True},
        "applications": {"include": "all"},
        "conditions": {"authenticationFlows": ["deviceCodeFlow", "authenticationTransfer"], "clientAppTypes": ["all"]},
        "grant": {"operator": "OR", "builtInControls": ["block"]},
    },
    {
        "id": "CA109",
        "displayName": "Require MFA for Azure Management",
        "description": "Protects Azure resource management workloads: MFA is required whenever accessing Azure portal, CLI, REST, Infrastructure-as-Code, or other ARM-related applications. Targets the workload identity surface used to change tenant posture.",
        "metadata": {"criticality": "Recommended", "v2Status": "Retained", "persona": "All users"},
        "include": {"users": "all"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass", "CA_ServiceAccount"], "guestsAndExternals": True},
        "applications": {"include": ["azureManagement"]},
        "conditions": {"clientAppTypes": ["all"]},
        "grant": {"operator": "OR", "builtInControls": ["mfa"]},
    },
    {
        "id": "CA110",
        "displayName": "Block Malicious IPs",
        "description": "Threat-intelligence egress control: denies sign-ins that map to indicators in the MALICIOUS_IPS named location (populate with SOC or feed-driven ranges before enforcement). Complements geo and risk policies.",
        "metadata": {"criticality": "Optional", "v2Status": "Retained", "persona": "All users"},
        "include": {"users": "all"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass", "CA_ServiceAccount"], "guestsAndExternals": True},
        "applications": {"include": "all"},
        "conditions": {"locations": {"include": ["MALICIOUS_IPS"]}, "clientAppTypes": ["all"]},
        "grant": {"operator": "OR", "builtInControls": ["block"]},
    },
    {
        "id": "CA111",
        "displayName": "Continuous Access Evaluation - Standard",
        "description": "Continuous Access Evaluation baseline for workforce (standard breadth, all cloud apps): deploy resolves intent to Graph sessionControls.continuousAccessEvaluation.mode disabled (matches Entra's non-strict CAE session setting-do not confuse with policy State Off). Pair with CA603 (strict CAE / strict location). Unlike other workforce policies, guest/external exclusion cannot be applied on this CAE-session-only rule in Graph-the baseline omits guest/external exclusion here only; other policies continue to exclude guests where supported.",
        "metadata": {"criticality": "Recommended", "v2Status": "NEW", "persona": "All users", "j0eyvEquivalent": "CA209"},
        "include": {"users": "all"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass", "CA_ServiceAccount"]},
        "applications": {"include": "all"},
        "conditions": {"clientAppTypes": ["all"]},
        "session": {"continuousAccessEvaluation": "standard"},
    },
    {
        "id": "CA112",
        "displayName": "MFA on Device Register or Join",
        "description": "Strengthens Entra device registration and join endpoints: MFA is required anytime a user completes device registration or Workplace Join/Azure AD join workflows, reducing unauthorized device onboarding.",
        "metadata": {"criticality": "Critical", "v2Status": "NEW", "persona": "All users", "j0eyvEquivalent": "CA003"},
        "include": {"users": "all"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass", "CA_ServiceAccount", "AUTOPILOT_DevicePrep"], "guestsAndExternals": True},
        "applications": {"userActions": ["urn:user:registerdevice"]},
        "conditions": {"clientAppTypes": ["all"]},
        "grant": {"operator": "OR", "builtInControls": ["mfa"]},
    },
    {
        "id": "CA113",
        "displayName": "Require Token Protection (Pilot)",
        "description": "Pilot control binding primary refresh tokens more tightly on supported Windows workloads (token protection). Limits token replay when adversaries steal session material via phishing proxies. Applies only to the CA_TokenProtection_Pilot group\u2014expand deliberately after telemetry review.",
        "metadata": {"criticality": "Optional", "v2Status": "NEW", "persona": "All users"},
        "include": {"groups": ["CA_TokenProtection_Pilot"]},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass"]},
        "applications": {"include": ["exchangeOnline", "sharePointOnline", "teams"]},
        "conditions": {"platforms": {"include": ["windows"]}, "clientAppTypes": ["browser", "mobileAppsAndDesktopClients"]},
        "session": {"tokenProtectionEnforced": True},
    },
    {
        "id": "CA114",
        "displayName": "Terms of Use",
        "description": "Regulatory / policy attestation workflow: prompts users for Microsoft Entra Terms of Use before access. Organizations must provision a tenant-specific Terms of Use object and inject its GUID at deployment time (see deploy SPA configuration).",
        "metadata": {"criticality": "Optional", "v2Status": "Retained", "persona": "All users"},
        "include": {"users": "all"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass", "CA_ServiceAccount"], "guestsAndExternals": True},
        "applications": {"include": "all"},
        "conditions": {"clientAppTypes": ["all"]},
        "grant": {"operator": "OR", "termsOfUse": ["TOU_default"]},
        "skipIfMissing": ["termsOfUse:TOU_default"],
    },
    # ----- Persona: All users - device tracks (CA2xx, CA3xx) ------------
    {
        "id": "CA201",
        "displayName": "Intune Enrolling - Require MFA",
        "description": "Secures enrollment into Microsoft Intune: MFA is mandated when enrolling a freshly managed endpoint so attackers cannot silently attach devices without strong proof of possession.",
        "metadata": {"criticality": "Critical", "v2Status": "Retained", "persona": "All users", "j0eyvEquivalent": "CA203"},
        "include": {"users": "all"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass", "CA_ServiceAccount", "AUTOPILOT_DevicePrep"], "guestsAndExternals": True},
        "applications": {"include": ["intuneEnrollment"]},
        "conditions": {"clientAppTypes": ["all"]},
        "grant": {"operator": "OR", "builtInControls": ["mfa"]},
    },
    {
        "id": "CA202",
        "displayName": "Require App Protection (Mobile)",
        "description": "Mobile application protection posture for Microsoft 365: requires Intune App Protection Policies on iOS and Android M365 workloads. Matches Microsoft\u2019s APP enforcement model (replaces fragile approved-client-app keyword matching).",
        "metadata": {"criticality": "Critical", "v2Status": "Updated", "persona": "All users", "j0eyvEquivalent": "CA005 / CA006"},
        "include": {"users": "all"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass", "CA_ServiceAccount"], "guestsAndExternals": True},
        "applications": {"include": ["office365"]},
        "conditions": {"platforms": {"include": ["iOS", "android"]}, "clientAppTypes": ["all"]},
        "grant": {"operator": "OR", "builtInControls": ["compliantApplication"]},
    },
    {
        "id": "CA204",
        "displayName": "Require Compliant Mobile (Optional MDM track)",
        "description": "Optional hardened path for supervised mobile fleets: complements CA202 by requiring Intune-compliant devices on MDM-enrolled handhelds running iOS/Android. Omit or soften if you intentionally stay app-protection-only without enrollment.",
        "metadata": {"criticality": "Optional", "v2Status": "NEW", "persona": "All users"},
        "include": {"users": "all"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass", "CA_ServiceAccount"], "guestsAndExternals": True},
        "applications": {"include": "all"},
        "conditions": {"platforms": {"include": ["iOS", "android"]}, "clientAppTypes": ["all"]},
        "grant": {"operator": "OR", "builtInControls": ["compliantDevice"]},
    },
    {
        "id": "CA301",
        "displayName": "Require Compliant Windows",
        "description": "Corporate Windows laptops and desktops must be Entra hybrid joined or marked Intune-compliant before granting access to Microsoft 365 and related cloud apps.",
        "metadata": {"criticality": "Critical", "v2Status": "Updated", "persona": "All users", "j0eyvEquivalent": "CA205"},
        "include": {"users": "all"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass", "CA_ServiceAccount"], "guestsAndExternals": True},
        "applications": {"include": "all"},
        "conditions": {"platforms": {"include": ["windows"]}, "clientAppTypes": ["all"]},
        "grant": {"operator": "OR", "builtInControls": ["compliantDevice", "domainJoinedDevice"]},
    },
    {
        "id": "CA302",
        "displayName": "Require Compliant macOS",
        "description": "Same enforcement as CA301 scoped to macOS clients: unmanaged Macs cannot access Microsoft 365 data until they enroll and report healthy compliance posture.",
        "metadata": {"criticality": "Critical", "v2Status": "Updated", "persona": "All users", "j0eyvEquivalent": "CA208"},
        "include": {"users": "all"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass", "CA_ServiceAccount"], "guestsAndExternals": True},
        "applications": {"include": "all"},
        "conditions": {"platforms": {"include": ["macOS"]}, "clientAppTypes": ["all"]},
        "grant": {"operator": "OR", "builtInControls": ["compliantDevice"]},
    },
    {
        "id": "CA303",
        "displayName": "Limited Browser Access on Unmanaged Devices",
        "description": "Reduces unmanaged-device blast radius under Microsoft 365: browser sessions can remain read-only/view-like against Exchange Online / SharePoint when the device fails the trusted workstation filter yet still needs lightweight productivity.",
        "metadata": {"criticality": "Recommended", "v2Status": "Updated", "persona": "All users"},
        "include": {"users": "all"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass", "CA_ServiceAccount"], "guestsAndExternals": True},
        "applications": {"include": ["office365"]},
        "conditions": {
            "clientAppTypes": ["browser"],
            "deviceFilter": {
                "mode": "exclude",
                "rule": "device.trustType -eq \"ServerAD\" -or device.isCompliant -eq True",
            },
        },
        "session": {"applicationEnforcedRestrictions": True},
    },
    {
        "id": "CA304",
        "displayName": "Require Compliant Linux",
        "description": "Closes the Linux User-Agent spoof gap left by the platform-scoped CA301/CA302/CA204 compliance gates. The CA platform condition is parsed from the (self-reported) User-Agent string; without CA304, an attacker holding stolen credentials can present User-Agent: Linux, satisfy CA101 MFA, and skip every device-compliance requirement (CA606 still covers admins). CA304 forces compliantDevice for any UA claiming Linux. No domainJoinedDevice grant: Entra hybrid join is Windows-only. Pre-requisite: Intune for Linux compliance policies on Ubuntu / RHEL desktops; if you do not run managed Linux endpoints, prefer dropping linux from CA105's exclude list to block the platform outright.",
        "metadata": {"criticality": "Critical", "v2Status": "NEW", "persona": "All users"},
        "include": {"users": "all"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass", "CA_ServiceAccount"], "guestsAndExternals": True},
        "applications": {"include": "all"},
        "conditions": {"platforms": {"include": ["linux"]}, "clientAppTypes": ["all"]},
        "grant": {"operator": "OR", "builtInControls": ["compliantDevice"]},
    },
    # ----- Persona: Admins (CA6xx) --------------------------------------
    {
        "id": "CA601",
        "displayName": "Phishing-Resistant MFA for Admins",
        "description": "Privileged role assignments (Azure AD Directory Roles, Delegated Administrative Partners, cloud-only role-backed accounts) must use phishing-resistant MFA (FIDO2, Windows Hello for Business with attestation, or federated certificate-based authentication where applicable).",
        "metadata": {"criticality": "Critical", "v2Status": "Updated", "persona": "Admins", "j0eyvEquivalent": "CA100 / CA101 / CA105"},
        "include": {"roles": "privilegedAdmins"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass", "CA_ServiceAccount"]},
        "applications": {"include": "all"},
        "conditions": {"clientAppTypes": ["all"]},
        "grant": {"operator": "OR", "authenticationStrength": "phishingResistantMfa"},
    },
    {
        "id": "CA602",
        "displayName": "Admin Session Controls",
        "description": "Admin session containment: repeats the tighter session controls applied to privileged accounts\u2014maximum four-hour recurring authentication and disallow persistent browser sessions\u2014for every identity holding directory or workload admin roles included in Privileged Administrators.",
        "metadata": {"criticality": "Critical", "v2Status": "Updated", "persona": "Admins", "j0eyvEquivalent": "CA102 / CA103"},
        "include": {"roles": "privilegedAdmins"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass", "CA_ServiceAccount"]},
        "applications": {"include": "all"},
        "conditions": {"clientAppTypes": ["all"]},
        "session": {"signInFrequency": {"value": 4, "type": "hours"}, "persistentBrowser": "never"},
    },
    {
        "id": "CA603",
        "displayName": "Admin CAE - Strict",
        "description": "Strict Continuous Access Evaluation for privileged identities paired with Conditional Access Strict Location evaluation: reacts immediately to IP deltas and high-sensitivity revocation signals suitable for Tier-0 workloads. Evaluate change windows carefully given Real Time CAE telemetry requirements.",
        "metadata": {"criticality": "Critical", "v2Status": "NEW", "persona": "Admins", "j0eyvEquivalent": "CA104"},
        "include": {"roles": "privilegedAdmins"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass", "CA_ServiceAccount"]},
        "applications": {"include": "all"},
        "conditions": {"clientAppTypes": ["all"]},
        "session": {"continuousAccessEvaluation": "strict"},
    },
    {
        "id": "CA604",
        "displayName": "Admin Block High User Risk",
        "description": "Break-glass for risky operators: denies admin role holders when Entra Identity Protection marks the user risky at high severity. Keeps admins from deepening compromise while investigative controls run.",
        "metadata": {"criticality": "Critical", "v2Status": "NEW", "persona": "Admins"},
        "include": {"roles": "privilegedAdmins"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass", "CA_ServiceAccount"]},
        "applications": {"include": "all"},
        "conditions": {"userRiskLevels": ["high"], "clientAppTypes": ["all"]},
        "grant": {"operator": "OR", "builtInControls": ["block"]},
    },
    {
        "id": "CA605",
        "displayName": "Admin Block High Sign-In Risk",
        "description": "Complements CA604 using sign-in risk for administrators: denies access when Identity Protection observes high sign-in risk, closing scenarios where compromised tokens still pass user-risk heuristics slowly.",
        "metadata": {"criticality": "Critical", "v2Status": "NEW", "persona": "Admins"},
        "include": {"roles": "privilegedAdmins"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass", "CA_ServiceAccount"]},
        "applications": {"include": "all"},
        "conditions": {"signInRiskLevels": ["high"], "clientAppTypes": ["all"]},
        "grant": {"operator": "OR", "builtInControls": ["block"]},
    },
    {
        "id": "CA606",
        "displayName": "Admin Require Compliant or Joined Device",
        "description": "Device trust bar for admins: privileged changes may only originate from Hybrid Entra Joined workstations or devices reporting compliant posture to Intune, preventing lateral movement from unmanaged kit.",
        "metadata": {"criticality": "Critical", "v2Status": "NEW", "persona": "Admins"},
        "include": {"roles": "privilegedAdmins"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass", "CA_ServiceAccount"]},
        "applications": {"include": "all"},
        "conditions": {"clientAppTypes": ["all"]},
        "grant": {"operator": "OR", "builtInControls": ["compliantDevice", "domainJoinedDevice"]},
    },
    # ----- Persona: Application (CA7xx) --------------------------------
    {
        "id": "CA701",
        "displayName": "App - FortiClient - MFA",
        "description": "Zero Trust gate for perimeter VPN integrations (Fortinet FortiClient in template form): MFA before granting network tunnel access aligned with phishing-resistant MFA investments elsewhere.",
        "metadata": {"criticality": "Optional", "v2Status": "Retained", "persona": "Application"},
        "include": {"users": "all"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass", "CA_ServiceAccount"], "guestsAndExternals": True},
        "applications": {"include": ["FortiClient SSO"], "lookup": "servicePrincipal"},
        "conditions": {"clientAppTypes": ["all"]},
        "grant": {"operator": "OR", "builtInControls": ["mfa"]},
        "session": {"signInFrequency": {"value": 4, "type": "hours"}},
        "skipIfMissing": ["servicePrincipal:FortiClient SSO"],
    },
    {
        "id": "CA702",
        "displayName": "App - Salesforce - MFA",
        "description": "SaaS control for Salesforce: interactive users must satisfy MFA whenever accessing Salesforce through Entra  SSO. Requires a valid enterprise application / service principal in the tenant reflecting production URLs.",
        "metadata": {"criticality": "Optional", "v2Status": "Retained", "persona": "Application"},
        "include": {"users": "all"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass", "CA_ServiceAccount"], "guestsAndExternals": True},
        "applications": {"include": ["Salesforce"], "lookup": "servicePrincipal"},
        "conditions": {"clientAppTypes": ["all"]},
        "grant": {"operator": "OR", "builtInControls": ["mfa"]},
        "skipIfMissing": ["servicePrincipal:Salesforce"],
    },
    # ----- Persona: Service (CA8xx) -------------------------------------
    {
        "id": "CA801",
        "displayName": "Service - Require MFA (Interactive)",
        "description": "Service principal hardening subset: mandates MFA whenever the delegated application signs in interactively (think human-driven scripts). Daemon / client-credential workloads remain out of scope via negative group conditioning paired with exclusions.",
        "metadata": {"criticality": "Recommended", "v2Status": "Updated", "persona": "Service", "j0eyvEquivalent": "CA300"},
        "include": {"groups": ["CA_ServiceAccount_Interactive"]},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass", "CA_ServiceAccount_NonInteractive"]},
        "applications": {"include": "all"},
        "conditions": {"clientAppTypes": ["all"]},
        "grant": {"operator": "OR", "builtInControls": ["mfa"]},
    },
    {
        "id": "CA802",
        "displayName": "Service - Block Outside Trusted IPs",
        "description": "Network perimeter for unattended automation: restricts allowed sign-ins for centralized service principals to the corporate or partner IP ranges modeled in SVC_TRUSTED_IPS, blocking roaming or hostile networks.",
        "metadata": {"criticality": "Critical", "v2Status": "Retained", "persona": "Service", "j0eyvEquivalent": "CA301"},
        "include": {"groups": ["CA_ServiceAccount"]},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass"]},
        "applications": {"include": "all"},
        "conditions": {"locations": {"include": ["All"], "exclude": ["SVC_TRUSTED_IPS"]}, "clientAppTypes": ["all"]},
        "grant": {"operator": "OR", "builtInControls": ["block"]},
    },
    {
        "id": "CA803",
        "displayName": "Service - Block Legacy Auth",
        "description": "Defense-in-depth block on legacy protocols for workloads using service principals: reinforces CA104 baseline by narrowly scoping SMTP AUTH/similar exposures that often slip through scripted automation identities.",
        "metadata": {"criticality": "Recommended", "v2Status": "Retained", "persona": "Service"},
        "include": {"groups": ["CA_ServiceAccount"]},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass"]},
        "applications": {"include": "all"},
        "conditions": {"clientAppTypes": ["exchangeActiveSync", "other"]},
        "grant": {"operator": "OR", "builtInControls": ["block"]},
    },
    {
        "id": "CA804",
        "displayName": "Service - Block Non-M365 Apps",
        "description": "Least-privilege SaaS stance for robotic identities: confines service credentials to approved Microsoft 365 applications while denying access to tertiary SaaS and consumer OAuth clients.",
        "metadata": {"criticality": "Recommended", "v2Status": "Retained", "persona": "Service"},
        "include": {"groups": ["CA_ServiceAccount"]},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass"]},
        "applications": {"include": "all", "exclude": ["office365"]},
        "conditions": {"clientAppTypes": ["all"]},
        "grant": {"operator": "OR", "builtInControls": ["block"]},
    },
    # ----- Persona: Guest (CA9xx) ---------------------------------------
    {
        "id": "CA901",
        "displayName": "Guest - Require MFA",
        "description": "Guest/B2B collaboration MFA: ensures every federated partner user proves MFA freshness in your tenant, closing the reliance on weaker home-tenant MFA states alone.",
        "metadata": {"criticality": "Critical", "v2Status": "Retained", "persona": "Guest", "j0eyvEquivalent": "CA400"},
        "include": {"users": "guestsAndExternals"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass"]},
        "applications": {"include": "all"},
        "conditions": {"clientAppTypes": ["all"]},
        "grant": {"operator": "OR", "builtInControls": ["mfa"]},
    },
    {
        "id": "CA902",
        "displayName": "Guest - Block High Sign-In Risk",
        "description": "Guest risk remediation: denies high sign-in-risk events even when the guest\u2019s home tenant is lenient (defense against cross-tenant token theft).",
        "metadata": {"criticality": "Recommended", "v2Status": "Updated", "persona": "Guest"},
        "include": {"users": "guestsAndExternals"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass"]},
        "applications": {"include": "all"},
        "conditions": {"signInRiskLevels": ["high"], "clientAppTypes": ["all"]},
        "grant": {"operator": "OR", "builtInControls": ["block"]},
    },
    {
        "id": "CA903",
        "displayName": "Guest - Block Legacy Auth",
        "description": "Prevents scripted or legacy-protocol abuse for guest personas; layered with CA901 to mandate modern apps and interactive controls.",
        "metadata": {"criticality": "Recommended", "v2Status": "Retained", "persona": "Guest"},
        "include": {"users": "guestsAndExternals"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass"]},
        "applications": {"include": "all"},
        "conditions": {"clientAppTypes": ["exchangeActiveSync", "other"]},
        "grant": {"operator": "OR", "builtInControls": ["block"]},
    },
    {
        "id": "CA904",
        "displayName": "Guest - Block Outside Trusted Countries",
        "description": "Geographic guardrail for collaborators: restricts guest access paths to countries mirrored in trusted named locations (typically broader lists than workforce policies). Pair with onboarding guidance for visiting partners.",
        "metadata": {"criticality": "Critical", "v2Status": "Retained", "persona": "Guest"},
        "include": {"users": "guestsAndExternals"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass"]},
        "applications": {"include": "all"},
        "conditions": {"locations": {"include": ["All"], "exclude": ["TRUSTED_COUNTRIES"]}, "clientAppTypes": ["all"]},
        "grant": {"operator": "OR", "builtInControls": ["block"]},
    },
    {
        "id": "CA905",
        "displayName": "Guest - Block Non-Collaboration Apps",
        "description": "Data-exfiltration control for guests collaborating in Microsoft Teams/Groups: confines Office 365 workloads while blocking ancillary SaaS (except explicitly excluded apps such as delegated admin workloads).",
        "metadata": {"criticality": "Critical", "v2Status": "Retained", "persona": "Guest", "j0eyvEquivalent": "CA401"},
        "include": {"users": "guestsAndExternals"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass", "CA_MSP_PartnerUsers"]},
        "applications": {"include": "all", "exclude": ["office365"]},
        "conditions": {"clientAppTypes": ["all"]},
        "grant": {"operator": "OR", "builtInControls": ["block"]},
    },
    {
        "id": "CA906",
        "displayName": "Guest - Terms of Use",
        "description": "Guest-visible Terms-of-Use acknowledgement for contractual or jurisdictional onboarding before accessing shared resources.",
        "metadata": {"criticality": "Optional", "v2Status": "Retained", "persona": "Guest"},
        "include": {"users": "guestsAndExternals"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass"]},
        "applications": {"include": "all"},
        "conditions": {"clientAppTypes": ["all"]},
        "grant": {"operator": "OR", "termsOfUse": ["TOU_guest"]},
        "skipIfMissing": ["termsOfUse:TOU_guest"],
    },
    {
        "id": "CA907",
        "displayName": "Guest - Session Controls",
        "description": "Session hygiene for collaborators: aligns guest browser sessions with the twelve-hour MFA refresh posture so stolen guest tokens degrade quickly\u2014mirroring CA107 protections for internals.",
        "metadata": {"criticality": "Recommended", "v2Status": "NEW", "persona": "Guest", "j0eyvEquivalent": "CA402 / CA403"},
        "include": {"users": "guestsAndExternals"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "BG_BreakGlass"]},
        "applications": {"include": "all"},
        "conditions": {"clientAppTypes": ["all"]},
        "session": {"signInFrequency": {"value": 12, "type": "hours"}, "persistentBrowser": "never"},
    },
    # ----- Persona: Agent (CAA01) ---------------------------------------
    {
        "id": "CAA01",
        "displayName": "Agent - Block High Risk",
        "description": "Workload identities (service principals using agent delegation) flagged high risk by Identity Protection lose access immediately across cloud apps targeted by the workload persona until risk clears.",
        "metadata": {"criticality": "Recommended", "v2Status": "NEW", "persona": "Agent", "j0eyvEquivalent": "CA501"},
        "include": {"agentIds": "all"},
        "exclude": {"groups": ["CA_ExcludedFromCA", "CA_ExcludedAgents"]},
        "applications": {"include": "all"},
        "conditions": {"agentIdRiskLevels": ["high"], "clientAppTypes": ["all"]},
        "grant": {"operator": "OR", "builtInControls": ["block"]},
    },
]


# Microsoft Entra policy display name: "{id} - {shortTitle}" (composed when writing
# baseline JSON; the id appears once in the portal title, not embedded twice).
_PORTAL_POLICY_TITLE_SEP = " - "


def _portal_policy_display_name(policy_id: str, short_title: str) -> str:
    """Full policy displayName as stored under baseline/policies/ and sent to Graph."""
    t = (short_title or "").strip()
    if not policy_id:
        return t
    prefixed_em = f"{policy_id}{_PORTAL_POLICY_TITLE_SEP}"
    prefixed_hy = f"{policy_id} - "
    if t.startswith(prefixed_em) or t.startswith(prefixed_hy):
        return t
    return prefixed_em + t if t else policy_id


def _policy_intent_for_disk(p: dict) -> dict:
    """Policy record as written to disk (adds id prefix to displayName once)."""
    out = dict(p)
    pid = out.get("id")
    if pid and isinstance(out.get("displayName"), str):
        out["displayName"] = _portal_policy_display_name(pid, out["displayName"])
    return out


# ---------------------------------------------------------------------------
# Groups required by the baseline. Mailnickname uses a stable slug.
# ---------------------------------------------------------------------------

GROUPS: list[dict] = [
    {
        "displayName": "BG_BreakGlass",
        "description": (
            "Break-glass and other emergency administrator accounts that must remain reachable if Conditional Access "
            "misconfiguration locks out normal admins. Keep membership empty until accounts exist; remove members when "
            "not actively needed. Excluded from nearly all CA policies so use only for documented recovery procedures."
        ),
        "mailNickname": "bg-breakglass",
        "tier": "required",
    },
    {
        "displayName": "CA_ExcludedFromCA",
        "description": (
            "Catch-all exclusion for identities that must never be evaluated by user-facing CA (for example certain "
            "directory sync or legacy integration principals your vendor documents as CA-exempt). Treat membership as "
            "highly privileged-every account here bypasses most workforce controls."
        ),
        "mailNickname": "ca-excludedfromca",
        "tier": "required",
    },
    {
        "displayName": "CA_ServiceAccount",
        "description": (
            "Parent group for non-human and automation accounts. Policies that target all users exclude this group "
            "so background jobs are not forced through interactive MFA. Nest members into the interactive vs "
            "non-interactive child groups so CA801 can target only human-driven service logons."
        ),
        "mailNickname": "ca-serviceaccount",
        "tier": "required",
    },
    {
        "displayName": "CA_ServiceAccount_Interactive",
        "description": (
            "Service principals or managed identities that sometimes sign in through a browser or device-code style "
            "flow. CA801 requires MFA for this population while leaving pure client-credential automation in the "
            "non-interactive sibling group."
        ),
        "mailNickname": "ca-serviceaccount-interactive",
        "tier": "service-tracks",
    },
    {
        "displayName": "CA_ServiceAccount_NonInteractive",
        "description": (
            "Automation identities that only use client credentials, managed identity, or other non-interactive OAuth "
            "flows. Excluded from CA801 so scheduled jobs are not blocked; pair with CA802-CA804 for network and app "
            "restrictions."
        ),
        "mailNickname": "ca-serviceaccount-noninteractive",
        "tier": "service-tracks",
    },
    {
        "displayName": "CA_TravelException",
        "description": (
            "Short-lived membership for employees who must sign in from outside TRUSTED_COUNTRIES during approved "
            "travel. CA106 excludes this group from the country condition so the geofence still applies to everyone "
            "else; expire memberships when the trip ends."
        ),
        "mailNickname": "ca-travelexception",
        "tier": "exception",
    },
    {
        "displayName": "CA_DeviceCodeApproved",
        "description": (
            "Rare allowance for CA108's block on device-code and authentication-transfer flows (for example controlled "
            "kiosk or DevOps scenarios). Add only fully trusted principals; every member is a phishing surface."
        ),
        "mailNickname": "ca-devicecodeapproved",
        "tier": "exception",
    },
    {
        "displayName": "CA_TokenProtection_Pilot",
        "description": (
            "Users or devices included in the CA113 Windows token-protection pilot. Start with a small population, "
            "collect sign-in and help-desk telemetry, then expand membership as your estate supports the feature."
        ),
        "mailNickname": "ca-tokenprotection-pilot",
        "tier": "pilot",
    },
    {
        "displayName": "CA_ExcludedAgents",
        "description": (
            "Workload agent or service principal objects that must not be blocked by CAA01 when Identity Protection "
            "flags them high risk (for example monitored automation with known false positives). Keep the group tiny "
            "and review quarterly."
        ),
        "mailNickname": "ca-excludedagents",
        "tier": "exception",
    },
    {
        "displayName": "CA_MSP_PartnerUsers",
        "description": (
            "Delegated administrator or partner accounts that need access to Microsoft 365 admin experiences blocked for "
            "standard guests in CA905. Requires explicit lifecycle: remove access when the engagement ends."
        ),
        "mailNickname": "ca-msp-partnerusers",
        "tier": "exception",
    },
    {
        "displayName": "AUTOPILOT_DevicePrep",
        "description": (
            "Device objects undergoing Windows Autopilot pre-provisioning so they can complete join/enrollment "
            "without triggering CA112 MFA-on-join or CA201 enrollment MFA prematurely. Clean up stale device members "
            "after deployment finishes."
        ),
        "mailNickname": "autopilot-deviceprep",
        "tier": "exception",
    },
]


# ---------------------------------------------------------------------------
# Named locations (placeholders - admins customise after deploy).
# ---------------------------------------------------------------------------

NAMED_LOCATIONS: list[dict] = [
    {
        "displayName": "TRUSTED_COUNTRIES",
        "type": "country",
        "countriesAndRegions": ["CA", "US"],
        "includeUnknownCountriesAndRegions": False,
        "_note": "Defaults to CA, US. Add or remove ISO 3166-1 alpha-2 codes for your operational footprint.",
    },
    {
        "displayName": "TRUSTED_IPS",
        "type": "ip",
        "isTrusted": True,
        "ipRanges": ["99.99.99.99/32"],
        "_note": "PLACEHOLDER. Replace 99.99.99.99/32 with the actual office / corporate IP ranges before enabling any policy that depends on this location.",
    },
    {
        "displayName": "SVC_TRUSTED_IPS",
        "type": "ip",
        "isTrusted": True,
        "ipRanges": ["99.99.99.99/32"],
        "_note": "PLACEHOLDER. Replace 99.99.99.99/32 with the IP ranges from which service accounts may sign in.",
    },
    {
        "displayName": "MALICIOUS_IPS",
        "type": "ip",
        "isTrusted": False,
        "ipRanges": ["99.99.99.99/32"],
        "_note": "PLACEHOLDER. Replace 99.99.99.99/32 with known-bad IPs / threat feed exports.",
    },
]


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------

def _write_json(path: str, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def write_groups() -> list[str]:
    written = []
    for g in GROUPS:
        path = os.path.join(OUT_GROUPS, g["displayName"] + ".json")
        _write_json(path, g)
        written.append(os.path.basename(path))
    return written


def write_named_locations() -> list[str]:
    written = []
    for n in NAMED_LOCATIONS:
        path = os.path.join(OUT_NAMED_LOCATIONS, n["displayName"] + ".json")
        _write_json(path, n)
        written.append(os.path.basename(path))
    return written


def write_policies() -> list[str]:
    written = []
    for p in POLICIES:
        path = os.path.join(OUT_POLICIES, p["id"] + ".json")
        _write_json(path, _policy_intent_for_disk(p))
        written.append(os.path.basename(path))
    wanted = set(written)
    for name in os.listdir(OUT_POLICIES):
        if name.endswith(".json") and name not in wanted:
            os.remove(os.path.join(OUT_POLICIES, name))
    return written


def write_manifest(groups, named_locations, policies) -> None:
    manifest = OrderedDict()
    manifest["$schemaVersion"] = "1.0"
    manifest["baseline"] = "Mirage CA Baseline v2026"
    manifest["source"] = {
        "policyMatrix": "reference/CA_Baseline_-_Mirage.xlsx",
        "summary": "reference/CA_Baseline_Summary_-_Mirage.xlsx",
        "runbook": "reference/CA_Baseline_-_Runbook.xlsx",
    }
    manifest["deployState"] = "enabledForReportingButNotEnforced"
    manifest["order"] = ["groups", "namedLocations", "policies"]
    manifest["groups"] = groups
    manifest["namedLocations"] = named_locations
    manifest["policies"] = policies
    _write_json(os.path.join(OUT_BASELINE, "manifest.json"), manifest)

def write_policy_inventory(policy_filenames: list[str]) -> None:
    """Write POLICY_INVENTORY.md - readable catalog of every CA policy intent."""

    def esc(cell: object) -> str:
        s = "" if cell is None else str(cell)
        return s.replace("|", "\\|").replace("\n", " ").strip()

    rows: list[tuple[str, str, str, str]] = []
    for fname in policy_filenames:
        pth = os.path.join(OUT_POLICIES, fname)
        with open(pth, encoding="utf-8") as f:
            data = json.load(f)
        meta = data.get("metadata") or {}
        rows.append(
            (
                str(data.get("id", "")),
                _catalog_policy_title(str(data.get("id", "")), str(data.get("displayName", ""))),
                str(meta.get("persona", "")),
                str(meta.get("criticality", "")),
            )
        )

    lines = [
        "# Conditional Access policy inventory",
        "",
        "Auto-generated by `python scripts/generate-baseline.py`. Regenerate after editing policies in that script.",
        "",
        "| ID | Display name | Persona | Criticality |",
        "| --- | --- | --- | --- |",
    ]
    for rid, dn, pers, crit in rows:
        lines.append(f"| {esc(rid)} | {esc(dn)} | {esc(pers)} | {esc(crit)} |")
    lines.append("")
    out_path = os.path.join(REPO_ROOT, "POLICY_INVENTORY.md")
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))






def _catalog_policy_title(policy_id: str, raw_display_name: str) -> str:
    """Catalog column: human title only when id is in its own column."""
    s = str(raw_display_name).replace("\n", " ").strip()
    prefix = f"[{policy_id}]"
    if s.startswith(prefix):
        s = s[len(prefix) :].lstrip()
    em = f"{policy_id}{_PORTAL_POLICY_TITLE_SEP}"
    hy = f"{policy_id} - "
    if s.startswith(em):
        return s[len(em) :].lstrip()
    if s.startswith(hy):
        return s[len(hy) :].lstrip()
    return s


def _load_policy_inventory_rows(policy_filenames: list[str]) -> list[tuple[str, str, str, str, str]]:
    """Returns list of (id, displayName, persona, criticality, description)."""
    rows: list[tuple[str, str, str, str, str]] = []
    for fname in policy_filenames:
        pth = os.path.join(OUT_POLICIES, fname)
        with open(pth, encoding="utf-8") as f:
            data = json.load(f)
        meta = data.get("metadata") or {}
        desc = str(data.get("description") or "").strip()
        rows.append(
            (
                str(data.get("id", "")),
                _catalog_policy_title(str(data.get("id", "")), str(data.get("displayName", ""))),
                str(meta.get("persona", "")),
                str(meta.get("criticality", "")),
                desc,
            )
        )
    return rows


def write_policy_inventory_html(policy_filenames: list[str]) -> None:
    """Write docs/inventory.html - styled catalog grouped by persona."""

    rows = _load_policy_inventory_rows(policy_filenames)
    by_persona: dict[str, list[tuple[str, str, str, str, str]]] = {}
    for row in rows:
        persona = row[2] or "Other"
        by_persona.setdefault(persona, []).append(row)

    def crit_class(crit: str) -> str:
        c = crit.lower()
        if c == "critical":
            return "pill pill--critical"
        if c == "recommended":
            return "pill pill--recommended"
        if c == "optional":
            return "pill pill--optional"
        return "pill pill--neutral"

    sections_html: list[str] = []
    seen: set[str] = set()
    for persona in PERSONA_SECTION_ORDER:
        if persona not in by_persona:
            continue
        seen.add(persona)
        blocks: list[str] = []
        for rid, dn, _pers, crit, desc in sorted(by_persona[persona], key=lambda r: r[0]):
            desc_html = (
                f'<p class="policy-desc">{html.escape(desc)}</p>' if desc else ""
            )
            blocks.append(
                f"""<article class="policy-card" id="{html.escape(rid)}">
  <div class="policy-card__head">
    <span class="policy-id">{html.escape(rid)}</span>
    <span class="{crit_class(crit)}">{html.escape(crit)}</span>
  </div>
  <h3 class="policy-title">{html.escape(dn)}</h3>
  {desc_html}
</article>"""
            )
        sections_html.append(
            f'<section class="persona-block"><h2 class="persona-heading">{html.escape(persona)}</h2>'
            f'<div class="policy-grid">\n{"\n".join(blocks)}\n</div></section>'
        )

    for persona in sorted(by_persona.keys()):
        if persona in seen:
            continue
        blocks = []
        for rid, dn, _pers, crit, desc in sorted(by_persona[persona], key=lambda r: r[0]):
            desc_html = (
                f'<p class="policy-desc">{html.escape(desc)}</p>' if desc else ""
            )
            blocks.append(
                f"""<article class="policy-card" id="{html.escape(rid)}">
  <div class="policy-card__head">
    <span class="policy-id">{html.escape(rid)}</span>
    <span class="{crit_class(crit)}">{html.escape(crit)}</span>
  </div>
  <h3 class="policy-title">{html.escape(dn)}</h3>
  {desc_html}
</article>"""
            )
        sections_html.append(
            f'<section class="persona-block"><h2 class="persona-heading">{html.escape(persona)}</h2>'
            f'<div class="policy-grid">\n{"\n".join(blocks)}\n</div></section>'
        )

    body_inner = "\n".join(sections_html)
    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <!-- Static catalog only: no scripts. CSP only via meta on GitHub Pages (no custom headers). -->
  <meta
    http-equiv="Content-Security-Policy"
    content="default-src 'self'; base-uri 'self'; script-src 'none'; style-src 'self'; img-src 'self' data:; font-src 'self';"
  />
  <meta name="color-scheme" content="dark light" />
  <meta name="description" content="Mirage CA Baseline v2026 - full Conditional Access policy catalog with personas and criticality." />
  <title>Mirage CA policy catalog</title>
  <link rel="stylesheet" href="style.css" />
  <link rel="stylesheet" href="inventory.css" />
  <link rel="icon" href="data:image/svg+xml;utf8,&lt;svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'&gt;&lt;text y='14' font-size='14'&gt;CA&lt;/text&gt;&lt;/svg&gt;" />
</head>
<body>
  <a class="skip-link" href="#main-content">Skip to main content</a>
  <header class="masthead masthead--catalog">
    <div class="brand">
      <span class="logo" aria-hidden="true">CA</span>
      <div>
        <h1>Mirage CA policy catalog</h1>
        <p class="subtitle">v2026 · {len(rows)} Conditional Access policies · Groups by persona · New deploys: mostly <strong>Report-only</strong>; including device registration MFA (<strong>CA112</strong>) in <strong>Report-only</strong>. <strong>CA111</strong>, <strong>CA202</strong>, <strong>CA204</strong>, <strong>CA302</strong>, <strong>CA303</strong>, <strong>CA603</strong>, <strong>CA606</strong>, <strong>CAA01</strong> default to <strong>Off</strong>; optional intent <code>deploymentState</code> for <strong>first POST only</strong> (never PATCH existing); turn <strong>On</strong> in Entra when ready</p>
        <p class="catalog-nav">
          <a href="index.html">Deploy app</a>
          <span aria-hidden="true">·</span>
          <a href="https://github.com/Teuftis/ConditionalAccessBaseline-Hardened#policy-catalog">README</a>
          <span aria-hidden="true">·</span>
          <a href="https://github.com/Teuftis/ConditionalAccessBaseline-Hardened/blob/main/POLICY_INVENTORY.md">POLICY_INVENTORY.md</a>
        </p>
      </div>
    </div>
  </header>
  <main id="main-content" class="catalog-main">
    <p class="catalog-lede">New policies deploy in <strong>Report-only</strong> (<code>enabledForReportingButNotEnforced</code>) except these default to <strong>Off</strong> (<code>disabled</code>): <strong>CA111</strong>, <strong>CA202</strong>, <strong>CA204</strong>, <strong>CA302</strong>, <strong>CA303</strong>, <strong>CA603</strong>, <strong>CA606</strong>, <strong>CAA01</strong> (<strong>CA112</strong> User actions defaults <strong>Report-only</strong> like the rest). Optional <code>deploymentState</code> / <code>deployState</code> in intent JSON picks Report-only vs Off <strong>only when the policy is first created</strong> (POST); existing tenant policies are never updated in place. This page is generated by <code>python scripts/generate-baseline.py</code>.</p>
    {body_inner}
  </main>
  <footer class="catalog-footer">
    <p>Mirage Conditional Access Baseline · Generated catalog · Same source data as POLICY_INVENTORY.md</p>
  </footer>
</body>
</html>
"""
    os.makedirs(OUT_DOCS, exist_ok=True)
    out_html = os.path.join(OUT_DOCS, "inventory.html")
    with open(out_html, "w", encoding="utf-8", newline="\n") as f:
        f.write(page)



def _readme_catalog_text(value: object) -> str:
    """Single-line Markdown fragment used in README bullets."""
    return str("" if value is None else value).replace("\n", " ").strip()


def _readme_table_cell(value: object) -> str:
    """GFM table cell: flatten and avoid breaking the table on pipe characters."""
    return _readme_catalog_text(value).replace("|", "\\|")


def _readme_criticality_badge(criticality: str) -> str:
    """Shields badge - GitHub Markdown has no native colored table cells."""
    key = (criticality or "").strip().lower()
    if key == "critical":
        msg, color = "Critical", "c62828"
    elif key == "recommended":
        msg, color = "Recommended", "1565c0"
    elif key == "optional":
        msg, color = "Optional", "757575"
    else:
        msg = (criticality or "Unknown").strip() or "Unknown"
        color = "757575"
    qs = urllib.parse.urlencode(
        {"label": "", "message": msg, "color": color, "style": "flat-square"}
    )
    return f"![{msg}](https://img.shields.io/static/v1?{qs})"


def write_readme_policy_catalog(policy_filenames: list[str]) -> None:
    """Replace the Markdown between markers in README.md with a summary table."""
    rows = _load_policy_inventory_rows(policy_filenames)
    lines: list[str] = [
        "| ID | Policy | Persona | Criticality |",
        "| --- | --- | --- | --- |",
    ]
    for rid, dn, pers, crit, _desc in rows:
        badge = _readme_criticality_badge(crit)
        lines.append(
            f"| {_readme_table_cell(rid)} | {_readme_table_cell(dn)} | "
            f"{_readme_table_cell(pers)} | {badge} |"
        )
    block = "\n".join(lines) + "\n"
    readme_path = os.path.join(REPO_ROOT, "README.md")
    readme = Path(readme_path).read_text(encoding="utf-8")
    if README_POLICY_CATALOG_START not in readme or README_POLICY_CATALOG_END not in readme:
        return
    before, rest = readme.split(README_POLICY_CATALOG_START, 1)
    _mid, after = rest.split(README_POLICY_CATALOG_END, 1)
    new_readme = (
        before
        + README_POLICY_CATALOG_START
        + "\n"
        + block
        + README_POLICY_CATALOG_END
        + after
    )
    Path(readme_path).write_text(new_readme, encoding="utf-8", newline="\n")


def write_readme_group_catalog() -> None:
    """Replace Entra groups bullet list between markers in README.md."""
    tier_display = {
        "required": "Required",
        "service-tracks": "Service track",
        "exception": "Exception",
        "pilot": "Pilot",
    }
    lines: list[str] = []
    for g in GROUPS:
        dn = _readme_catalog_text(g.get("displayName", ""))
        tier = tier_display.get(str(g.get("tier", "")), _readme_catalog_text(g.get("tier", "")))
        nick = _readme_catalog_text(g.get("mailNickname", ""))
        desc = _readme_catalog_text(g.get("description", ""))
        lines.append(f"- **{dn}** \u2014 {tier} \u2014 mailNickname `{nick}`")
        if desc:
            lines.append(f"  {desc}")
    block = "\n".join(lines) + "\n"
    readme_path = os.path.join(REPO_ROOT, "README.md")
    body = Path(readme_path).read_text(encoding="utf-8")
    if README_GROUP_CATALOG_START not in body or README_GROUP_CATALOG_END not in body:
        return
    before, rest = body.split(README_GROUP_CATALOG_START, 1)
    _mid, after = rest.split(README_GROUP_CATALOG_END, 1)
    new_body = (
        before
        + README_GROUP_CATALOG_START
        + "\n"
        + block
        + README_GROUP_CATALOG_END
        + after
    )
    Path(readme_path).write_text(new_body, encoding="utf-8", newline="\n")


def _crit_pill_class(crit: str) -> str:
    c = crit.lower()
    if c == "critical":
        return "policy-pill policy-pill--critical"
    if c == "recommended":
        return "policy-pill policy-pill--recommended"
    if c == "optional":
        return "policy-pill policy-pill--optional"
    return "policy-pill"


def write_index_html_policy_catalog_table(policy_filenames: list[str]) -> None:
    """Replace the <tbody> rows between markers in docs/index.html.

    Mirrors README policy IDs and names so users can scan every Conditional
    Access policy without leaving the SPA. Marker delimiters match the ones
    used in README.md; each file is rewritten in place by splitting on its
    own marker pair.
    """
    rows = _load_policy_inventory_rows(policy_filenames)
    row_indent = " " * 14
    cell_indent = " " * 16
    rendered: list[str] = []
    for rid, dn, pers, crit, _desc in rows:
        rendered.append(
            f"{row_indent}<tr>\n"
            f"{cell_indent}<th scope=\"row\"><code>{html.escape(rid)}</code></th>\n"
            f"{cell_indent}<td>{html.escape(dn)}</td>\n"
            f"{cell_indent}<td>{html.escape(pers)}</td>\n"
            f"{cell_indent}<td><span class=\"{_crit_pill_class(crit)}\">{html.escape(crit)}</span></td>\n"
            f"{row_indent}</tr>"
        )
    block = "\n".join(rendered) + "\n"

    index_path = os.path.join(OUT_DOCS, "index.html")
    if not os.path.isfile(index_path):
        return
    text = Path(index_path).read_text(encoding="utf-8")
    if README_POLICY_CATALOG_START not in text or README_POLICY_CATALOG_END not in text:
        return
    before, rest = text.split(README_POLICY_CATALOG_START, 1)
    _mid, after = rest.split(README_POLICY_CATALOG_END, 1)
    new_text = (
        before
        + README_POLICY_CATALOG_START
        + "\n"
        + block
        + " " * 14
        + README_POLICY_CATALOG_END
        + after
    )
    Path(index_path).write_text(new_text, encoding="utf-8", newline="\n")

def sync_baseline_to_docs_site() -> None:
    """Copy baseline/ to docs/baseline so GitHub Pages can serve manifest.json same-origin."""
    if os.path.isdir(DOCS_BASELINE):
        shutil.rmtree(DOCS_BASELINE)
    shutil.copytree(OUT_BASELINE, DOCS_BASELINE)


def main() -> int:
    groups = write_groups()
    named_locations = write_named_locations()
    policies = write_policies()
    write_manifest(groups, named_locations, policies)
    write_policy_inventory(policies)
    write_policy_inventory_html(policies)
    write_readme_policy_catalog(policies)
    write_readme_group_catalog()
    write_index_html_policy_catalog_table(policies)
    sync_baseline_to_docs_site()
    print(
        f"Wrote {len(groups)} groups, {len(named_locations)} named locations, {len(policies)} policies, "
        "POLICY_INVENTORY.md, docs/inventory.html, README policy & group lists, docs/index.html policy table, docs/baseline mirror."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
