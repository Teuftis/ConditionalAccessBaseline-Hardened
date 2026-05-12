// Translates the intent JSON files under /baseline/policies/*.json
// into Microsoft Graph Conditional Access policy bodies.
//
// Why intent-based rather than raw Graph bodies?
//   * Tenant-specific identifiers (group IDs, named-location IDs, service
//     principal IDs) are resolved at deploy time. The repo stores names.
//   * The translation sets a safe default CA state (report-mostly; Off for a pinned list;
//     see POLICY_IDS_DEPLOY_DISABLED_BY_DEFAULT and resolvePolicyDeployState)
//     in one place rather than duplicating state in every policy file.
//   * For some session-only CAE policies, guest/external exclusions in intent are
//     omitted in the Graph payload (see resolveUsers) to satisfy API schema.
import { ALLOWED_DEPLOY_STATES } from "./config.js";

// Well-known first-party app identifiers used by name in the intent files.
export const KNOWN_APPS = {
  azureManagement: "797f4846-ba00-4fd7-ba43-dac1f8f63013",
  intuneEnrollment: "d4ebce55-015a-49b5-a083-c84d1797ae8c",
  exchangeOnline: "00000002-0000-0ff1-ce00-000000000000",
  sharePointOnline: "00000003-0000-0ff1-ce00-000000000000",
  teams: "cc15fd57-2c6c-4117-a88c-83b1d56b4bbe",
  microsoftAdminPortals: "MicrosoftAdminPortals",
  office365: "Office365",
};

// Well-known directory role template IDs treated as "privileged" by the
// Mirage baseline. Sourced from Microsoft Learn / built-in roles list.
const PRIVILEGED_ROLE_TEMPLATE_IDS = [
  "62e90394-69f5-4237-9190-012177145e10", // Global Administrator
  "e8611ab8-c189-46e8-94e1-60213ab1f814", // Privileged Role Administrator
  "b1be1c3e-b65d-4f19-8427-f6fa0d97feb9", // Conditional Access Administrator
  "194ae4cb-b126-40b2-bd5b-6091b380977d", // Security Administrator
  "9b895d92-2cd3-44c7-9d02-a6ac2d5ea5c3", // Application Administrator
  "158c047a-c907-4556-b7ef-446551a6b5f7", // Cloud Application Administrator
  "c4e39bd9-1100-46d3-8c65-fb160da0071f", // Authentication Administrator
  "fe930be7-5e62-47db-91af-98c3a49a38b1", // User Administrator
  "729827e3-9c14-49f7-bb1b-9608f156bbb8", // Helpdesk Administrator
  "29232cdf-9323-42fd-ade2-1d097af3e4de", // Exchange Administrator
  "f28a1f50-f6e7-4571-818b-6a12f2af6b6c", // SharePoint Administrator
  "69091246-20e8-4a56-aa4d-066075b2a7a8", // Teams Administrator
  "3a2c62db-5318-420d-8d74-23affee5d9d5", // Intune Administrator
  "17315797-102d-40b4-93e0-432062caca18", // Compliance Administrator
  "7be44c8a-adaf-4e2a-84d6-ab2649e08a13", // Privileged Authentication Administrator
];

const AUTHENTICATION_STRENGTH_BUILTINS = {
  // Built-in authentication strength policy IDs are stable per tenant.
  phishingResistantMfa: "00000000-0000-0000-0000-000000000004",
  passwordlessMfa: "00000000-0000-0000-0000-000000000003",
  mfa: "00000000-0000-0000-0000-000000000002",
};

const GUEST_OR_EXTERNAL_KINDS = [
  "internalGuest",
  "b2bCollaborationGuest",
  "b2bCollaborationMember",
  "b2bDirectConnectUser",
  "otherExternalUser",
  "serviceProvider",
];

