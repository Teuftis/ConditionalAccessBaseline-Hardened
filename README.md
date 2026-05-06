# Mirage Conditional Access Baseline (v2026)

Opinionated, production-oriented **Conditional Access** for Microsoft Entra ID: baseline objects live as **intent JSON** (not tenant-specific Graph payloads). A **static web app under `docs/`** turns names into GUIDs via Microsoft Graph — no backend and no client secret in the repo. Sign in as a tenant admin with delegated consent, then create missing **groups**, **named locations**, and **Conditional Access policies** (new CA policies default to **disabled**).

**Not a Microsoft product.** Use as a baseline only: validate against your apps, licenses (for example Entra ID P2 for risk-based controls), and your change process.

| | |
|---|---|
| **Live deploy app** | [ConditionalAccessBaseline-Hardened on Pages](https://teuftis.github.io/ConditionalAccessBaseline-Hardened/) |
| **Source** | [Teuftis/ConditionalAccessBaseline-Hardened](https://github.com/Teufis/ConditionalAccessBaseline-Hardened) |
| **Styled policy catalog** | [inventory.html](https://teuftis.github.io/ConditionalAccessBaseline-Hardened/inventory.html) (filters and layout for browsing)

[![Open deploy app](https://img.shields.io/badge/Open-deploy%20app-0078D4?logo=microsoftazure&logoColor=white&style=for-the-badge)](https://teuftis.github.io/ConditionalAccessBaseline-Hardened/)

## Choose your path

| You want to… | Start here |
|--------------|------------|
| Deploy into a tenant today | See [Deploy in your tenant](#deploy-in-your-tenant) · [Safety and trust](#safety-and-trust) · [Further reading](#further-reading) |
| Maintain the baseline, regenerate JSON, fork the app registration | See [Customize & fork](#customize--fork) · [GitHub Pages](#github-pages) · [Safety and trust](#safety-and-trust) |

## Contents

| Section | What you'll find |
|---------|------------------|
| [What's in this repository](#whats-in-this-repository) | Folders, intent model, skips, catalogs |
| [Deploy in your tenant](#deploy-in-your-tenant) | Roles, dry run, writes vs untouched policies |
| [After deploy](#after-deploy-in-microsoft-entra-admin-center) | Portal checklist before enabling policies |
| [Safety and trust](#safety-and-trust) | Delegated-only writes, naming match, branch supply chain |
| [Customize & fork](#customize--fork) | Generator, naming, forks, local dev |
| [GitHub Pages](#github-pages) | Publishing SPA + troubleshooting **404**, `docs/baseline` mirror |
| [Policy catalog](#policy-catalog) | Long auto-generated appendix (browse [inventory.html](https://teuftis.github.io/ConditionalAccessBaseline-Hardened/inventory.html) first) |
| [Groups](#groups-entra) | Auto-generated Entra groups appendix |
| [Further reading](#further-reading) | Microsoft Learn CA links |
| [Legal & reference](#legal--reference) | License · security · spreadsheets |

---

## What's in this repository

**Intent JSON** describes policies ([`baseline/policies/`](./baseline/policies/)), groups ([`baseline/groups/`](./baseline/groups/)), and named locations ([`baseline/namedLocations/`](./baseline/namedLocations/)). At deploy time, [`docs/translate.js`](docs/translate.js) resolves display names into Graph IDs (`ALLOWED_DEPLOY_STATES` in [`docs/config.js`](docs/config.js) forces policies to **`disabled`** for new creations).

| Artifact | Count | Path |
|---------|-------|------|
| Conditional Access policies | 40 | [`baseline/policies/`](./baseline/policies/) |
| Groups | 11 | [`baseline/groups/`](./baseline/groups/) |
| Named locations | 4 | [`baseline/namedLocations/`](./baseline/namedLocations/) |

You do **not** need this repo cloned to deploy: open the **[live app](https://teuftis.github.io/ConditionalAccessBaseline-Hardened/)** once [GitHub Pages](#github-pages) is serving it. Policies that scope optional workloads may **skip** if a required third-party **service principal** is missing. Terms of Use stay **tenant-owned** objects — nothing creates them automatically.

For reviews and Git diffs, [`POLICY_INVENTORY.md`](./POLICY_INVENTORY.md) duplicates the appendix as a table. **`python scripts/generate-baseline.py`** keeps **`baseline/`**, the mirrored **`docs/baseline/`** tree (Pages same-origin JSON), [`POLICY_INVENTORY.md`](./POLICY_INVENTORY.md), SPA tables (`docs/inventory.html`, `docs/index.html`), and README appendices aligned — see [Customize & fork](#customize--fork).

[`docs/deploy.js`](docs/deploy.js) runs the manifest flow; **`baseline/manifest.json`** defines deploy order.

## Deploy in your tenant

Delegated roles that can complete the flow commonly include combinations of **Conditional Access Administrator**, **Groups Administrator**, **Security Administrator**, or **Global Administrator**.

1. Open the **[deploy web app](https://teuftis.github.io/ConditionalAccessBaseline-Hardened/)** (blank baseline or errors → [GitHub Pages](#github-pages) troubleshooting).
2. **Sign in** and accept **delegated** Microsoft Graph scopes.
3. Optionally keep **Dry run** enabled (preview only — no tenant writes), then disable it for a real run.
4. Read the activity log: **skipped** (missing deps), **unchanged** (existing **display name** already in tenant), **created**, or **error** (Graph rejected the payload — often schema or missing prerequisite).

**Writes vs what stays unchanged on re-run**

| Artifact | Behavior |
|---------|----------|
| Conditional Access policies | **POST** creates a policy **only when no existing policy shares that normalized display name** (exact or Unicode hyphen-normalized match). Existing policies are **never PATCH**ed — state stays as in the tenant. |
| Groups | Ensured exists; membership and props are **not** updated afterward — only reused for ID resolution during deploy. |
| Named locations | Created if missing; if present, IPs/countries definitions are **not** overwritten automatically. |

The log summarizes outcomes (including skips like **`firstPartyApp:`**… when required Microsoft-native apps lack a tenant service principal binding).

### After deploy in Microsoft Entra admin center

1. Populate **named location** ranges/countries and **group** memberships (break-glass, exclusions, pilots, automation groups).
2. Review **Protection → Conditional Access**, **Sign-in logs**, and Conditional Access insights before changing policy effect.
3. Move policies **report-only**, then **on**, **in phases** that match your runbook — enabling everything at once rarely ends well.

## Safety and trust

| Topic | What to know |
|-------|----------------|
| **Credentialed only** | The SPA uses your admin session and **delegated** Graph scopes. There is **no** OAuth client secret in Git ([`docs/config.js`](docs/config.js)). |
| **Writes are guarded** | New CA policies arrive **disabled** ([`ALLOWED_DEPLOY_STATES`](docs/config.js)). Existing tenants keep live rules because policies that **match display name** (after normalization shown in Customize) are skipped — zero silent overwrites via PATCH. Turning policies **report-only / on** stays a **manual** admin-center decision. |
| **Supply chain** | Whatever ships on **GitHub Pages** from `main` is what browsers execute — protect the default branch and review PRs that touch `docs/` or CI. |

## Customize & fork

| Task | Steps |
|------|-------|
| **Change policies or groups** | Edit **`POLICIES`** / **`GROUPS`** (and related structures) in [`scripts/generate-baseline.py`](scripts/generate-baseline.py). Run **`python scripts/generate-baseline.py`**. Commit **`baseline/`**, **`docs/baseline/`**, **`POLICY_INVENTORY.md`**, **`docs/inventory.html`**, **`docs/index.html`**, and the README appendix regions this script rewrites. On Windows, save the script as **UTF-8**. |
| **Naming in Entra** | Generated **`displayName`** patterns look like **`CA101 — Require MFA`** (em dash **`—`**). Deploy loads all CA policies, then dedupes with exact match **plus** Unicode hyphen normalization and casing (so **`CA101 -`** still matches **`CA101 —`**). Dupes skip creation — rename or delete stale Entra copies if you need a regenerate. |
| **Fork another app registration** | Multitenant **public client SPA** registration (still no secrets). Paste **`clientId`** + HTTPS redirect URIs into [`docs/config.js`](docs/config.js), expose matching [`GRAPH_SCOPES`](docs/config.js), re-enable Pages hosting on your GH org. |
| **Hack locally** | From repo root, `python -m http.server` (or VS Code Live Server). Open **`/docs/`**. Register **localhost** redirect URIs on the Entra SPA app alongside your production Pages URL pairings. |

## GitHub Pages

The browser bundle is **`docs/`**, emitted by [.github/workflows/deploy-pages.yml](.github/workflows/deploy-pages.yml) whenever **`main`** updates.

Pages needs one-time **[Settings → Pages → GitHub Actions](https://docs.github.com/pages/getting-started-with-github-pages/about-github-pages)** (historic **branch `/docs`** path also works).

**Architecture note:** workflows run **`rm -rf docs/baseline && cp -r baseline docs/baseline`** so `fetch("./baseline/manifest.json")` stays **same-origin** with the SPA (reduces CORS pain vs only raw GitHub raw endpoints). The generator copies the same mirror when you run it locally.

**404 or empty manifest in the live app?** Confirm the **Deploy GitHub Pages** workflow finished. Hard-refresh. Legacy forks that never got the copy step can still override `window.MIRAGE_BASELINE_URL` to a reachable baseline root or fall back to **raw.githubusercontent.com** (requires `baseline/` on your default branch).

## Further reading

- [Conditional Access overview — Microsoft Learn](https://learn.microsoft.com/entra/identity/conditional-access/overview)
- [Policies and assignments](https://learn.microsoft.com/entra/identity/conditional-access/concept-conditional-access-policies)
- [Named locations](https://learn.microsoft.com/entra/identity/conditional-access/concept-assignment-network)

## Policy catalog

**Appendix.** The summary table below mirrors [`POLICY_INVENTORY.md`](./POLICY_INVENTORY.md) and the spreadsheet summary (ID, policy title, persona, criticality). It auto-regenerates from JSON when you run **`scripts/generate-baseline.py`**. GitHub Markdown does not support Excel-style cell shading; **criticality** is shown with colored badges (same semantics as the pills in **[inventory.html](https://teuftis.github.io/ConditionalAccessBaseline-Hardened/inventory.html)**). Full descriptions stay in each policy JSON; use the inventory page or `POLICY_INVENTORY.md` for prose.

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

## Groups (Entra)

**Appendix (auto-generated).** Every entry below maps to a JSON file under [`baseline/groups/`](./baseline/groups/). Policy intent references these by display name; deploy resolves them to object IDs. **`tier`** labels mean **Required** (foundation), **Service track** (automation splits for CA801/802), **Exception** (short-lived bypasses), **Pilot** (narrow experiments). **`mailNickname`** values are chosen for Graph uniqueness at creation time.

<!-- group-catalog:start -->
- **BG_BreakGlass** — Required — mailNickname `bg-breakglass`
  Break-glass and other emergency administrator accounts that must remain reachable if Conditional Access misconfiguration locks out normal admins. Keep membership empty until accounts exist; remove members when not actively needed. Excluded from nearly all CA policies so use only for documented recovery procedures.
- **AC_ExcludedFromCA** — Required — mailNickname `ac-excludedfromca`
  Catch-all exclusion for identities that must never be evaluated by user-facing CA (for example certain directory sync or legacy integration principals your vendor documents as CA-exempt). Treat membership as highly privileged—every account here bypasses most workforce controls.
- **AC_ServiceAccount** — Required — mailNickname `ac-serviceaccount`
  Parent group for non-human and automation accounts. Policies that target all users exclude this group so background jobs are not forced through interactive MFA. Nest members into the interactive vs non-interactive child groups so CA801 can target only human-driven service logons.
- **AC_ServiceAccount_Interactive** — Service track — mailNickname `ac-serviceaccount-interactive`
  Service principals or managed identities that sometimes sign in through a browser or device-code style flow. CA801 requires MFA for this population while leaving pure client-credential automation in the non-interactive sibling group.
- **AC_ServiceAccount_NonInteractive** — Service track — mailNickname `ac-serviceaccount-noninteractive`
  Automation identities that only use client credentials, managed identity, or other non-interactive OAuth flows. Excluded from CA801 so scheduled jobs are not blocked; pair with CA802-CA804 for network and app restrictions.
- **AC_TravelException** — Exception — mailNickname `ac-travelexception`
  Short-lived membership for employees who must sign in from outside TRUSTED_COUNTRIES during approved travel. CA106 excludes this group from the country condition so the geofence still applies to everyone else; expire memberships when the trip ends.
- **AC_DeviceCodeApproved** — Exception — mailNickname `ac-devicecodeapproved`
  Rare allowance for CA108's block on device-code and authentication-transfer flows (for example controlled kiosk or DevOps scenarios). Add only fully trusted principals; every member is a phishing surface.
- **AC_TokenProtection_Pilot** — Pilot — mailNickname `ac-tokenprotection-pilot`
  Users or devices included in the CA113 Windows token-protection pilot. Start with a small population, collect sign-in and help-desk telemetry, then expand membership as your estate supports the feature.
- **AC_ExcludedAgents** — Exception — mailNickname `ac-excludedagents`
  Workload agent or service principal objects that must not be blocked by CAA01 when Identity Protection flags them high risk (for example monitored automation with known false positives). Keep the group tiny and review quarterly.
- **AC_MSP_PartnerUsers** — Exception — mailNickname `ac-msp-partnerusers`
  Delegated administrator or partner accounts that need access to Microsoft 365 admin experiences blocked for standard guests in CA905. Requires explicit lifecycle: remove access when the engagement ends.
- **AUTOPILOT_DevicePrep** — Exception — mailNickname `autopilot-deviceprep`
  Device objects undergoing Windows Autopilot pre-provisioning so they can complete join/enrollment without triggering CA112 MFA-on-join or CA201 enrollment MFA prematurely. Clean up stale device members after deployment finishes.
<!-- group-catalog:end -->

## Legal & reference

- **License:** [MIT License](./LICENSE)
- **Security:** [SECURITY.md](./SECURITY.md) (prefer GitHub **Security → Report a vulnerability**)
- **`reference/` spreadsheets:** Design-time `.xlsx` companions for the baseline (not read by the deploy runtime). Office XML in this repo was scrubbed for obvious sensitive strings (no emails, no `.onmicrosoft` patterns, no extra HTTP(S) URLs beyond Open XML schema refs). Re-scan if you fork and diverge.
