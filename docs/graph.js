// Thin Microsoft Graph helpers used by the deploy SPA.
// Keeps pagination, error shaping, and rate-limit handling in one place.
import { GRAPH_BASE } from "./config.js";

export class GraphError extends Error {
  constructor(message, { status, code, requestId, body } = {}) {
    super(message);
    this.name = "GraphError";
    this.status = status;
    this.code = code;
    this.requestId = requestId;
    this.body = body;
  }
}

async function readError(resp) {
  let payload;
  try {
    payload = await resp.json();
  } catch (_) {
    payload = { error: { code: "non-json", message: await resp.text().catch(() => "") } };
  }
  const err = payload && payload.error ? payload.error : {};
  return new GraphError(err.message || resp.statusText || `HTTP ${resp.status}`, {
    status: resp.status,
    code: err.code || String(resp.status),
    requestId: resp.headers.get("request-id") || resp.headers.get("client-request-id"),
    body: payload,
  });
}

async function delay(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

// Single fetch with throttling-aware retry. 429 / 5xx are retried with
// exponential backoff, honoring Retry-After when present.
async function rawFetch(token, method, url, body, attempt = 0) {
  const resp = await fetch(url, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/json",
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (resp.status === 429 || resp.status >= 500) {
    if (attempt >= 4) throw await readError(resp);
    const retryAfter = Number(resp.headers.get("retry-after")) || Math.pow(2, attempt);
    await delay(Math.min(30, retryAfter) * 1000);
    return rawFetch(token, method, url, body, attempt + 1);
  }

  if (!resp.ok && resp.status !== 204) throw await readError(resp);
  if (resp.status === 204) return null;
  return resp.json();
}

export async function graphGet(token, path, query) {
  const sep = path.includes("?") ? "&" : "?";
  const qs = query ? sep + new URLSearchParams(query).toString() : "";
  return rawFetch(token, "GET", `${GRAPH_BASE}${path}${qs}`);
}

export async function graphList(token, path, query) {
  const items = [];
  let url = `${GRAPH_BASE}${path}`;
  if (query) {
    const sep = url.includes("?") ? "&" : "?";
    url += sep + new URLSearchParams(query).toString();
  }
  while (url) {
    const page = await rawFetch(token, "GET", url);
    if (Array.isArray(page.value)) items.push(...page.value);
    url = page["@odata.nextLink"] || null;
  }
  return items;
}

export async function graphPost(token, path, body) {
  return rawFetch(token, "POST", `${GRAPH_BASE}${path}`, body);
}

export async function graphPatch(token, path, body) {
  return rawFetch(token, "PATCH", `${GRAPH_BASE}${path}`, body);
}

// Convenience: find a directory object by displayName.
export async function findByDisplayName(token, collectionPath, displayName, select) {
  const filter = `displayName eq '${displayName.replace(/'/g, "''")}'`;
  const items = await graphList(token, collectionPath, {
    $filter: filter,
    ...(select ? { $select: select } : {}),
  });
  return items[0] || null;
}