function resolveApps(intent, ctx) {
  const result = {
    includeApplications: [],
    excludeApplications: [],
  };

  const apps = intent.applications || {};

  if (apps.userActions && apps.userActions.length) {
    result.includeUserActions = apps.userActions.slice();
    return result;
  }
  // Omit includeUserActions when unused - Graph rejects empty collections on CA payloads.

  if (apps.include === "all") {
    result.includeApplications = ["All"];
  } else if (typeof apps.include === "string") {
    result.includeApplications = [resolveAppToken(apps.include, apps.lookup, ctx)];
  } else if (Array.isArray(apps.include)) {
    result.includeApplications = apps.include
      .map((token) => resolveAppToken(token, apps.lookup, ctx))
      .filter((v) => v !== null);
  }

  if (apps.exclude) {
    if (apps.exclude === "office365") {
      result.excludeApplications = [KNOWN_APPS.office365];
    } else if (Array.isArray(apps.exclude)) {
      result.excludeApplications = apps.exclude
        .map((token) => resolveAppToken(token, apps.lookup, ctx))
        .filter((v) => v !== null);
    }
  }

  return result;
}

function resolveAppToken(token, lookup, ctx) {
  if (token in KNOWN_APPS) return KNOWN_APPS[token];
  if (lookup === "servicePrincipal") {
    const sp = ctx.servicePrincipalIdsByDisplayName.get(token);
    if (!sp) {
      ctx.missing.push(`servicePrincipal:${token}`);
      return null;
    }
    return sp;
  }
  return token; // assume already-GUID
}

function resolveUsers(intent, ctx) {
  const include = intent.include || {};
  const exclude = intent.exclude || {};

  // Only include keys Graph should see; empty arrays on user/role/group collections
  // often yield 400 Invalid Request on conditional access APIs.
  const users = {};

  if (include.users === "all") users.includeUsers = ["All"];
  else if (include.users === "none") users.includeUsers = ["None"];
  else if (include.users === "guestsAndExternals") {
    users.includeGuestsOrExternalUsers = {
      guestOrExternalUserTypes: GUEST_OR_EXTERNAL_KINDS.join(","),
      externalTenants: { membershipKind: "all" },
    };
  } else if (Array.isArray(include.groups)) {
    users.includeGroups = include.groups.map((g) => resolveGroup(g, ctx)).filter(Boolean);
  } else if (include.roles === "privilegedAdmins") {
    users.includeRoles = PRIVILEGED_ROLE_TEMPLATE_IDS.slice();
  } else if (include.agentIds === "all") {
    users.includeUsers = ["None"];
  }

  // Workload / agent-scope policies scope identities via conditions.clientApplications, not users.
  // User-level excludeGroups with includeUsers: None violates the CA schema (1007).
  const workloadAgentAllAgents = include.agentIds === "all";
  if (Array.isArray(exclude.groups) && !workloadAgentAllAgents) {
    users.excludeGroups = exclude.groups.map((g) => resolveGroup(g, ctx)).filter(Boolean);
  }
  // Guest/external exclusion works on most workforce policies via excludeGuestsOrExternalUsers.
  // Graph rejects session-only Continuous Access Evaluation (continuousAccessEvaluation intent, no grant)
  // combined with excludeGuestsOrExternalUsers and includeUsers All (1007). Baseline CA111 therefore
  // does not declare guestsAndExternals in exclude.
  const caeOnlyNoGrantGuestExcludeFailsGraph =
    Boolean(intent.session?.continuousAccessEvaluation) && !intent.grant;
  if (
    exclude.guestsAndExternals &&
    !workloadAgentAllAgents &&
    !caeOnlyNoGrantGuestExcludeFailsGraph
  ) {
    users.excludeGuestsOrExternalUsers = {
      guestOrExternalUserTypes: GUEST_OR_EXTERNAL_KINDS.join(","),
      externalTenants: { membershipKind: "all" },
    };
  }

  return users;
}

function resolveGroup(name, ctx) {
  const id = ctx.groupIdsByDisplayName.get(name);
  if (!id) {
    ctx.missing.push(`group:${name}`);
    return null;
  }
  return id;
}

function resolveLocations(locations, ctx) {
  if (!locations) return null;
  const out = { includeLocations: [], excludeLocations: [] };
  for (const item of locations.include || []) out.includeLocations.push(resolveLocationToken(item, ctx));
  for (const item of locations.exclude || []) out.excludeLocations.push(resolveLocationToken(item, ctx));
  out.includeLocations = out.includeLocations.filter(Boolean);
  out.excludeLocations = out.excludeLocations.filter(Boolean);
  if (out.includeLocations.length === 0 && out.excludeLocations.length === 0) return null;
  return out;
}

