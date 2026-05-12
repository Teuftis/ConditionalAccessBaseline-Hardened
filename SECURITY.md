# Security

Thank you for reviewing the security of this project.

## Reporting a vulnerability

**Preferred:** use [GitHub Security Advisories](https://docs.github.com/code-security/security-advisories/about-github-security-advisories) for this repository ( **Security** tab → **Report a vulnerability** ). That keeps details private while maintainers triage and fix.

Include:

- Description of the impact and affected component (for example deploy SPA, generator, or baseline JSON).
- Steps to reproduce or proof-of-concept where safe and appropriate.
- Your preferred contact for follow-up (optional).

We will acknowledge receipt and coordinate a fix and disclosure timeline as far as we reasonably can.

If you cannot use GitHub (for example you are not a GitHub user), open an issue with **no exploitable details**, and ask to be contacted privately; we will follow up to obtain the full report securely.

## Scope

In scope: issues in this repo that could affect **confidentiality**, **integrity**, or **availability** when using the generate script, static deploy app, or published GitHub Pages artifacts (for example unsafe handling of tokens, unsafe inclusion of third-party scripts, unexpected **overwrite** behavior, or unintended **writes** to Microsoft Graph-including **creating** Conditional Access policies the operator did not intend).

Out of scope by default: purely operational or configuration choices in your own Entra tenant after you deploy policies.

## Client-side hardening (GitHub Pages)

The deploy SPA builds UI text with **`textContent`** only (never `innerHTML`) so tenant or Graph-derived strings cannot execute as markup.

Defense in depth shipped in [`docs/index.html`](docs/index.html):

- **Content-Security-Policy** (meta tag - Pages sites cannot emit security headers unless you front them with a proxy or CDN you control). The policy limits script to same-origin modules plus the pinned MSAL CDN host, restricts `connect-src` to Graph / Microsoft login endpoints and **`raw.githubusercontent.com`** baseline fallback, and sets `frame-src` for hidden auth iframes. **National clouds** may use other hosts - if sign-in breaks, extend [`docs/index.html`](docs/index.html) accordingly or drop the meta tag temporarily and report an issue.

- [**Subresource Integrity**](https://developer.mozilla.org/en-US/docs/Web/Security/Subresource_Integrity) on the [`@azure/msal-browser`](https://cdn.jsdelivr.net/npm/@azure/msal-browser@3.28.0/lib/msal-browser.min.js) script (`integrity="sha384-…"`). You must bump the hash when upgrading the pinned MSAL version.

The [`docs/inventory.html`](docs/inventory.html) catalog is script-free CSP `script-src 'none'` (policy template in [`scripts/generate-baseline.py`](scripts/generate-baseline.py)).

**Not covered here:** CSP `frame-ancestors` (clickjacking) is ignored in `<meta>` in most browsers; use HTTP headers via an edge/WAF/reverse-proxy if framing is a concern.

## Safe harbor

We support coordinated disclosure and will not take legal action against good-faith security research that follows this process and avoids harm to users or data.
