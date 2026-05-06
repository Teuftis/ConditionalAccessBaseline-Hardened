# Mirage Conditional Access Baseline (v2026)

**At a glance**

- **40** Conditional Access policies, **11** groups, **4** named locations — stored as **intent JSON** under [`baseline/`](./baseline/), not as a raw tenant export.
- **Deploy through the hosted app** (the `docs/` bundle on GitHub Pages): **delegated** Microsoft Graph only — **no** OAuth client secret in this repository.
- **New CA policies deploy in Report-only** (`enabledForReportingButNotEnforced`) by default, except **eight** baseline rules land **Off** (`disabled`): **CA111**, **CA202**, **CA204**, **CA302**, **CA303**, **CA603**, **CA606**, **CAA01**. **CA112** (device registration MFA / **User actions**) uses the same deploy default — **Report-only**. Override per policy with intent **`deploymentState`** / **`deployState`** (see **`POLICY_IDS_DEPLOY_DISABLED_BY_DEFAULT`** in [`docs/translate.js`](docs/translate.js)). Existing policies that match the baseline **display name** are **never** silently updated via PATCH.
- **Not a Microsoft product.** Validate licensing (for example Entra ID P2 for risk-based policies), app coverage, and your change process. See [Legal & reference](#legal--reference).

This project is an opinionated Conditional Access posture for Microsoft Entra ID. Open the **[deploy app](https://teuftis.github.io/ConditionalAccessBaseline-Hardened/)** (static site from [`docs/`](./docs/)), sign in as a tenant admin, and run a dry run or full deploy: the app resolves names to Graph IDs using [`docs/translate.js`](docs/translate.js), applies [`baseline/manifest.json`](./baseline/manifest.json), and creates missing **groups**, **named locations**, and **policies**. Terms of Use and some third-party prerequisites remain **tenant-owned** — they can show as **skipped** until you create or license them.

> **Operational risk:** Graph APIs and CA policy schemas change over time. Prefer a **non-production** tenant for first runs, keep **break-glass** reachable, and move policies to report-only and then on in **phases** in the Microsoft Entra admin center.

[![Open deploy app](https://img.shields.io/badge/Open-deploy%20app-0078D4?logo=microsoftazure&logoColor=white&style=for-the-badge)](https://teuftis.github.io/ConditionalAccessBaseline-Hardened/)

**Quick links:** [Deploy app](https://teuftis.github.io/ConditionalAccessBaseline-Hardened/) · [GitHub repo](https://github.com/Teuftis/ConditionalAccessBaseline-Hardened) · [Policy catalog (Pages)](https://teuftis.github.io/ConditionalAccessBaseline-Hardened/inventory.html) · [`POLICY_INVENTORY.md`](./POLICY_INVENTORY.md) · [`SECURITY.md`](./SECURITY.md)

---

## Navigating this repo

| Outcome | Start here |
|--------|--------------|
| **Deploy** baseline objects into a tenant (**most new policies in Report-only**; **CA111, CA202, CA204, CA302, CA303, CA603, CA606, CAA01** default **Off**) | [Deploy in your tenant](#deploy-in-your-tenant) → [After deploy](#after-deploy-in-microsoft-entra-admin-center) |
| **Review** assurance, criticality, and write behavior | [Safety and trust](#safety-and-trust) · [inventory.html](https://teuftis.github.io/ConditionalAccessBaseline-Hardened/inventory.html) · [`POLICY_INVENTORY.md`](./POLICY_INVENTORY.md) · per-policy [`baseline/policies/`](./baseline/policies/) |
| **Change** definitions or publish your fork | [`scripts/generate-baseline.py`](scripts/generate-baseline.py) and [Customize & fork](#customize--fork); hosting in [GitHub Pages](#github-pages) |
| **Summarize** for stakeholders | **At a glance** above + artifact counts below |

---

## What's in this repository

**Intent JSON** describes policies ([`baseline/policies/`](./baseline/policies/)), groups ([`baseline/groups/`](./baseline/groups/)), and named locations ([`baseline/namedLocations/`](./baseline/namedLocations/)). Deploy time resolution uses [`docs/translate.js`](docs/translate.js); [`ALLOWED_DEPLOY_STATES`](docs/config.js) constrains new policies so the SPA creates **Report-only** or **Off** only (`enabledForReportingButNotEnforced` vs `disabled`). **Off by default** only for `POLICY_IDS_DEPLOY_DISABLED_BY_DEFAULT` (see `resolvePolicyDeployState`). Flip to **On** only from the admin center when your runbook says so.

| Artifact | Count | Path |
|---------|-------|------|
| Conditional Access policies | 40 | [`baseline/policies/`](./baseline/policies/) |
| Groups | 11 | [`baseline/groups/`](./baseline/groups/) |
| Named locations | 4 | [`baseline/namedLocations/`](./baseline/namedLocations/) |

You **do not** need a local clone just to deploy: use the **[deploy app](https://teuftis.github.io/ConditionalAccessBaseline-Hardened/)** once [GitHub Pages](#github-pages) is publishing the default branch.

Policies that scope optional workloads may appear as **skipped** when a third-party **service principal** does not exist. **Terms of Use** objects remain **tenant-owned** — deploy does not create them.

[`docs/deploy.js`](docs/deploy.js) runs the manifest flow. Regenerating artifacts from the spreadsheet-driven generator is documented under [Customize & fork](#customize--fork).

## Safety and trust

| Topic | What to know |
|-------|----------------|
| **Credentialed only** | The app uses **your** admin session with **delegated** Graph scopes. There is **no** OAuth client secret in GitHub ([`docs/config.js`](docs/config.js)). |
| **Writes are guarded** | New CA policies default to **Report-only** except **`POLICY_IDS_DEPLOY_DISABLED_BY_DEFAULT`** (**CA111, CA202, CA204, CA302, CA303, CA603, CA606, CAA01**), which are created **Off**. [`ALLOWED_DEPLOY_STATES`](docs/config.js) forbids creating policies **On** from the SPA. If a tenant policy shares the normalized **display name**, deploy **skips** it — zero silent PATCH. |
| **Supply chain** | Browsers execute whatever `main` publishes to **Pages** via `docs/` and CI — protect the default branch and review changes under `docs/` and [.github/workflows/deploy-pages.yml](.github/workflows/deploy-pages.yml). |

## Deploy in your tenant

Delegated roles that can complete the flow commonly combine **Conditional Access Administrator**, **Groups Administrator**, **Security Administrator**, or **Global Administrator**.

1. Open the **[deploy app](https://teuftis.github.io/ConditionalAccessBaseline-Hardened/)** (errors or blank app → [GitHub Pages](#github-pages) troubleshooting).
2. **Sign in** and accept **delegated** Microsoft Graph scopes.
3. Optionally keep **Dry run** enabled (preview only — no tenant writes); clear it when you intend to create objects.
4. Read the activity log: **skipped** (missing prerequisites), **unchanged** (existing **display name** already matches), **created**, or **error** (often schema or prerequisites).

### Writes vs re-run behavior

| Artifact | Behavior |
|---------|----------|
| Conditional Access policies | **POST** only when **no** existing policy shares that normalized **display name**. Existing tenant policies **never PATCH** automatically. |
| Groups | Ensured to exist so IDs resolve; memberships and props are **not** maintained by deploy. |
| Named locations | Created if missing; if present, IP/country payload is **not** overwritten automatically. |

The log summarizes outcomes (including skips such as **`firstPartyApp:`…** where Microsoft-hosted apps lack a tenant service principal).

### After deploy in Microsoft Entra admin center

1. Populate **named location** ranges/countries and **group** memberships (break-glass, exclusions, pilots, automation groups).
2. Review **Protection → Conditional Access**, **Sign-in logs**, and Conditional Access insights before changing policy effects.
3. Turn policies **On** (fully enforced) in phases when sign-in logs and your runbook justify it — most land in **Report-only** from deploy unless they defaulted **Off**.

## Customize & fork

| Task | Steps |
|------|-------|
| **Change policies or groups** | Edit **`POLICIES`** / **`GROUPS`** (and related structures) in [`scripts/generate-baseline.py`](scripts/generate-baseline.py). Run **`python scripts/generate-baseline.py`**. Commit **`baseline/`**, **`docs/baseline/`**, **`POLICY_INVENTORY.md`**, **`docs/inventory.html`**, **`docs/index.html`**, and README appendix markers this script replaces. Save the generator as **UTF-8** on Windows. [`POLICY_INVENTORY.md`](./POLICY_INVENTORY.md) stays in sync as a Markdown mirror of policy rows. |
| **Naming in Entra** | **`displayName`** values such as **`CA101 — Require MFA`** use an **em dash** (**`—`**). Deploy normalizes hyphen variants (`CA101 —` ↔ `CA101 -`) — dupes skip creation until you rename or remove stale tenant policies. |
| **Fork another app registration** | Multitenant **public client SPA** (still no secrets). Paste **`clientId`** + HTTPS redirect URIs into [`docs/config.js`](docs/config.js) with [`GRAPH_SCOPES`](docs/config.js), then publish **Pages** on your fork. |
| **Hack locally** | Repo root → `python -m http.server` (or VS Code Live Server); open **`/docs/`**. Register **localhost** redirect URIs beside your production Pages URIs on the SPA app registration. |

## GitHub Pages

The browser bundle is **`docs/`**, rebuilt by [.github/workflows/deploy-pages.yml](.github/workflows/deploy-pages.yml) on **`main`**.

Configure **Pages** once (**[Settings → Pages → GitHub Actions](https://docs.github.com/pages/getting-started-with-github-pages/about-github-pages)**; historically **Publish from branch `/docs`** also works).

**Same-origin baseline JSON:** workflows run **`rm -rf docs/baseline && cp -r baseline docs/baseline`** so `fetch("./baseline/manifest.json")` stays **same-origin** with the SPA. `generate-baseline.py` refreshes that mirror locally too.

**404 or empty manifest?** Confirm the **Deploy GitHub Pages** workflow completed; hard refresh. Older forks lacking the copy step can set `window.MIRAGE_BASELINE_URL` or use **raw.githubusercontent.com** URLs (subject to **CORS**).

## Appendix

Auto-generated excerpts follow. The **policy table** below stays in sync with [`POLICY_INVENTORY.md`](./POLICY_INVENTORY.md); for filters and layout use **[inventory.html](https://teuftis.github.io/ConditionalAccessBaseline-Hardened/inventory.html)**.

### Policy catalog

Summaries regenerate from [`baseline/policies/`](./baseline/policies/) when you run **`python scripts/generate-baseline.py`**.

<!-- policy-catalog:start -->
| ID | Policy | Persona | Criticality |
| --- | --- | --- | --- |
| CA101 | Require MFA | All users | ![Critical](https://img.shields.io/static/v1?label=&message=Critical&color=c62828&style=flat-square) |
| CA102 | User Risk - Require MFA + Password Change | All users | ![Critical](https://img.shields.io/static/v1?label=&message=Critical&color=c62828&style=flat-square) |
| CA103 | Sign-In Risk - Require MFA | All users | ![Critical](https://img.shields.io/static/v1?label=&message=Critical&color=c62828&style=flat-square) |
| CA104 | Block Legacy Authentication | All users | ![Critical](https://img.shields.io/static/v1?label=&message=Critical&color=c62828&style=flat-square) |
| CA105 | Block Unknown Platforms | All users | ![Recommended](https://img.shields.io/static/v1?label=&message=Recommended&color=1565c0&style=flat-square) |
| CA106 | Block Outside Trusted Countries | All users | ![Critical](https://img.shields.io/static/v1?label=&message=Critical&color=c62828&style=flat-square) |
| CA107 | Session Controls | All users | ![Recommended](https://img.shields.io/static/v1?label=&message=Recommended&color=1565c0&style=flat-square) |
| CA108 | Block Cross-Device Auth Flows | All users | ![Critical](https://img.shields.io/static/v1?label=&message=Critical&color=c62828&style=flat-square) |
| CA109 | Require MFA for Azure Management | All users | ![Recommended](https://img.shields.io/static/v1?label=&message=Recommended&color=1565c0&style=flat-square) |
| CA110 | Block Malicious IPs | All users | ![Optional](https://img.shields.io/static/v1?label=&message=Optional&color=757575&style=flat-square) |
| CA111 | Continuous Access Evaluation - Standard | All users | ![Recommended](https://img.shields.io/static/v1?label=&message=Recommended&color=1565c0&style=flat-square) |
| CA112 | MFA on Device Register or Join | All users | ![Critical](https://img.shields.io/static/v1?label=&message=Critical&color=c62828&style=flat-square) |
| CA113 | Require Token Protection (Pilot) | All users | ![Optional](https://img.shields.io/static/v1?label=&message=Optional&color=757575&style=flat-square) |
| CA114 | Terms of Use | All users | ![Optional](https://img.shields.io/static/v1?label=&message=Optional&color=757575&style=flat-square) |
| CA201 | Intune Enrolling - Require MFA | All users | ![Critical](https://img.shields.io/static/v1?label=&message=Critical&color=c62828&style=flat-square) |
| CA202 | Require App Protection (Mobile) | All users | ![Critical](https://img.shields.io/static/v1?label=&message=Critical&color=c62828&style=flat-square) |
| CA204 | Require Compliant Mobile (Optional MDM track) | All users | ![Optional](https://img.shields.io/static/v1?label=&message=Optional&color=757575&style=flat-square) |
| CA301 | Require Compliant Windows | All users | ![Critical](https://img.shields.io/static/v1?label=&message=Critical&color=c62828&style=flat-square) |
| CA302 | Require Compliant macOS | All users | ![Critical](https://img.shields.io/static/v1?label=&message=Critical&color=c62828&style=flat-square) |
| CA303 | Limited Browser Access on Unmanaged Devices | All users | ![Recommended](https://img.shields.io/static/v1?label=&message=Recommended&color=1565c0&style=flat-square) |
| CA601 | Phishing-Resistant MFA for Admins | Admins | ![Critical](https://img.shields.io/static/v1?label=&message=Critical&color=c62828&style=flat-square) |
| CA602 | Admin Session Controls | Admins | ![Critical](https://img.shields.io/static/v1?label=&message=Critical&color=c62828&style=flat-square) |
| CA603 | Admin CAE - Strict | Admins | ![Critical](https://img.shields.io/static/v1?label=&message=Critical&color=c62828&style=flat-square) |
| CA604 | Admin Block High User Risk | Admins | ![Critical](https://img.shields.io/static/v1?label=&message=Critical&color=c62828&style=flat-square) |
| CA605 | Admin Block High Sign-In Risk | Admins | ![Critical](https://img.shields.io/static/v1?label=&message=Critical&color=c62828&style=flat-square) |
| CA606 | Admin Require Compliant or Joined Device | Admins | ![Critical](https://img.shields.io/static/v1?label=&message=Critical&color=c62828&style=flat-square) |
| CA701 | App - FortiClient - MFA | Application | ![Optional](https://img.shields.io/static/v1?label=&message=Optional&color=757575&style=flat-square) |
| CA702 | App - Salesforce - MFA | Application | ![Optional](https://img.shields.io/static/v1?label=&message=Optional&color=757575&style=flat-square) |
| CA801 | Service - Require MFA (Interactive) | Service | ![Recommended](https://img.shields.io/static/v1?label=&message=Recommended&color=1565c0&style=flat-square) |
| CA802 | Service - Block Outside Trusted IPs | Service | ![Critical](https://img.shields.io/static/v1?label=&message=Critical&color=c62828&style=flat-square) |
| CA803 | Service - Block Legacy Auth | Service | ![Recommended](https://img.shields.io/static/v1?label=&message=Recommended&color=1565c0&style=flat-square) |
| CA804 | Service - Block Non-M365 Apps | Service | ![Recommended](https://img.shields.io/static/v1?label=&message=Recommended&color=1565c0&style=flat-square) |
| CA901 | Guest - Require MFA | Guest | ![Critical](https://img.shields.io/static/v1?label=&message=Critical&color=c62828&style=flat-square) |
| CA902 | Guest - Block High Sign-In Risk | Guest | ![Recommended](https://img.shields.io/static/v1?label=&message=Recommended&color=1565c0&style=flat-square) |
| CA903 | Guest - Block Legacy Auth | Guest | ![Recommended](https://img.shields.io/static/v1?label=&message=Recommended&color=1565c0&style=flat-square) |
| CA904 | Guest - Block Outside Trusted Countries | Guest | ![Critical](https://img.shields.io/static/v1?label=&message=Critical&color=c62828&style=flat-square) |
| CA905 | Guest - Block Non-Collaboration Apps | Guest | ![Critical](https://img.shields.io/static/v1?label=&message=Critical&color=c62828&style=flat-square) |
| CA906 | Guest - Terms of Use | Guest | ![Optional](https://img.shields.io/static/v1?label=&message=Optional&color=757575&style=flat-square) |
| CA907 | Guest - Session Controls | Guest | ![Recommended](https://img.shields.io/static/v1?label=&message=Recommended&color=1565c0&style=flat-square) |
| CAA01 | Agent - Block High Risk | Agent | ![Recommended](https://img.shields.io/static/v1?label=&message=Recommended&color=1565c0&style=flat-square) |
<!-- policy-catalog:end -->

### Groups (Entra)

Each entry mirrors a JSON file under [`baseline/groups/`](./baseline/groups/). Policy intent references groups by **display name**; deploy binds them to object IDs. **`tier`** means **Required** (foundation), **Service track** (automation splits for CA801 / CA802), **Exception** (short-lived allowances), **Pilot** (narrow experiments). **`mailNickname`** values satisfy Graph uniqueness at creation time.

<!-- group-catalog:start -->
- **BG_BreakGlass** — Required — mailNickname `bg-breakglass`
  Break-glass and other emergency administrator accounts that must remain reachable if Conditional Access misconfiguration locks out normal admins. Keep membership empty until accounts exist; remove members when not actively needed. Excluded from nearly all CA policies so use only for documented recovery procedures.
- **CA_ExcludedFromCA** — Required — mailNickname `ca-excludedfromca`
  Catch-all exclusion for identities that must never be evaluated by user-facing CA (for example certain directory sync or legacy integration principals your vendor documents as CA-exempt). Treat membership as highly privileged—every account here bypasses most workforce controls.
- **CA_ServiceAccount** — Required — mailNickname `ca-serviceaccount`
  Parent group for non-human and automation accounts. Policies that target all users exclude this group so background jobs are not forced through interactive MFA. Nest members into the interactive vs non-interactive child groups so CA801 can target only human-driven service logons.
- **CA_ServiceAccount_Interactive** — Service track — mailNickname `ca-serviceaccount-interactive`
  Service principals or managed identities that sometimes sign in through a browser or device-code style flow. CA801 requires MFA for this population while leaving pure client-credential automation in the non-interactive sibling group.
- **CA_ServiceAccount_NonInteractive** — Service track — mailNickname `ca-serviceaccount-noninteractive`
  Automation identities that only use client credentials, managed identity, or other non-interactive OAuth flows. Excluded from CA801 so scheduled jobs are not blocked; pair with CA802-CA804 for network and app restrictions.
- **CA_TravelException** — Exception — mailNickname `ca-travelexception`
  Short-lived membership for employees who must sign in from outside TRUSTED_COUNTRIES during approved travel. CA106 excludes this group from the country condition so the geofence still applies to everyone else; expire memberships when the trip ends.
- **CA_DeviceCodeApproved** — Exception — mailNickname `ca-devicecodeapproved`
  Rare allowance for CA108's block on device-code and authentication-transfer flows (for example controlled kiosk or DevOps scenarios). Add only fully trusted principals; every member is a phishing surface.
- **CA_TokenProtection_Pilot** — Pilot — mailNickname `ca-tokenprotection-pilot`
  Users or devices included in the CA113 Windows token-protection pilot. Start with a small population, collect sign-in and help-desk telemetry, then expand membership as your estate supports the feature.
- **CA_ExcludedAgents** — Exception — mailNickname `ca-excludedagents`
  Workload agent or service principal objects that must not be blocked by CAA01 when Identity Protection flags them high risk (for example monitored automation with known false positives). Keep the group tiny and review quarterly.
- **CA_MSP_PartnerUsers** — Exception — mailNickname `ca-msp-partnerusers`
  Delegated administrator or partner accounts that need access to Microsoft 365 admin experiences blocked for standard guests in CA905. Requires explicit lifecycle: remove access when the engagement ends.
- **AUTOPILOT_DevicePrep** — Exception — mailNickname `autopilot-deviceprep`
  Device objects undergoing Windows Autopilot pre-provisioning so they can complete join/enrollment without triggering CA112 MFA-on-join or CA201 enrollment MFA prematurely. Clean up stale device members after deployment finishes.
<!-- group-catalog:end -->

## Further reading

- [Conditional Access overview — Microsoft Learn](https://learn.microsoft.com/entra/identity/conditional-access/overview)
- [Policies and assignments](https://learn.microsoft.com/entra/identity/conditional-access/concept-conditional-access-policies)
- [Named locations](https://learn.microsoft.com/entra/identity/conditional-access/concept-assignment-network)
- Microsoft's Zero Trust / CA architecture materials (conceptual grounding): see [microsoft/ConditionalAccessforZeroTrustResources](https://github.com/microsoft/ConditionalAccessforZeroTrustResources) and linked guidance.

## Legal & reference

- **License:** [MIT License](./LICENSE)
- **Security:** [`SECURITY.md`](./SECURITY.md) (prefer GitHub **Security → Report a vulnerability**)
- **`reference/` spreadsheets:** Authoring companions (`.xlsx`) for the baseline; **not** read by the deploy runtime. Keep group display names and `mailNickname`-style strings aligned with **`baseline/groups/`** (prefix **`CA_`**, **`ca-`**) when you edit the workbooks; regenerate from **`scripts/generate-baseline.py`** for the JSON side of the house.

## Microsoft Sentinel / Log Analytics — Conditional Access outcome queries

Below queries assume **`SigninLogs`** and **`AADNonInteractiveUserSignInLogs`** (or equivalents) flow into your workspace. Tune `lookback`; policy display names reflect what Entra emits in each sign-in (`ConditionalAccessPolicies`).

### Report-only, hard failures, and interrupts — 5d lookback

Use this to prioritize **baseline policies in Report-only** (`reportOnlyFailure`, `reportOnlyInterrupted`) versus **production hard fails** (`failure`, `interrupted`), including **legacy auth** and **device posture** context.

```kusto
let lookback = 5d;

union isfuzzy=true

    (SigninLogs | extend SignInType = "Interactive"),

    (AADNonInteractiveUserSignInLogs | extend SignInType = "NonInteractive")

| where TimeGenerated > ago(lookback)

| extend CAPolicies = coalesce(

    todynamic(column_ifexists("ConditionalAccessPolicies_string", "")),

    column_ifexists("ConditionalAccessPolicies_dynamic", dynamic(null)),

    column_ifexists("ConditionalAccessPolicies", dynamic(null)))

| extend StatusObj = coalesce(

    todynamic(column_ifexists("Status_string", "")),

    column_ifexists("Status_dynamic", dynamic(null)),

    column_ifexists("Status", dynamic(null)))

| extend DeviceObj = coalesce(

    todynamic(column_ifexists("DeviceDetail_string", "")),

    column_ifexists("DeviceDetail_dynamic", dynamic(null)),

    column_ifexists("DeviceDetail", dynamic(null)))

| extend LocationObj = coalesce(

    todynamic(column_ifexists("LocationDetails_string", "")),

    column_ifexists("LocationDetails_dynamic", dynamic(null)),

    column_ifexists("LocationDetails", dynamic(null)))

| where isnotempty(CAPolicies) and tostring(CAPolicies) != "[]"

| mv-expand CAPolicies

| extend

    PolicyName    = tostring(CAPolicies.displayName),

    PolicyResult  = tostring(CAPolicies.result),

    GrantControls = tostring(CAPolicies.enforcedGrantControls)

| where PolicyResult in ("failure", "reportOnlyFailure", "interrupted", "reportOnlyInterrupted")

| extend

    ErrorCode     = tostring(StatusObj.errorCode),

    FailureReason = tostring(StatusObj.failureReason),

    IsCompliant   = tobool(DeviceObj.isCompliant),

    IsManaged     = tobool(DeviceObj.isManaged),

    Country       = tostring(LocationObj.countryOrRegion)

| summarize

    HardFailures          = countif(PolicyResult == "failure"),

    ReportOnlyFailures    = countif(PolicyResult == "reportOnlyFailure"),

    Interrupted           = countif(PolicyResult == "interrupted"),

    ReportOnlyInterrupted = countif(PolicyResult == "reportOnlyInterrupted"),

    DistinctIPs           = dcount(IPAddress),

    Apps                  = make_set(AppDisplayName, 10),

    ClientApps            = make_set(ClientAppUsed, 10),

    GrantControlsHit      = make_set(GrantControls, 10),

    ErrorCodes            = make_set(ErrorCode, 10),

    FailureReasons        = make_set(FailureReason, 5),

    Countries             = make_set(Country, 5),

    LegacyAuthSeen        = countif(ClientAppUsed in ("Other clients", "IMAP", "POP", "SMTP", "Exchange ActiveSync", "Authenticated SMTP", "Exchange Web Services")),

    NonCompliantDevice    = countif(IsCompliant == false),

    UnmanagedDevice       = countif(IsManaged == false),

    LastSeen              = max(TimeGenerated)

    by UserPrincipalName, PolicyName, SignInType

| extend Severity = case(

    HardFailures > 0 and LegacyAuthSeen > 0, "High - hard fail + legacy auth",

    HardFailures > 0, "Medium - hard fail",

    ReportOnlyFailures > 0, "Tuning - report-only fail",

    "Low - interrupt only")

| order by HardFailures desc, ReportOnlyFailures desc, Interrupted desc, UserPrincipalName asc
```

### Enforcement (On) policies — hard failures only — 1d lookback

Excludes Report-only outcomes; focus on **`failure`** for policies that **enforce** (**On**).

```kusto
let lookback = 1d;

union isfuzzy=true

    (SigninLogs | extend SignInType = "Interactive"),

    (AADNonInteractiveUserSignInLogs | extend SignInType = "NonInteractive")

| where TimeGenerated > ago(lookback)

| extend CAPolicies = coalesce(

    todynamic(column_ifexists("ConditionalAccessPolicies_string", "")),

    column_ifexists("ConditionalAccessPolicies_dynamic", dynamic(null)),

    column_ifexists("ConditionalAccessPolicies", dynamic(null)))

| extend StatusObj = coalesce(

    todynamic(column_ifexists("Status_string", "")),

    column_ifexists("Status_dynamic", dynamic(null)),

    column_ifexists("Status", dynamic(null)))

| extend DeviceObj = coalesce(

    todynamic(column_ifexists("DeviceDetail_string", "")),

    column_ifexists("DeviceDetail_dynamic", dynamic(null)),

    column_ifexists("DeviceDetail", dynamic(null)))

| extend LocationObj = coalesce(

    todynamic(column_ifexists("LocationDetails_string", "")),

    column_ifexists("LocationDetails_dynamic", dynamic(null)),

    column_ifexists("LocationDetails", dynamic(null)))

| where isnotempty(CAPolicies) and tostring(CAPolicies) != "[]"

| mv-expand CAPolicies

| extend

    PolicyName    = tostring(CAPolicies.displayName),

    PolicyResult  = tostring(CAPolicies.result),

    GrantControls = tostring(CAPolicies.enforcedGrantControls)

| where PolicyResult == "failure"

| extend

    ErrorCode     = tostring(StatusObj.errorCode),

    FailureReason = tostring(StatusObj.failureReason),

    IsCompliant   = tobool(DeviceObj.isCompliant),

    IsManaged     = tobool(DeviceObj.isManaged),

    DeviceOS      = tostring(DeviceObj.operatingSystem),

    Country       = tostring(LocationObj.countryOrRegion),

    City          = tostring(LocationObj.city)

| summarize

    Failures         = count(),

    DistinctIPs      = dcount(IPAddress),

    DistinctApps     = dcount(AppDisplayName),

    Apps             = make_set(AppDisplayName, 10),

    ClientApps       = make_set(ClientAppUsed, 10),

    GrantControlsHit = make_set(GrantControls, 10),

    ErrorCodes       = make_set(ErrorCode, 10),

    FailureReasons   = make_set(FailureReason, 5),

    Countries        = make_set(Country, 5),

    Cities           = make_set(City, 5),

    DeviceOSes       = make_set(DeviceOS, 5),

    LegacyAuthHits   = countif(ClientAppUsed in ("Other clients", "IMAP", "POP", "SMTP", "Exchange ActiveSync", "Authenticated SMTP", "Exchange Web Services")),

    NonCompliantHits = countif(IsCompliant == false),

    UnmanagedHits    = countif(IsManaged == false),

    FirstSeen        = min(TimeGenerated),

    LastSeen         = max(TimeGenerated)

    by PolicyName, UserPrincipalName, SignInType

| extend Triage = case(

    LegacyAuthHits > 0, "Legacy auth — check for stale app config or attack",

    NonCompliantHits == Failures, "Device compliance — Intune posture issue",

    UnmanagedHits == Failures, "Unmanaged device — enrollment gap",

    GrantControlsHit has "block", "Block policy fired — verify intent",

    GrantControlsHit has "mfa", "MFA failure — user couldn't complete challenge",

    "Investigate")

| order by Failures desc, LastSeen desc
```