function resolveLocationToken(token, ctx) {
  if (token === "All" || token === "AllTrusted") return token;
  const id = ctx.namedLocationIdsByDisplayName.get(token);
  if (!id) {
    ctx.missing.push(`namedLocation:${token}`);
    return null;
  }
  return id;
}

function resolvePlatforms(platforms) {
  if (!platforms) return null;
  return {
    includePlatforms: platforms.include || [],
    excludePlatforms: platforms.exclude || [],
  };
}

function resolveDeviceFilter(filter) {
  if (!filter) return null;
  return { mode: filter.mode, rule: filter.rule };
}

function resolveAuthenticationFlows(flows) {
  if (!flows || !flows.length) return null;
  return { transferMethods: flows.join(",") };
}

function resolveGrant(intent, ctx) {
  const grant = intent.grant;
  if (!grant) return null;
  const out = {
    operator: grant.operator || "OR",
  };
  const bic = grant.builtInControls;
  if (Array.isArray(bic) && bic.length) out.builtInControls = bic;
  if (grant.authenticationStrength) {
    const id = AUTHENTICATION_STRENGTH_BUILTINS[grant.authenticationStrength];
    if (id) out.authenticationStrength = { id };
    else ctx.missing.push(`authenticationStrength:${grant.authenticationStrength}`);
  }
  if (Array.isArray(grant.termsOfUse)) {
    const touIds = [];
    for (const tou of grant.termsOfUse) {
      const id = ctx.termsOfUseIdsByDisplayName.get(tou);
      if (id) touIds.push(id);
      else ctx.missing.push(`termsOfUse:${tou}`);
    }
    if (touIds.length) out.termsOfUse = touIds;
  }
  return out;
}

function resolveSession(intent) {
  const s = intent.session;
  if (!s) return null;
  const out = {};
  if (s.signInFrequency) {
    // Omit authenticationType for time-based frequency; Graph documents it as
    // optional and some validators reject the combination incorrectly.
    out.signInFrequency = {
      isEnabled: true,
      type: s.signInFrequency.type || "hours",
      value: s.signInFrequency.value,
      frequencyInterval: "timeBased",
    };
  }
  if (s.persistentBrowser) {
    out.persistentBrowser = { isEnabled: true, mode: s.persistentBrowser };
  }
  if (s.continuousAccessEvaluation) {
    const raw = s.continuousAccessEvaluation;
    // Standard workforce CAE (CA111): Entra session control "Disabled" (not strict location)
    // maps to Graph `disabled`. Never send `strictEnforcement` - API returns 1138 (rolled back).
    if (raw === "standard" || raw === "strictEnforcement") {
      out.continuousAccessEvaluation = { mode: "disabled" };
    } else {
      // Intent uses shorthand; Graph only accepts continuousAccessEvaluationMode.
      // strictLocation is evolvable - send Prefer: include-unknown-enum-members (graph.js).
      const CAE_TO_GRAPH_MODE = {
        strict: "strictLocation",
        strictLocation: "strictLocation",
        disabled: "disabled",
      };
      const mode = CAE_TO_GRAPH_MODE[raw] ?? raw;
      out.continuousAccessEvaluation = { mode };
    }
  }
  if (s.applicationEnforcedRestrictions) {
    out.applicationEnforcedRestrictions = { isEnabled: true };
  }
  if (s.tokenProtectionEnforced) {
    out.secureSignInSession = { isEnabled: true };
  }
  return Object.keys(out).length ? out : null;
}

/**
 * Skip policies that target native first-party apps (resolved from KNOWN_APPS)
 * when no service principal exists for that appId - common without Intune/MDM.
 */
export function evaluateFirstPartyAppSkip(intent, ctx) {
  const present = ctx.appIdInTenant;
  if (!present || !(present instanceof Set)) return null;
  const apps = intent.applications;
  if (!apps) return null;

  const tokens = [];
  if (typeof apps.include === "string" && apps.include in KNOWN_APPS) tokens.push(apps.include);
  if (Array.isArray(apps.include)) {
    for (const t of apps.include) {
      if (t in KNOWN_APPS) tokens.push(t);
    }
  }
  for (const token of tokens) {
    const appId = KNOWN_APPS[token];
    if (typeof appId !== "string") continue;
    if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(appId)) continue;
    if (!present.has(appId.toLowerCase())) {
      return `firstPartyApp:${token}`;
    }
  }
  return null;
}

