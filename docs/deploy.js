// Mirage CA Baseline Deployer - main orchestration.
// Sign-in -> consent -> create missing groups / named locations -> create Conditional
// Access policies in Off only when displayName is absent (never PATCH existing CA policies).
import { APP_CONFIG, GRAPH_SCOPES, ALLOWED_DEPLOY_STATES, resolveBaselineUrl, resolveBaselineUrlBases } from "./config.js";
import { graphGet, graphList, graphPost, graphPatch, findByDisplayName, GraphError } from "./graph.js";
import {
  KNOWN_APPS,
  buildGroupBody,
  buildNamedLocationBody,
  buildPolicyBody,
  evaluateFirstPartyAppSkip,
  evaluateSkip,
} from "./translate.js";

// MSAL is loaded as a UMD global from the CDN script tag in index.html.
const msalApp = new msal.PublicClientApplication({
  auth: {
    clientId: APP_CONFIG.clientId,
    authority: APP_CONFIG.authority,
    redirectUri: APP_CONFIG.redirectUri,
    postLogoutRedirectUri: APP_CONFIG.postLogoutRedirectUri,
  },
  cache: { cacheLocation: "sessionStorage" },
});

let msalInitialized = false;
async function ensureMsal() {
  if (msalInitialized) return;
  if (typeof msalApp.initialize === "function") await msalApp.initialize();
  msalInitialized = true;
}

// ---- DOM helpers ---------------------------------------------------------
const $ = (id) => document.getElementById(id);
const ui = {
  signInBtn: () => $("btn-signin"),
  deployBtn: () => $("btn-deploy"),
  signOutBtn: () => $("btn-signout"),
  dryRun: () => $("dry-run"),
  status: () => $("status"),
  account: () => $("account"),
  log: () => $("log"),
  summary: () => $("summary"),
  baselineUrl: () => $("baseline-url"),
};

function setStatus(text, kind = "info") {
  const el = ui.status();
  el.textContent = text;
  el.dataset.kind = kind;
}

function logLine(text, kind = "info") {
  const el = ui.log();
  const line = document.createElement("div");
  line.className = `log-line log-${kind}`;
  const ts = new Date().toLocaleTimeString();
  line.textContent = `[${ts}] ${text}`;
  el.appendChild(line);
  el.scrollTop = el.scrollHeight;
}

function setSignedIn(account) {
  ui.account().textContent = `${account.username} (tenant ${account.tenantId})`;
  ui.signInBtn().disabled = true;
  ui.signOutBtn().disabled = false;
  ui.deployBtn().disabled = false;
}

function setSignedOut() {
  ui.account().textContent = "Not signed in";
  ui.signInBtn().disabled = false;
  ui.signOutBtn().disabled = true;
  ui.deployBtn().disabled = true;
}

// ---- Friendly error mapping ---------------------------------------------
// MSAL surfaces err.errorCode (e.g. popup_window_error, user_cancelled,
// consent_required, interaction_required) and AAD codes inside err.message
// (e.g. AADSTS65004). Map the common cases to short, actionable copy and
// fall back to the raw message for everything else.
function describeAuthError(err) {
  if (!err) return null;
  const code = err.errorCode || "";
  const message = err.errorMessage || err.message || String(err);
  if (code === "popup_window_error" || /popup_window_error|popup.*block/i.test(message)) {
    return "Sign-in popup was blocked. Allow popups for this site, then try again.";
  }
  if (code === "user_cancelled" || /user_cancell?ed|cancelled by the user/i.test(message)) {
    return "Sign-in was cancelled. Click Sign in & consent when you're ready.";
  }
  if (code === "consent_required" || /AADSTS65004|consent.*required|consent.*declined/i.test(message)) {
    return "Consent was declined or is required. Sign in with an admin who can grant the requested Graph permissions, or ask a tenant admin to grant consent first.";
  }
  if (code === "interaction_required" || /AADSTS50076|AADSTS50079|interaction_required/i.test(message)) {
    return "Microsoft needs another sign-in step (for example MFA). Sign in again to continue.";
  }
  if (/Failed to fetch|NetworkError|net::|networkerror/i.test(message)) {
    return "Network error talking to Microsoft. Check your connection and try again.";
  }
  return null;
}

