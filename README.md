# Mirage CA Baseline

A Conditional Access baseline for Microsoft 365 plus a browser-based deployer. 41 policies covering users, admins, applications, service accounts, guests, and workload identities, with 11 supporting groups and 4 named locations.

Deployer: https://teuftis.github.io/ConditionalAccessBaseline-Hardened/

Click the badge, sign in as a CA admin, deploy. The deployer is a single-page app using PKCE — no client secret, no backend, no GitHub Actions, no Cloud Shell. Your delegated Graph token does the work and dies when the tab closes.

[![Open deploy app](https://img.shields.io/badge/Open-deploy%20app-0078D4?logo=microsoftazure&logoColor=white&style=for-the-badge&logoWidth=28)](https://teuftis.github.io/ConditionalAccessBaseline-Hardened/)

Quick links: [deployer](https://teuftis.github.io/ConditionalAccessBaseline-Hardened/) · [policy catalog (filterable)](https://teuftis.github.io/ConditionalAccessBaseline-Hardened/inventory.html) · [POLICY_INVENTORY.md](./POLICY_INVENTORY.md) · [SECURITY.md](./SECURITY.md)

## What gets created

41 Conditional Access policies, 11 groups, and 4 named locations. Stored as intent JSON under [`baseline/`](./baseline/), not as raw Graph exports — the deployer in [`docs/`](./docs/) resolves display names to object IDs at write time.

The policy catalog and group descriptions are at the bottom of this README. Full per-policy detail lives in [`baseline/policies/`](./baseline/policies/).

### Why CA304 — Require Compliant Linux

Added to close the Linux User-Agent spoof gap: the CA platform condition is self-reported (from User-Agent), so without CA304, an attacker can present `User-Agent: Linux` and skip the Windows/macOS/mobile compliance gates. CA304 requires compliant Linux devices, completing the platform coverage. If you don't run managed Linux endpoints, drop `linux` from CA105's exclude list to block it outright instead.

## What state policies deploy in

Most land in **Report-only**. Eight specific policies deploy **disabled** because Report-only either doesn't apply to them cleanly or misrepresents what they'd do once enforced — those are `CA111`, `CA202`, `CA204`, `CA302`, `CA303`, `CA603`, `CA606`, `CAA01`. The list lives in `POLICY_IDS_DEPLOY_DISABLED_BY_DEFAULT` in [`docs/translate.js`](docs/translate.js) and `ALLOWED_DEPLOY_STATES` in [`docs/config.js`](docs/config.js) blocks the SPA from creating anything in the On state regardless of intent. You enable manually from the Entra admin center after reviewing telemetry.

If a policy with the same display name already exists in the tenant, deploy leaves it alone. There is no PATCH path. Same for groups and named locations: created if missing, never overwritten.

You can override the default state per-policy in a fork by adding `deploymentState` (or `deployState`) to a policy intent file. That only affects the first POST when no policy with that name exists yet — it doesn't unlock PATCH.

## Deploying

You need one of: Conditional Access Administrator, Security Administrator, Groups Administrator, or Global Admin. The first three combined cover all the writes the deployer makes; Global covers everything if you'd rather not split roles.

1. Open the deployer.
2. Sign in. Accept the delegated Graph scopes.
3. Run with **Dry run** enabled the first time. No writes happen, but you'll see exactly what would.
4. Clear Dry run and run again to actually deploy.
5. Read the activity log. Outcomes are `created`, `unchanged` (display name already matches), `skipped` (missing prerequisite — usually a third-party service principal that doesn't exist in your tenant yet), or `error`.

After deploy, in the Entra admin center:

- Populate group memberships (break-glass, exclusions, pilot groups, automation groups).
- Fill in named location IP ranges and country lists. The placeholders are empty.
- Review CA insights and sign-in logs against the Report-only policies.
- Move policies to On in phases when telemetry says it's safe.

The Microsoft Sentinel queries at the bottom of this README are what I use to triage Report-only and hard-failure outcomes.

## Auth model

Whatever lands on `main` and gets published to GitHub Pages is what runs in the admin's browser. Branch protection on `main` and code review on anything under [`docs/`](./docs/) or [`.github/workflows/deploy-pages.yml`](.github/workflows/deploy-pages.yml) are the controls that count. Treat them as such if you fork.

## Forking it for your own MSP

You'll want your own multitenant SPA registration and your own GitHub Pages site so customers see your branding, not mine.

1. Register a multitenant single-page application in your tenant. Add `https://<your-org>.github.io/<repo>/` as a redirect URI. No secret. Delegated scopes: `Policy.ReadWrite.ConditionalAccess`, `Policy.Read.All`, `Group.ReadWrite.All`, `Directory.Read.All`, `Application.Read.All`, `User.Read`.
2. Fork this repo. Edit [`docs/config.js`](docs/config.js): replace `clientId` and the redirect URI list. `GRAPH_SCOPES` is in the same file.
3. Settings → Pages → GitHub Actions. The included [`deploy-pages.yml`](.github/workflows/deploy-pages.yml) builds and publishes on push to `main`.
4. Put your own deploy badge in your README.

To change the actual policies, edit the `POLICIES` and `GROUPS` dicts in [`scripts/generate-baseline.py`](scripts/generate-baseline.py), then run `python scripts/generate-baseline.py`. The generator rewrites everything under `baseline/`, mirrors it to `docs/baseline/` for same-origin fetch from the SPA, and regenerates `POLICY_INVENTORY.md` plus the appendix tables in this README. Commit all of those together.

For local hacking: `python -m http.server` from the repo root, open `/docs/`, and add a localhost redirect URI alongside your production one on the SPA registration.

## GitHub Pages

The browser bundle lives under [`docs/`](./docs/) and rebuilds via [`deploy-pages.yml`](.github/workflows/deploy-pages.yml) on every push to `main`. Configure Pages once under Settings → Pages → GitHub Actions (older "publish from branch `/docs`" works too).

The workflow runs `rm -rf docs/baseline && cp -r baseline docs/baseline` so `fetch("./baseline/manifest.json")` stays same-origin with the SPA. `generate-baseline.py` does the same locally. If you fork an older copy that lacks this step, set `window.MIRAGE_BASELINE_URL` or fall back to raw.githubusercontent.com URLs (subject to CORS).

If the deployer loads blank or 404s on the manifest, the Pages workflow probably hasn't completed yet. Check Actions, then hard refresh.

## Caveats

- Not a Microsoft product. Nothing here is supported by them.
- Risk-based policies need Entra ID P2.
- Graph and CA schemas drift. If a POST returns 400, the schema probably moved — open an issue with the response body.
- Display names use an em dash, e.g. `CA101 — Require MFA`. The deployer normalizes em-dash and hyphen variants when matching, but policies you've already created with a different convention won't be touched.
- Terms of Use objects are tenant-owned by Microsoft's design. The deployer can't create them.
- Use a non-prod tenant for first runs if you have one, and confirm at least one break-glass account is excluded from everything before flipping any policy to On.

## Issues and contributions

Issues are the right place to start. A reproduction with the deployer's activity log helps most. PRs require collaboration access on this repo — open an issue first and we can sort it from there.

## Repo layout

```
baseline/                  intent JSON: policies, groups, namedLocations
docs/                      the deployer (GitHub Pages source)
scripts/                   generate-baseline.py — rebuilds baseline/ from dicts
reference/                 authoring spreadsheets, not read at runtime
.github/workflows/         deploy-pages.yml publishes Pages on main
POLICY_INVENTORY.md        markdown mirror of the policy table below
SECURITY.md                prefer GitHub Security → Report a vulnerability
LICENSE                    MIT
```

---

## Policy catalog

Auto-generated from [`baseline/policies/`](./baseline/policies/) via `python scripts/generate-baseline.py`. The filterable version is at [inventory.html](https://teuftis.github.io/ConditionalAccessBaseline-Hardened/inventory.html).

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
| CA304 | Require Compliant Linux | All users | ![Critical](https://img.shields.io/static/v1?label=&message=Critical&color=c62828&style=flat-square) |
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

## Groups

Each group below has a JSON file under [`baseline/groups/`](./baseline/groups/). Policies reference groups by display name; the deployer binds them to object IDs at write time. The `mailNickname` values are there to satisfy Graph's uniqueness constraint at creation.

`tier` values: **Required** is foundation, **Service track** is the automation split that lets CA801 hit interactive service logons without breaking unattended ones, **Exception** is short-lived allowances, **Pilot** is narrow experiments.

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

## Microsoft Sentinel queries

Two KQL queries I use to triage outcomes from the Report-only and enforced policies. They assume `SigninLogs` and `AADNonInteractiveUserSignInLogs` (or equivalents) are in the workspace.

### Report-only and hard failures, 5-day lookback

Triages Report-only outcomes (`reportOnlyFailure`, `reportOnlyInterrupted`) alongside production hard fails (`failure`, `interrupted`). Includes legacy auth and device posture context.

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

### Enforced (On) policies, hard failures only, 1-day lookback

Same shape, narrower window, drops Report-only outcomes. Use this for ops triage of policies you've already moved to On.

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

## Further reading

- [Conditional Access overview](https://learn.microsoft.com/entra/identity/conditional-access/overview)
- [Policies and assignments](https://learn.microsoft.com/entra/identity/conditional-access/concept-conditional-access-policies)
- [Named locations](https://learn.microsoft.com/entra/identity/conditional-access/concept-assignment-network)
- Microsoft's Zero Trust / CA reference materials at [microsoft/ConditionalAccessforZeroTrustResources](https://github.com/microsoft/ConditionalAccessforZeroTrustResources).

## License

MIT. See [LICENSE](./LICENSE).

## Security

See [SECURITY.md](./SECURITY.md). For vulnerability reports, prefer GitHub Security → Report a vulnerability over public issues.

The `reference/` spreadsheets are authoring companions, not read by the deployer. If you edit them, keep group display names and `mailNickname` strings aligned with [`baseline/groups/`](./baseline/groups/) (`CA_` prefix on display names, `ca-` on nicknames), then regenerate via `scripts/generate-baseline.py`.