// Apply skipIfMissing rules. Returns a string explaining what is missing,
// or null if the policy can be deployed.
export function evaluateSkip(intent, ctx) {
  if (!Array.isArray(intent.skipIfMissing)) return null;
  for (const dep of intent.skipIfMissing) {
    if (dep.startsWith("servicePrincipal:") && !ctx.servicePrincipalIdsByDisplayName.has(dep.slice("servicePrincipal:".length))) {
      return dep;
    }
    if (dep.startsWith("termsOfUse:") && !ctx.termsOfUseIdsByDisplayName.has(dep.slice("termsOfUse:".length))) {
      return dep;
    }
    if (dep.startsWith("namedLocation:") && !ctx.namedLocationIdsByDisplayName.has(dep.slice("namedLocation:".length))) {
      return dep;
    }
  }
  return null;
}

// Conditional Access payloads often reject explicit empty string collections ([]).
// Recursively omit empty arrays; drop nested objects that become {} after stripping.
function stripEmptyGraphCollections(value) {
  if (Array.isArray(value)) {
    return value.map((item) => stripEmptyGraphCollections(item));
  }
  if (value && typeof value === "object") {
    const out = {};
    for (const [k, v] of Object.entries(value)) {
      if (Array.isArray(v)) {
        if (v.length === 0) continue;
        out[k] = v.map((item) => stripEmptyGraphCollections(item));
      } else if (v != null && typeof v === "object") {
        const nested = stripEmptyGraphCollections(v);
        if (nested != null && typeof nested === "object" && !Array.isArray(nested) && Object.keys(nested).length === 0) {
          continue;
        }
        out[k] = nested;
      } else if (v !== undefined) {
        out[k] = v;
      }
    }
    return out;
  }
  return value;
}

// Workload identities (Agent-ID scoped) CA policies validate against a fuller
// conditionalAccessConditionSet shape on create than intent + strip-empty leaves.
// See Graph beta POST example 7: conditionalaccessroot-post-policies (block high-risk agents).
function finalizeWorkloadAgentPolicyBody(body, intent) {
  if ((intent.include || {}).agentIds !== "all") return body;

  const prev = body.conditions || {};
  const apps = prev.applications || {};
  const levels = intent.conditions?.agentIdRiskLevels;

  const conditions = {
    ...prev,
    agentIdRiskLevels:
      Array.isArray(levels) && levels.length === 1 ? levels[0] : prev.agentIdRiskLevels,
    applications: {
      includeApplications: apps.includeApplications || ["All"],
      excludeApplications: apps.excludeApplications || [],
      includeUserActions: apps.includeUserActions || [],
      includeAuthenticationContextClassReferences: apps.includeAuthenticationContextClassReferences || [],
      applicationFilter: apps.applicationFilter ?? null,
    },
    users: {
      includeUsers: ["None"],
      excludeUsers: [],
      includeGroups: [],
      excludeGroups: [],
      includeRoles: [],
      excludeRoles: [],
      includeGuestsOrExternalUsers: null,
      excludeGuestsOrExternalUsers: null,
    },
    clientApplications: {
      includeServicePrincipals: [],
      includeAgentIdServicePrincipals: ["All"],
      excludeServicePrincipals: [],
      excludeAgentIdServicePrincipals: [],
      agentIdServicePrincipalFilter: null,
    },
  };

  return { ...body, conditions };
}

// Policies that land **Off** on deploy unless `deploymentState` / `deployState` on intent
// requests `enabledForReportingButNotEnforced` (recommended for phased adoption).
/** @type {ReadonlySet<string>} */
export const POLICY_IDS_DEPLOY_DISABLED_BY_DEFAULT = new Set([
  "CA111", // Session CAE non-strict
  "CA202", // APP-only mobile
  "CA204", // MDM-required optional path
  "CA302",
  "CA303",
  "CA603",
  "CA606",
  "CAA01", // Agent / workload persona
]);