// 401/403 from Graph mean the run cannot continue (token expired or signed-in
// account lacks the required Conditional Access / directory roles). Treat
// them as fatal so the phase loops abort instead of repeating the same error
// for every group, named location, and policy.
function isFatalGraphError(err) {
  return err instanceof GraphError && (err.status === 401 || err.status === 403);
}

function describeFatalGraphError(err) {
  if (!(err instanceof GraphError)) return null;
  if (err.status === 401) {
    return "Microsoft Graph rejected the access token (401). Sign out and sign in again to refresh, then retry.";
  }
  if (err.status === 403) {
    return "Microsoft Graph denied the request (403). The signed-in account is missing required Conditional Access or directory roles.";
  }
  return null;
}

function logGraphFailure(context, err) {
  if (err instanceof GraphError) {
    let msg = `${context}: ${err.code} ${err.status} — ${err.message}`;
    if (err.body) {
      try {
        msg += ` | ${JSON.stringify(err.body)}`;
      } catch (_) {
        /* ignore */
      }
    }
    logLine(msg, "error");
  } else {
    logLine(`${context}: ${err && err.message ? err.message : String(err)}`, "error");
  }
}

// ---- Auth ----------------------------------------------------------------
async function signIn() {
  await ensureMsal();
  setStatus("Opening Microsoft sign-in...", "info");
  try {
    const result = await msalApp.loginPopup({
      scopes: GRAPH_SCOPES,
      prompt: "select_account",
    });
    msalApp.setActiveAccount(result.account);
    setSignedIn(result.account);
    setStatus("Signed in. Ready to deploy.", "ok");
    logLine(`Signed in as ${result.account.username} in tenant ${result.account.tenantId}`, "ok");
  } catch (err) {
    const friendly = describeAuthError(err);
    setStatus(friendly || "Sign-in failed.", "error");
    const codePrefix = err && err.errorCode ? `${err.errorCode} - ` : "";
    logLine(`Sign-in error: ${codePrefix}${err.message || err}`, "error");
  }
}

async function signOut() {
  await ensureMsal();
  const account = msalApp.getActiveAccount();
  if (!account) {
    setSignedOut();
    return;
  }
  await msalApp.logoutPopup({ account });
  setSignedOut();
  setStatus("Signed out.", "info");
}

async function getToken() {
  await ensureMsal();
  const account = msalApp.getActiveAccount() || msalApp.getAllAccounts()[0];
  if (!account) throw new Error("No active account. Sign in first.");
  msalApp.setActiveAccount(account);
  try {
    const r = await msalApp.acquireTokenSilent({ scopes: GRAPH_SCOPES, account });
    return r.accessToken;
  } catch (_) {
    const r = await msalApp.acquireTokenPopup({ scopes: GRAPH_SCOPES, account });
    return r.accessToken;
  }
}

// ---- Manifest loading ----------------------------------------------------
let resolvedBaselineRoot = null;

async function loadJson(path) {
  const candidates = resolvedBaselineRoot ? [resolvedBaselineRoot] : resolveBaselineUrlBases();
  let lastErr = null;
  for (const base of candidates) {
    const root = base.replace(/\/+$/, "");
    const url = `${root}/${path.replace(/^\/+/, "")}`;
    const resp = await fetch(url, { cache: "no-cache" });
    if (resp.ok) {
      resolvedBaselineRoot = root;
      return resp.json();
    }
    lastErr = new Error(`Failed to fetch ${url}: ${resp.status}`);
  }
  throw lastErr || new Error("No baseline URL candidates");
}

// ---- Resolution: groups, named locations, service principals -------------
async function ensureGroup(token, intent, dryRun) {
  const existing = await findByDisplayName(token, "/groups", intent.displayName, "id,displayName");
  if (existing) {
    logLine(`group [${intent.displayName}] already exists -> ${existing.id}`, "info");
    return existing.id;
  }
  if (dryRun) {
    logLine(`group [${intent.displayName}] WOULD BE CREATED`, "warn");
    return "dryrun-" + intent.displayName;
  }
  const created = await graphPost(token, "/groups", buildGroupBody(intent));
  logLine(`group [${intent.displayName}] CREATED -> ${created.id}`, "ok");
  return created.id;
}

