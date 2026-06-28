# Mirage Conditional Access Baseline - release notes (template)

> **Git tags:** This repository had **no tags** at the time these notes were drafted. To use GitHub’s **Generate release notes** with a “previous tag,” create a baseline tag first, then tag each release.

### Suggested tagging (for future automated notes)

1. Tag the first baseline import on commit `8f7022c`, e.g. **`v2026.0.0`**  
   `git tag v2026.0.0 8f7022c` then `git push origin v2026.0.0`
2. Tag this release on **`main`** (e.g. current HEAD when you publish), e.g. **`v2026.1.0`**
3. On **GitHub → Releases → Draft a new release**, set **Previous tag** to `v2026.0.0` and the **target** to `v2026.1.0`, then click **Generate release notes**

---

## v2026.1.0 (draft)

### Highlights

- **Baseline-as-code:** Conditional Access (45 policies), Entra groups, and named locations as **intent JSON** under `baseline/`, with a **deploy SPA** under `docs/` that resolves names to Graph IDs and creates policies mostly in **Report-only**; **eight** rules default **Off** (**CA111**, **CA202**, **CA204**, **CA302**, **CA303**, **CA603**, **CA606**, **CAA01**) - **`CA112`** (User actions) defaults **Report-only** like the rest. Optional `deploymentState` / `deployState` in intent JSON sets Report-only vs Off **only on first CREATE** (POST), never for existing tenant policies.
- **Deploy safety:** No silent overwrites of existing CA policies (name-based match / skip); **dry run**; clarified **skipped** vs **unchanged** behavior; improvements to policy existence checks and display-name matching to reduce accidental **CREATE** churn.
- **Graph / API alignment:** Translator and payload fixes for **CAE-only** session policies, **Prefer evolvable** enums, **workload / agent** policies, optional **first-party app** skips, and related **conditionalAccessConditionSet** shape fixes (e.g. **CAA01**, **CA111**).
- **CA111 (Continuous Access Evaluation - Standard):** Intent and deploy path aligned with Graph limitations (guest / external exclusion omitted where the API rejects that combination for CAE-session-only rules); comments and policy descriptions updated accordingly.
- **Repository hygiene:** **MIT License**, **SECURITY.md**, **`.gitignore`** hardening for Python artifacts; reference workbook handling documented in README.

### Documentation & UX

- **README** restructured for clearer paths (deploy, review, customize, appendix), **Safety** before deploy, **Further reading** after appendices; **policy catalog** as a full **Markdown table** with criticality badges (generated via `generate-baseline.py`), alongside **inventory.html** and **POLICY_INVENTORY.md**.

### For operators

- Validate **Entra ID P2** where risk-based policies require it; fill **named locations**, **group memberships**, and **break-glass** before broad **On**; review **sign-in logs** Report-only tabs, then flip to **On** in **phases** in the Entra admin center.

### Upgrade / migration

- No database or data migration. Refresh from `main`, re-run **`python scripts/generate-baseline.py`** if you maintain a fork, redeploy **GitHub Pages**, and use the deploy app against your tenant as before.

### Acknowledgments

- Built with Microsoft **Conditional Access** and **Microsoft Graph**; **not** a Microsoft product - see README and **SECURITY.md** for reporting issues.

---

### Shorter body (for the GitHub release description field)

**v2026.1.0** - Mirage CA Baseline: intent JSON + Pages deploy SPA; guarded writes (no silent CA PATCH), deploy/Graph fixes (CAE, agent policies, CA111/CAA01), README and generated policy catalog, LICENSE and SECURITY hygiene. See `RELEASE_NOTES.md` for detail.