function resolvePolicyDeployState(intent) {
  // Optional per-policy intent field `deploymentState` / `deployState` selects Report-only vs Off
  // only on first POST - existing tenant policies are never modified (deploy skips same display name).
  // Default is report-only except POLICY_IDS_DEPLOY_DISABLED_BY_DEFAULT. User-actions (e.g. CA112)
  // follow the same path. If Graph rejects report-only at POST time, add `deploymentState: "disabled"`
  // to that intent JSON for your fork.
  const raw = intent.deploymentState ?? intent.deployState;
  if (typeof raw === "string" && ALLOWED_DEPLOY_STATES.includes(raw)) {
    return raw;
  }
  const pid = intent.id;
  if (typeof pid === "string" && POLICY_IDS_DEPLOY_DISABLED_BY_DEFAULT.has(pid)) {
    return "disabled";
  }
  return ALLOWED_DEPLOY_STATES[0];
}

// Build the final Graph body for a CA policy from an intent file.
export function buildPolicyBody(intent, ctx) {
  const body = {
    displayName: intent.displayName,
    state: resolvePolicyDeployState(intent),
    conditions: {
      userRiskLevels: intent.conditions?.userRiskLevels || [],
      signInRiskLevels: intent.conditions?.signInRiskLevels || [],
      clientAppTypes: intent.conditions?.clientAppTypes || ["all"],
      applications: resolveApps(intent, ctx),
      users: resolveUsers(intent, ctx),
    },
  };

  const platforms = resolvePlatforms(intent.conditions?.platforms);
  if (platforms) body.conditions.platforms = platforms;

  const locations = resolveLocations(intent.conditions?.locations, ctx);
  if (locations) body.conditions.locations = locations;

  const deviceFilter = resolveDeviceFilter(intent.conditions?.deviceFilter);
  if (deviceFilter) body.conditions.devices = { deviceFilter };

  const authFlows = resolveAuthenticationFlows(intent.conditions?.authenticationFlows);
  if (authFlows) body.conditions.authenticationFlows = authFlows;

  if (Array.isArray(intent.conditions?.agentIdRiskLevels) && intent.conditions.agentIdRiskLevels.length) {
    body.conditions.agentIdRiskLevels = intent.conditions.agentIdRiskLevels;
  }

  const grant = resolveGrant(intent, ctx);
  if (grant) body.grantControls = grant;

  const session = resolveSession(intent);
  if (session) body.sessionControls = session;

  let out = stripEmptyGraphCollections(body);
  if ((intent.include || {}).agentIds === "all") {
    out = finalizeWorkloadAgentPolicyBody(out, intent);
  }
  return out;
}

// Build the Graph body for a group create call from a group intent file.
export function buildGroupBody(intent) {
  const body = {
    displayName: intent.displayName,
    mailEnabled: false,
    mailNickname: intent.mailNickname,
    securityEnabled: true,
    groupTypes: [],
  };
  if (intent.description != null && String(intent.description).length > 0) {
    body.description = intent.description;
  }
  return body;
}

// Build the Graph body for a named location create call.
export function buildNamedLocationBody(intent) {
  if (intent.type === "country") {
    return {
      "@odata.type": "#microsoft.graph.countryNamedLocation",
      displayName: intent.displayName,
      countriesAndRegions: intent.countriesAndRegions || [],
      includeUnknownCountriesAndRegions: !!intent.includeUnknownCountriesAndRegions,
      countryLookupMethod: intent.countryLookupMethod || "clientIpAddress",
    };
  }
  if (intent.type === "ip") {
    return {
      "@odata.type": "#microsoft.graph.ipNamedLocation",
      displayName: intent.displayName,
      isTrusted: !!intent.isTrusted,
      ipRanges: (intent.ipRanges || []).map((r) => ({
        "@odata.type": r.includes(":") ? "#microsoft.graph.iPv6CidrRange" : "#microsoft.graph.iPv4CidrRange",
        cidrAddress: r,
      })),
    };
  }
  throw new Error(`Unsupported named location type: ${intent.type}`);
}
