# Mirage Conditional Access Baseline (v2026)

**Opinionated, production-style Conditional Access for Microsoft Entra ID** — stored as JSON in this repo and applied with a **small static web app** (no backend, no client secret in Git). Sign in as a tenant admin, consent to Microsoft Graph, and create **new** policies, groups, and named locations. **New Conditional Access policies are created in Off (disabled)**. If a policy **display name** already exists in the tenant, the deploy app **does not overwrite it** (so active settings stay intact). You turn policies on in the admin center when you are ready.

**This is not a Microsoft product.** Treat the baseline as a starting point: validate against your apps, licenses (for example Entra ID P2 for risk-based policies), and change process.

| | |
|---|---|
| **Live deploy app** | [teuftis.github.io/ConditionalAccessBaseline-Hardened](https://teuftis.github.io/ConditionalAccessBaseline-Hardened/) |
| **Source** | [Teuftis/ConditionalAccessBaseline-Hardened](https://github.com/Teuftis/ConditionalAccessBaseline-Hardened) |
| **Browse policies (styled)** | [inventory.html](https://teuftis.github.io/ConditionalAccessBaseline-Hardened/inventory.html) on GitHub Pages |

[![Open deploy app](https://img.shields.io/badge/Open-deploy%20app-0078D4?logo=microsoftazure&logoColor=white&style=for-the-badge)](https://teuftis.github.io/ConditionalAccessBaseline-Hardened/)

Tenant admins → **[Deploy in your tenant](#deploy-in-your-tenant)** · Fork owners → **[GitHub Pages](#github-pages)** · **[Customize & fork](#customize--fork)**

---

### On this page

| Section | Contents |
|---------|----------|
| [Overview](#overview) | What ships in `baseline/` and how writes work |
| [Deploy](#deploy-in-your-tenant) | Steps to run the app in your directory |
| [After deploy](#after-deploy-in-microsoft-entra-admin-center) | Portal work before turning policies on |
| [Trust](#trust) | Permissions, posture, reviewer expectations |
| [GitHub Pages](#github-pages) | Publishing the SPA from this repo |
| [Customize](#customize--fork) | Editing the baseline and running the generator |
| [Further reading](#further-reading) | Microsoft docs |
| [Policy catalog](#policy-catalog) | Full regenerated list (~40 rows) |
| [Groups](#groups-entra) | Regenerated Entra group summaries |

---

## Overview

Baseline objects live under **`baseline/`**: **intent** JSON for policies (**not** raw Graph bodies — [`docs/translate.js`](docs/translate.js) turns names into IDs at deploy time).

| Artefact | Count | Location |
|---------|-------|----------|
| Conditional Access policies | 40 | [`baseline/policies/`](./baseline/policies/) |
| Groups | 11 | [`baseline/groups/`](./baseline/groups/) |
| Named locations | 4 | [`baseline/namedLocations/`](./baseline/namedLocations/) |

You do **not** need to clone the repo to deploy: open the **[deploy app](https://teuftis.github.io/ConditionalAccessBaseline-Hardened/)** after [Pages](#github-pages) is publishing. Scoped policies (for example optional SaaS apps) **may skip** if the referenced service principal is missing. Terms of Use are **your** objects — they are **not** created automatically.

[`POLICY_INVENTORY.md`](./POLICY_INVENTORY.md) is a Markdown table suited to reviews and PR diffs; the **[styled catalog](https://teuftis.github.io/ConditionalAccessBaseline-Hardened/inventory.html)** adds layout and filters. **`python scripts/generate-baseline.py`** keeps `baseline/`, those files, SPA tables, and the **Policy catalog / Groups** sections at the bottom of this README in sync (see **[Customize & fork](#customize--fork)**).

**Safe defaults:** new policies only are created **`disabled`** (**Off**) — see [`ALLOWED_DEPLOY_STATES`](docs/config.js). Policies that already exist (matched by **display name**) are never updated by the app. Moving to Report-only or On stays a **manual** admin-center step.

---

## Deploy in your tenant

You need permissions to manage **Conditional Access** and **groups** (typical combos: **Conditional Access Administrator** + **Groups Administrator**, **Security Administrator**, or **Global Administrator**, depending on the tenant).

1. Open the **[deploy web app](https://teuftis.github.io/ConditionalAccessBaseline-Hardened/)** ([troubleshooting](#github-pages) if you get **404** or an empty baseline).
2. **Sign in** and complete **delegated consent** for the requested Microsoft Graph scopes.
3. Optionally leave **Dry run** enabled to preview (**no tenant writes**), then disable it and run **Deploy**.
4. Scan the activity log — **optional workloads** may show as **skipped** (missing dependencies); **Conditional Access policies** whose **display name** already exist show as **unchanged** (not overwritten). Policies that could not POST will show **error** until prerequisites or translation rules are addressed.

**What writes vs what is left alone**

| Artefact | On re-run |
|----------|-----------|
| **Conditional Access policies** | **POST** only when no policy with that **display name** exists. Existing policies are **never PATCHed** (state and rules stay as in the tenant). |
| **Groups** | Created if missing; if the group exists, its **membership and properties are not updated**—only reused for ID resolution. |
| **Named locations** | Created if missing; existing objects are reused **without** overwriting IP/country definitions. |

The activity log summarizes **created**, **unchanged**, **skipped**, and **errors** (including **`firstPartyApp:…`** when a Microsoft app lacks a tenant service principal).

### After deploy in Microsoft Entra admin center

1. Finish **named location** definitions and **group** membership (break glass, exclusions, automation groups, pilots).
2. Review **Protection → Conditional Access** and use **Sign-in logs** / **Conditional Access insights** before changing policy states.
3. Turn policies **On** in **phases** that match your runbook rather than flipping the full set at once.

---

## Trust

| Topic | Detail |
|-------|--------|
| **Credentialed access only** | The SPA uses your admin sign-in via **delegated** Graph scopes — nothing runs without **you**. There is **no** client secret in the repo ([`docs/config.js`](docs/config.js)). |
| **Writes are limited by design** | **New** CA policies are created **`disabled`**. **Existing** CA policies (same **display name**) are **not patched** by the app. Report-only / On remain **portal-only** choices. |
| **Supply chain** | `main` (and whoever can publish **GitHub Pages**) controls what browsers execute — review PRs and protect the default branch accordingly. |

---

## GitHub Pages

The SPA is **`docs/`**, deployed by [.github/workflows/deploy-pages.yml](.github/workflows/deploy-pages.yml) on pushes to **`main`**.

**First publish:** Repository **Settings → Pages** → source **GitHub Actions** (or **Deploy from branch** → **`main` / `/docs`**). Run the workflow and approve **`github-pages`** if GitHub prompts. A short delay before the site appears is normal.

**404 or missing manifest?** Confirm the **Deploy GitHub Pages** workflow has run after this change (it copies `baseline/` beside the SPA). Hard-refresh the site. Older setups that only publish `docs/` without that copy can still set `window.MIRAGE_BASELINE_URL` to a reachable `.../baseline` base URL, or rely on **raw.githubusercontent.com** as the second fallback (requires `baseline/` committed on `main`). Background: [About GitHub Pages](https://docs.github.com/pages/getting-started-with-github-pages/about-github-pages).

---

## Customize & fork

| Task | Steps |
|------|-------|
| **Change policies or groups** | Edit **`POLICIES`** / **`GROUPS`** (and related structs) in [`scripts/generate-baseline.py`](scripts/generate-baseline.py); run **`python scripts/generate-baseline.py`**; commit **`baseline/`**, **`POLICY_INVENTORY.md`**, **`docs/inventory.html`**, **`docs/index.html`**, and the generated sections in **`README.md`**. On Windows save the script as UTF-8. |
| **Naming in Entra** | Generated **`displayName`** values look like **`CA101 — Require MFA`**; deploy looks up existing policies **by that exact name**. Matches are **skipped** (not deleted or PATCHed)—rename or remove a conflicting object in Entra if you intend the app to POST a fresh policy. Older manual names cause **duplicate** parallel policies unless you align names first. |
| **Fork another account** | Create a multitenant SPA app registration (**public client**, no secret), plug **`clientId`** and redirect URIs into [`docs/config.js`](docs/config.js), enable Pages, use **`https://<you>.github.io/<repo>/`**, and mirror [`GRAPH_SCOPES`](docs/config.js). |
| **Hack locally** | From repo root run `python -m http.server` (or equivalent), open **`/docs/`**, add **localhost** redirect URIs on the app registration. |

[`docs/deploy.js`](docs/deploy.js) orchestrates sequencing; **`baseline/manifest.json`** controls order.

---

## Further reading

- [Conditional Access overview — Microsoft Learn](https://learn.microsoft.com/entra/identity/conditional-access/overview)
- [Policies and assignments](https://learn.microsoft.com/entra/identity/conditional-access/concept-conditional-access-policies)
- [Named locations](https://learn.microsoft.com/entra/identity/conditional-access/concept-assignment-network)

---

## Policy catalog

Each bullet is **policy id — short title — persona — criticality**; the indented line matches the **`description`** field from that policy JSON. Prefer **[inventory.html](https://teuftis.github.io/ConditionalAccessBaseline-Hardened/inventory.html)** for browsing — full list for search and clones below. **[POLICY_INVENTORY.md](./POLICY_INVENTORY.md)** duplicates this as a table. Regenerated alongside **[Groups (Entra)](#groups-entra)** by **`scripts/generate-baseline.py`**.

<!-- policy-catalog:start -->
- **CA101** — Require MFA — All users — Critical
  Foundation control for workforce users: requires multifactor authentication on every interactive sign-in to cloud applications. Applies broadly (all users) with exclusions for break-glass, CA-wide exclusions, service principals in AC_ServiceAccount, and external/guest identities (covered by guest policies).
- **CA102** — User Risk - Require MFA + Password Change — All users — Critical
  Identity Protection remediation for elevated user risk (medium or high): requires MFA and a secure password change during the session. Depends on Entra ID P2 (user risk evaluations). Honors standard exclusions including guests and externals disabled for this persona.
- **CA103** — Sign-In Risk - Require MFA — All users — Critical
  Identity Protection challenge for risky sign-ins (medium or high): requires MFA to continue the session when Entra evaluates elevated sign-in risk. Requires Entra ID P2. Excludes universal exclusions and separates guest traffic via policy construction.
- **CA104** — Block Legacy Authentication — All users — Critical
  Tenant-wide legacy authentication hardening: blocks basic authentication and legacy client protocols (for example POP, IMAP, SMTP AUTH, authenticated SMTP, and broader legacy client application types aligned with Microsoft guidance). Enables a dependable modern-auth-only posture; pair with workload-specific disables.
- **CA105** — Block Unknown Platforms — All users — Recommended
  Device-platform allow list: denies access when the client is not Windows, macOS, iOS, Android, or Linux. Mitigates access from unmanaged or unexpected operating systems across all workloads in scope.
- **CA106** — Block Outside Trusted Countries — All users — Critical
  Geolocation control using the TRUSTED_COUNTRIES named location. Sign-ins originating outside trusted regions are blocked unless the user is exempted via AC_TravelException (time-bounded travel). Excludes the travel exception group from the country condition so legitimate trips still work.
- **CA107** — Session Controls — All users — Recommended
  Session tightening for standard users: enforces recurring reauthentication (twelve-hour sign-in frequency) and disallows persistent browser sessions. Applies a device filter so compliant or hybrid Entra joined devices can be handled according to organizational exception rules.
- **CA108** — Block Cross-Device Auth Flows — All users — Critical
  Blocks high-abuse OAuth flows tied to phishing: denies device-code authentication and OAuth authentication transfer where supported. Exempts freshly approved enterprise device registrations that still need onboarding.
- **CA109** — Require MFA for Azure Management — All users — Recommended
  Protects Azure resource management workloads: MFA is required whenever accessing Azure portal, CLI, REST, Infrastructure-as-Code, or other ARM-related applications. Targets the workload identity surface used to change tenant posture.
- **CA110** — Block Malicious IPs — All users — Optional
  Threat-intelligence egress control: denies sign-ins that map to indicators in the MALICIOUS_IPS named location (populate with SOC or feed-driven ranges before enforcement). Complements geo and risk policies.
- **CA111** — Continuous Access Evaluation - Standard — All users — Recommended
  Continuous Access Evaluation in standard sensitivity for workforce accounts: reacts faster to revocation or policy changes compared with long-lived tokens. Administrators should pair with CA603 (strict CAE). Deploy note: Microsoft Graph rejects some CAE-only session payloads that also exclude guests/externals; the deploy SPA omits excludeGuestsOrExternalUsers for this rule (see docs/translate.js); guest collaborators remain covered by other baseline policies.
- **CA112** — MFA on Device Register or Join — All users — Critical
  Strengthens Entra device registration and join endpoints: MFA is required anytime a user completes device registration or Workplace Join/Azure AD join workflows, reducing unauthorized device onboarding.
- **CA113** — Require Token Protection (Pilot) — All users — Optional
  Pilot control binding primary refresh tokens more tightly on supported Windows workloads (token protection). Limits token replay when adversaries steal session material via phishing proxies. Applies only to the AC_TokenProtection_Pilot group—expand deliberately after telemetry review.
- **CA114** — Terms of Use — All users — Optional
  Regulatory / policy attestation workflow: prompts users for Microsoft Entra Terms of Use before access. Organizations must provision a tenant-specific Terms of Use object and inject its GUID at deployment time (see deploy SPA configuration).
- **CA201** — Intune Enrolling - Require MFA — All users — Critical
  Secures enrollment into Microsoft Intune: MFA is mandated when enrolling a freshly managed endpoint so attackers cannot silently attach devices without strong proof of possession.
- **CA202** — Require App Protection (Mobile) — All users — Critical
  Mobile application protection posture for Microsoft 365: requires Intune App Protection Policies on iOS and Android M365 workloads. Matches Microsoft’s APP enforcement model (replaces fragile approved-client-app keyword matching).
- **CA204** — Require Compliant Mobile (Optional MDM track) — All users — Optional
  Optional hardened path for supervised mobile fleets: complements CA202 by requiring Intune-compliant devices on MDM-enrolled handhelds running iOS/Android. Omit or soften if you intentionally stay app-protection-only without enrollment.
- **CA301** — Require Compliant Windows — All users — Critical
  Corporate Windows laptops and desktops must be Entra hybrid joined or marked Intune-compliant before granting access to Microsoft 365 and related cloud apps.
- **CA302** — Require Compliant macOS — All users — Critical
  Same enforcement as CA301 scoped to macOS clients: unmanaged Macs cannot access Microsoft 365 data until they enroll and report healthy compliance posture.
- **CA303** — Limited Browser Access on Unmanaged Devices — All users — Recommended
  Reduces unmanaged-device blast radius under Microsoft 365: browser sessions can remain read-only/view-like against Exchange Online / SharePoint when the device fails the trusted workstation filter yet still needs lightweight productivity.
- **CA601** — Phishing-Resistant MFA for Admins — Admins — Critical
  Privileged role assignments (Azure AD Directory Roles, Delegated Administrative Partners, cloud-only role-backed accounts) must use phishing-resistant MFA (FIDO2, Windows Hello for Business with attestation, or federated certificate-based authentication where applicable).
- **CA602** — Admin Session Controls — Admins — Critical
  Admin session containment: repeats the tighter session controls applied to privileged accounts—maximum four-hour recurring authentication and disallow persistent browser sessions—for every identity holding directory or workload admin roles included in Privileged Administrators.
- **CA603** — Admin CAE - Strict — Admins — Critical
  Strict Continuous Access Evaluation for privileged identities paired with Conditional Access Strict Location evaluation: reacts immediately to IP deltas and high-sensitivity revocation signals suitable for Tier-0 workloads. Evaluate change windows carefully given Real Time CAE telemetry requirements.
- **CA604** — Admin Block High User Risk — Admins — Critical
  Break-glass for risky operators: denies admin role holders when Entra Identity Protection marks the user risky at high severity. Keeps admins from deepening compromise while investigative controls run.
- **CA605** — Admin Block High Sign-In Risk — Admins — Critical
  Complements CA604 using sign-in risk for administrators: denies access when Identity Protection observes high sign-in risk, closing scenarios where compromised tokens still pass user-risk heuristics slowly.
- **CA606** — Admin Require Compliant or Joined Device — Admins — Critical
  Device trust bar for admins: privileged changes may only originate from Hybrid Entra Joined workstations or devices reporting compliant posture to Intune, preventing lateral movement from unmanaged kit.
- **CA701** — App - FortiClient - MFA — Application — Optional
  Zero Trust gate for perimeter VPN integrations (Fortinet FortiClient in template form): MFA before granting network tunnel access aligned with phishing-resistant MFA investments elsewhere.
- **CA702** — App - Salesforce - MFA — Application — Optional
  SaaS control for Salesforce: interactive users must satisfy MFA whenever accessing Salesforce through Entra  SSO. Requires a valid enterprise application / service principal in the tenant reflecting production URLs.
- **CA801** — Service - Require MFA (Interactive) — Service — Recommended
  Service principal hardening subset: mandates MFA whenever the delegated application signs in interactively (think human-driven scripts). Daemon / client-credential workloads remain out of scope via negative group conditioning paired with exclusions.
- **CA802** — Service - Block Outside Trusted IPs — Service — Critical
  Network perimeter for unattended automation: restricts allowed sign-ins for centralized service principals to the corporate or partner IP ranges modeled in SVC_TRUSTED_IPS, blocking roaming or hostile networks.
- **CA803** — Service - Block Legacy Auth — Service — Recommended
  Defense-in-depth block on legacy protocols for workloads using service principals: reinforces CA104 baseline by narrowly scoping SMTP AUTH/similar exposures that often slip through scripted automation identities.
- **CA804** — Service - Block Non-M365 Apps — Service — Recommended
  Least-privilege SaaS stance for robotic identities: confines service credentials to approved Microsoft 365 applications while denying access to tertiary SaaS and consumer OAuth clients.
- **CA901** — Guest - Require MFA — Guest — Critical
  Guest/B2B collaboration MFA: ensures every federated partner user proves MFA freshness in your tenant, closing the reliance on weaker home-tenant MFA states alone.
- **CA902** — Guest - Block High Sign-In Risk — Guest — Recommended
  Guest risk remediation: denies high sign-in-risk events even when the guest’s home tenant is lenient (defense against cross-tenant token theft).
- **CA903** — Guest - Block Legacy Auth — Guest — Recommended
  Prevents scripted or legacy-protocol abuse for guest personas; layered with CA901 to mandate modern apps and interactive controls.
- **CA904** — Guest - Block Outside Trusted Countries — Guest — Critical
  Geographic guardrail for collaborators: restricts guest access paths to countries mirrored in trusted named locations (typically broader lists than workforce policies). Pair with onboarding guidance for visiting partners.
- **CA905** — Guest - Block Non-Collaboration Apps — Guest — Critical
  Data-exfiltration control for guests collaborating in Microsoft Teams/Groups: confines Office 365 workloads while blocking ancillary SaaS (except explicitly excluded apps such as delegated admin workloads).
- **CA906** — Guest - Terms of Use — Guest — Optional
  Guest-visible Terms-of-Use acknowledgement for contractual or jurisdictional onboarding before accessing shared resources.
- **CA907** — Guest - Session Controls — Guest — Recommended
  Session hygiene for collaborators: aligns guest browser sessions with the twelve-hour MFA refresh posture so stolen guest tokens degrade quickly—mirroring CA107 protections for internals.
- **CAA01** — Agent - Block High Risk — Agent — Recommended
  Workload identities (service principals using agent delegation) flagged high risk by Identity Protection lose access immediately across cloud apps targeted by the workload persona until risk clears.
<!-- policy-catalog:end -->

## Groups (Entra)

Deployed from [`baseline/groups/`](./baseline/groups/) with the SPA. **`tier`** labels: **Required** (foundation), **Service track** (automation subdivisions referenced by CA801/802 paths), **Exception** (short-lived bypasses), **Pilot** (narrow experiments). **`mailNickname`** values are chosen for uniqueness at creation time via Graph.

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

---

## License

Licensed under the [MIT License](./LICENSE).

## Security

Report vulnerabilities as described in [SECURITY.md](./SECURITY.md) (prefer GitHub **Security → Report a vulnerability**).

## Reference spreadsheets

The **`reference/`** `.xlsx` files are companion material for baseline design (not consumed at runtime by the deploy app). Embedded Office XML has been scanned for obvious sensitive strings: **no email addresses**, **no `.onmicrosoft` / tenant-style identifiers**, and **no non-schema HTTPS/HTTP URLs** beyond standard Open XML schema namespaces. Re-scan your copy if it diverges from this repository before wider distribution.