async function ensureNamedLocation(token, intent, dryRun) {
  const items = await graphList(token, "/identity/conditionalAccess/namedLocations");
  const existing = items.find((n) => n.displayName === intent.displayName);
  if (existing) {
    logLine(`namedLocation [${intent.displayName}] already exists -> ${existing.id}`, "info");
    return existing.id;
  }
  if (dryRun) {
    logLine(`namedLocation [${intent.displayName}] WOULD BE CREATED (placeholder ranges)`, "warn");
    return "dryrun-" + intent.displayName;
  }
  const created = await graphPost(token, "/identity/conditionalAccess/namedLocations", buildNamedLocationBody(intent));
  logLine(`namedLocation [${intent.displayName}] CREATED -> ${created.id}`, "ok");
  return created.id;
}

async function indexServicePrincipals(token, displayNames) {
  const map = new Map();
  for (const name of displayNames) {
    const sp = await findByDisplayName(token, "/servicePrincipals", name, "id,displayName,appId");
    if (sp) {
      map.set(name, sp.appId);
      logLine(`servicePrincipal [${name}] resolved -> ${sp.appId}`, "info");
    } else {
      logLine(`servicePrincipal [${name}] NOT FOUND in this tenant - dependent policies will be skipped`, "warn");
    }
  }
  return map;
}

function collectServicePrincipalNames(policyIntents) {
  const names = new Set();
  for (const p of policyIntents) {
    if (p.applications?.lookup === "servicePrincipal" && Array.isArray(p.applications.include)) {
      for (const n of p.applications.include) names.add(n);
    }
  }
  return [...names];
}

function collectReferencedFirstPartyAppIds(policyIntents) {
  const ids = new Set();
  const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  const addToken = (token) => {
    if (!(token in KNOWN_APPS)) return;
    const appId = KNOWN_APPS[token];
    if (typeof appId === "string" && uuid.test(appId)) ids.add(appId.toLowerCase());
  };
  for (const p of policyIntents) {
    const apps = p.applications;
    if (!apps) continue;
    if (typeof apps.include === "string") addToken(apps.include);
    if (Array.isArray(apps.include)) for (const t of apps.include) addToken(t);
  }
  return ids;
}

async function indexFirstPartyAppIds(token, policyIntents) {
  const wanted = collectReferencedFirstPartyAppIds(policyIntents);
  const present = new Set();
  for (const appId of wanted) {
    try {
      const r = await graphGet(token, "/servicePrincipals", {
        $filter: `appId eq '${appId}'`,
        $select: "id",
        $top: "1",
      });
      if (Array.isArray(r.value) && r.value.length) present.add(appId);
    } catch (e) {
      logLine(`Could not verify first-party app ${appId}: ${e.message || e}`, "warn");
    }
  }
  for (const appId of wanted) {
    if (!present.has(appId)) {
      logLine(
        `First-party app appId=${appId} has no service principal in this tenant — policies that target only named Microsoft apps will be skipped.`,
        "warn",
      );
    }
  }
  return present;
}

