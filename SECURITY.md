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

In scope: issues in this repo that could affect **confidentiality**, **integrity**, or **availability** when using the generate script, static deploy app, or published GitHub Pages artifacts (for example unsafe handling of tokens, unsafe inclusion of third-party scripts, or unintended writes to Microsoft Graph).

Out of scope by default: purely operational or configuration choices in your own Entra tenant after you deploy policies.

## Safe harbor

We support coordinated disclosure and will not take legal action against good-faith security research that follows this process and avoids harm to users or data.
