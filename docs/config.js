// Mirage CA Baseline Deployer - SPA configuration
// Multi-tenant Entra ID app (SPA, public client, no secret).
export const APP_CONFIG = Object.freeze({
  clientId: "0a54b934-a282-49c8-8e95-eaf7719c9ab2",
  authority: "https://login.microsoftonline.com/organizations",
  // PKCE redirect: must match the SPA platform redirect URI on the app registration.
  // For GitHub Pages this resolves to https://<owner>.github.io/<repo>/
  redirectUri: window.location.origin + window.location.pathname,
  postLogoutRedirectUri: window.location.origin + window.location.pathname,
});

// Delegated Microsoft Graph scopes requested at consent time.
// Each customer admin consents once per tenant on first use.
export const GRAPH_SCOPES = Object.freeze([
  "User.Read",
  "Directory.Read.All",
  "Application.Read.All",
  "Group.ReadWrite.All",
  "Policy.Read.All",
  "Policy.ReadWrite.ConditionalAccess",
]);

// Microsoft Graph endpoint. The Conditional Access surface uses /beta for
// newer features (token protection, agent risk, CAE strict) that have not
// yet been promoted to /v1.0 at the time of writing.
export const GRAPH_BASE = "https://graph.microsoft.com/beta";

// Baseline JSON URLs to try, in order. Override with window.MIRAGE_BASELINE_URL for a single explicit base.
// On *.github.io: first same-origin /baseline/ (copied into docs/ by Deploy GitHub Pages workflow), then Raw GitHub.
function stripTrailingSlashes(s) {
  return s.replace(/\/+$/, "");
}

function currentSpaDirectoryUrl() {
  const u = new URL(window.location.href);
  u.hash = "";
  u.search = "";
  let pathname = u.pathname;
  const lastSeg = pathname.split("/").pop() || "";
  if (/\.html?$/i.test(lastSeg)) {
    pathname = pathname.slice(0, pathname.length - lastSeg.length);
  }
  if (!pathname.endsWith("/")) pathname += "/";
  u.pathname = pathname;
  return u.href;
}

export function resolveBaselineUrlBases() {
  if (typeof window.MIRAGE_BASELINE_URL === "string" && window.MIRAGE_BASELINE_URL.length > 0) {
    return [stripTrailingSlashes(window.MIRAGE_BASELINE_URL)];
  }

  const host = window.location.host;
  const segments = window.location.pathname.split("/").filter(Boolean);

  if (host.endsWith(".github.io") && segments.length >= 1) {
    const owner = host.split(".")[0];
    const repo = segments[0];
    const ref = window.MIRAGE_BASELINE_REF || "main";
    const sameOrigin = stripTrailingSlashes(new URL("baseline", currentSpaDirectoryUrl()).href);
    const rawGithub = stripTrailingSlashes(`https://raw.githubusercontent.com/${owner}/${repo}/${ref}/baseline`);
    return [sameOrigin, rawGithub];
  }

  // Local dev: serve repo root (e.g. python -m http.server) and open /docs/.
  return [stripTrailingSlashes("../baseline")];
}

/** Human-readable candidates for the UI (baseline source label). */
export function resolveBaselineUrl() {
  return resolveBaselineUrlBases().join(" · ");
}

// Hard cap on what state the SPA may set on Conditional Access policies.
// Anything other than "disabled" is rejected client-side. The README and
// UI both make this contract explicit so admins can rely on it.
export const ALLOWED_DEPLOY_STATES = Object.freeze(["disabled"]);