async function ensurePolicy(token, intent, ctx, dryRun) {
  const skip = evaluateSkip(intent, ctx);
  if (skip) {
    logLine(`policy [${intent.displayName}] SKIPPED (missing dependency: ${skip})`, "warn");
    return { id: intent.id, status: "skipped", reason: skip };
  }

  const skipFp = evaluateFirstPartyAppSkip(intent, ctx);
  if (skipFp) {
    logLine(`policy [${intent.displayName}] SKIPPED (missing dependency: ${skipFp})`, "warn");
    return { id: intent.id, status: "skipped", reason: skipFp };
  }

  const existing = await findByDisplayName(
    token,
    "/identity/conditionalAccess/policies",
    intent.displayName,
    "id,displayName,state",
  );

  if (existing) {
    logLine(
      `policy [${intent.displayName}] already exists (${dryRun ? "dry run — " : ""}id=${existing.id}, tenant state=${existing.state}) — not modifying to avoid overwriting live settings.`,
      dryRun ? "warn" : "info",
    );
    return {
      id: intent.id,
      status: dryRun ? "would-remain" : "unchanged",
      graphId: existing.id,
      tenantState: existing.state,
    };
  }

  const body = buildPolicyBody(intent, ctx);

  // Hard guard: never deploy in any state but those allowed by config.
  if (!ALLOWED_DEPLOY_STATES.includes(body.state)) {
    throw new Error(`Refusing to deploy policy [${intent.displayName}] with state=${body.state}`);
  }

  if (dryRun) {
    logLine(`policy [${intent.displayName}] WOULD BE CREATED (state=disabled)`, "warn");
    return { id: intent.id, status: "would-create" };
  }

  try {
    const created = await graphPost(token, "/identity/conditionalAccess/policies", body);
    logLine(`policy [${intent.displayName}] CREATED (state=disabled, id=${created.id})`, "ok");
    return { id: intent.id, status: "created" };
  } catch (err) {
    if (isFatalGraphError(err)) throw err;
    logGraphFailure(`policy [${intent.displayName}] POST`, err);
    return { id: intent.id, status: "error", error: err.message };
  }
}

// ---- Main orchestration --------------------------------------------------
async function deploy() {
  ui.deployBtn().disabled = true;
  ui.signOutBtn().disabled = true;
  ui.log().textContent = "";
  ui.summary().textContent = "";

  const dryRun = ui.dryRun().checked;
  if (dryRun) logLine("DRY RUN: nothing will be written to the tenant.", "warn");

  resolvedBaselineRoot = null;

  let token;
  try {
    token = await getToken();
  } catch (err) {
    const friendly = describeAuthError(err);
    setStatus(friendly || "Could not acquire access token.", "error");
    const codePrefix = err && err.errorCode ? `${err.errorCode} - ` : "";
    logLine(`Token error: ${codePrefix}${err.message || err}`, "error");
    ui.deployBtn().disabled = false;
    ui.signOutBtn().disabled = false;
    return;
  }

  let manifest;
  try {
    setStatus("Fetching baseline manifest...", "info");
    manifest = await loadJson("manifest.json");
    logLine(`Loaded ${manifest.baseline} (manifest schema ${manifest.$schemaVersion}) from ${resolvedBaselineRoot}`, "info");
  } catch (err) {
    const message = err && err.message ? err.message : String(err);
    let friendly = "Could not load baseline manifest.";
    // loadJson throws "Failed to fetch <url>: 404" — check status before generic "Failed to fetch".
    if (/: 404\b|\b404\b/.test(message)) {
      friendly =
        "Baseline manifest returned 404 from every URL we tried. On GitHub Pages, the deploy workflow must copy baseline/ into the site (Actions → Deploy GitHub Pages). " +
        "If you use branch-based Pages without that copy, add baseline/ to the published tree or set window.MIRAGE_BASELINE_URL in index.html. " +
        "Raw GitHub fallback also needs baseline/ on the branch (default main): run python scripts/generate-baseline.py, commit, and push.";
    } else if (/Failed to fetch|NetworkError|net::|networkerror/i.test(message)) {
      friendly =
        "Could not reach the baseline files (network or blocked request). Check connectivity, corporate proxy, and that the raw GitHub URL is reachable.";
    }
    setStatus(friendly, "error");
    logLine(message, "error");
    ui.deployBtn().disabled = false;
    ui.signOutBtn().disabled = false;
    return;
  }

  const ctx = {
    groupIdsByDisplayName: new Map(),
    namedLocationIdsByDisplayName: new Map(),
    servicePrincipalIdsByDisplayName: new Map(),
    termsOfUseIdsByDisplayName: new Map(),
    missing: [],
  };

  // Phase 1 - Groups.
  setStatus(`Phase 1/3: ensuring ${manifest.groups.length} groups...`, "info");
  for (const file of manifest.groups) {
    try {
      const intent = await loadJson(`groups/${file}`);
      const id = await ensureGroup(token, intent, dryRun);
      ctx.groupIdsByDisplayName.set(intent.displayName, id);
    } catch (err) {
      if (isFatalGraphError(err)) throw err;
      logGraphFailure(`group ${file}`, err);
    }
  }

  // Phase 2 - Named locations.
  setStatus(`Phase 2/3: ensuring ${manifest.namedLocations.length} named locations...`, "info");
  for (const file of manifest.namedLocations) {
    try {
      const intent = await loadJson(`namedLocations/${file}`);
      const id = await ensureNamedLocation(token, intent, dryRun);
      ctx.namedLocationIdsByDisplayName.set(intent.displayName, id);
    } catch (err) {
      if (isFatalGraphError(err)) throw err;
      logGraphFailure(`namedLocation ${file}`, err);
    }
  }

  // Pre-resolve service principals so policies can be skipped cleanly.
  setStatus("Resolving 3rd-party service principals...", "info");
  const policyIntents = [];
  for (const file of manifest.policies) {
    try {
      policyIntents.push(await loadJson(`policies/${file}`));
    } catch (err) {
      logLine(`policy ${file} could not be loaded: ${err.message}`, "error");
    }
  }
  const spNames = collectServicePrincipalNames(policyIntents);
  if (spNames.length) ctx.servicePrincipalIdsByDisplayName = await indexServicePrincipals(token, spNames);

  setStatus("Verifying Microsoft first-party apps referenced by policies...", "info");
  ctx.appIdInTenant = await indexFirstPartyAppIds(token, policyIntents);

  // Phase 3 - Policies.
  setStatus(
    `Phase 3/3: Conditional Access policies — create missing as disabled; skip existing display names (${policyIntents.length} in manifest)...`,
    "info",
  );
  const results = [];
  for (const intent of policyIntents) {
    const r = await ensurePolicy(token, intent, ctx, dryRun);
    results.push(r);
  }

  const counts = {
    created: 0,
    unchanged: 0,
    skipped: 0,
    error: 0,
    "would-create": 0,
    "would-remain": 0,
  };
  for (const r of results) counts[r.status] = (counts[r.status] || 0) + 1;

  const summary = [
    `created: ${counts.created}`,
    `unchanged: ${counts.unchanged}`,
    `would-create: ${counts["would-create"]}`,
    `would-remain: ${counts["would-remain"]}`,
    `skipped: ${counts.skipped}`,
    `error: ${counts.error}`,
  ].join(" | ");
  ui.summary().textContent = summary;

  setStatus(
    dryRun
      ? "Dry run complete."
      : "Deployment complete. New policies were created disabled; existing Conditional Access policies (same display name) were not changed.",
    counts.error ? "warn" : "ok",
  );
  logLine(summary, counts.error ? "warn" : "ok");
  if (ctx.missing.length) {
    logLine(`Unresolved references: ${[...new Set(ctx.missing)].join(", ")}`, "warn");
  }

  ui.deployBtn().disabled = false;
  ui.signOutBtn().disabled = false;
}

// ---- Wire up -------------------------------------------------------------
function wire() {
  ui.baselineUrl().textContent = resolveBaselineUrl();
  ui.signInBtn().addEventListener("click", signIn);
  ui.signOutBtn().addEventListener("click", signOut);
  ui.deployBtn().addEventListener("click", () => {
    deploy().catch((err) => {
      const friendly = describeAuthError(err) || describeFatalGraphError(err);
      setStatus(friendly || "Unhandled error during deploy.", "error");
      const codePrefix = err && err.errorCode ? `${err.errorCode} - ` : "";
      logLine(err.stack || `${codePrefix}${err.message || err}`, "error");
      ui.deployBtn().disabled = false;
      ui.signOutBtn().disabled = false;
    });
  });

  ensureMsal()
    .then(() => {
      const account = msalApp.getActiveAccount() || msalApp.getAllAccounts()[0];
      if (account) {
        msalApp.setActiveAccount(account);
        setSignedIn(account);
        setStatus("Existing session restored. Ready to deploy.", "ok");
      } else {
        setSignedOut();
        setStatus("Sign in to begin.", "info");
      }
    })
    .catch((err) => {
      setStatus(
        "Could not initialize Microsoft sign-in. Reload the page; if it persists, the MSAL CDN may be blocked by your network.",
        "error",
      );
      logLine(`MSAL init failed: ${err.message || err}`, "error");
    });
}

document.addEventListener("DOMContentLoaded", wire);
