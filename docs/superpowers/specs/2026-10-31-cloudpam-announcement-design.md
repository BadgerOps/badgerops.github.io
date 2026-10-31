# CloudPAM Announcement Blog Post — Design

**Date:** 2026-10-31  
**Status:** Draft for review  
**Repos:** `badgerops.github.io` (post + static media), `~/code/cloudpam` (flake, Playwright capture, GIFs)

## Goal

Publish a single Hugo blog post on BadgerOps that announces CloudPAM: what it is, what it does, and how to use it — for platform/network engineers — with refreshed still screenshots and 2–3 short usage GIFs captured via Playwright inside the CloudPAM Nix flake/shell.

## Decisions (locked)

| Decision | Choice |
|----------|--------|
| Shape | Hybrid: short origin/problem story + concrete end-to-end how-to as backbone |
| Audience | Platform / network engineers at work (multi-account AWS/GCP, drift, Terraform) |
| How-to spine | **A then B**: local quickstart (pools) → seeded discovery import/drift (no live cloud creds for media) |
| Media | Stills + 2–3 short GIFs |
| Nix | Add Playwright-related packages to `cloudpam` flake; **ffmpeg on the host OS** (not flake) |
| Honesty | Short **Known limits** section; do not dump every gap from CURRENT_STATUS |
| Packaging | One long post (not teaser + companion, not README-only) |

## Post outline

Working title: *Introducing CloudPAM: IPAM that knows about your cloud*  
Slug: `introducing-cloudpam`  
File: `content/posts/introducing-cloudpam.md`

1. **Hook** — Multi-account AWS/GCP IP sprawl; spreadsheets / IPAM that do not see cloud reality  
2. **What it is** — Cloud-native IPAM for hybrid/multi-cloud; Go + React; single binary / container  
3. **What it does** — Hierarchical pools; AWS (+ GCP) discovery; drift detect/resolve/ignore; schema planner; auth/RBAC/API keys; brief Terraform provider for pools/accounts  
4. **How to use it (A)** — Flake/`just dev` (or documented DEV_MODE binary) quickstart; create supernet → child pools; search. Stills + 1 GIF  
5. **How to use it (B)** — Seeded discovery path: resources → select → import → conflicts/drift. Explicitly say demo uses seeded data; link `docs/DISCOVERY.md` for real AWS/GCP. Stills + 1–2 GIFs  
6. **Known limits** — IPv4-only; Azure selectable but no collector; single-tenant; analysis mostly API-side  
7. **CTA** — GitHub, deployment docs, issues welcome  

**Voice:** BadgerOps conversational (Graphēon / UniFi provider posts): first person, concrete, lightly wry. Work-facing; no homelab cosplay.

**Claims to make:** Hierarchical pools, AWS (+ GCP) discovery, drift, schema planner, auth/RBAC/API keys, Terraform provider (pools/accounts), single-binary/container deploy.

**Claims to avoid:** Azure collector works; IPv6; multi-tenant isolation; full analysis UI; “replaces NetBox.”

## Media capture pipeline

### Environment

- All capture from `~/code/cloudpam` inside `nix develop`
- Follow/extend `docs/SCREENSHOTS.md` (throwaway in-memory server, seed via Playwright)
- Host prerequisite: `ffmpeg` installed on the OS for GIF encode
- Current `photos/*.png` files are Git LFS / stub placeholders (~131 bytes ASCII); regenerate real PNGs before copying to the blog

### Flake changes (`~/code/cloudpam/flake.nix`)

Add packages needed to run Playwright Chromium reliably in the dev shell:

- Keep `nodejs_22`, `just`, Go toolchain (already present)
- Prefer Nix-managed Playwright browsers via `playwright-driver.browsers` (or the current nixpkgs equivalent) and set `PLAYWRIGHT_BROWSERS_PATH` / `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1` in `shellHook` so `npm run screenshots` does not download browsers into the user profile
- If that package is unavailable or broken on this nixpkgs pin, fall back to documenting `npx playwright install chromium` plus the minimal shared library packages the install reports missing — still inside the flake, still no ffmpeg
- Add `just screenshots` and `just gifs` recipes wrapping `docs/SCREENSHOTS.md`

Do **not** add ffmpeg to the flake; document it as a host OS dependency in `docs/SCREENSHOTS.md`.

### Stills

- Reuse/extend `scripts/capture_screenshots.js` + existing seed payloads
- Output: `cloudpam/photos/*.png`
- Copy curated set to `badgerops.github.io/static/images/cloudpam/`

**Curated stills (~8):**

| Asset | View |
|-------|------|
| `pools.png` | Pool hierarchy |
| `blocks.png` | Assigned blocks / allocation view (existing capture group) |
| `discovery-import-selection.png` | Resources selected + toolbar |
| `discovery-import-preview.png` | Import preview |
| `discovery-network-hierarchy.png` | Merged network hierarchy |
| `discovery-network-conflicts.png` | Conflict review |
| `accounts.png` | Cloud accounts |
| Terraform | Show a short `cloudpam_pool` HCL snippet in prose (no extra UI still required) |

### GIFs (3 short, ~8–12s each)

1. First-boot setup / login → land on pools  
2. Create child pool under supernet  
3. Discovery: select resources → import preview → confirm  

**Technique:** Playwright video recording (WebM) → host `ffmpeg` with palettegen/paletteuse → GIF. Prefer a dedicated `scripts/capture_gifs.js` (or mode flag) sharing auth/setup/seed helpers with the still script.

### Blog embeds

- Paths under `/images/cloudpam/...` via Hugo static files
- `<figure>` / `<img>` (and GIF `<img>`) in the post; no external CDN

## Repo touchpoints

| Repo | Changes |
|------|---------|
| `cloudpam` | Flake Playwright deps; GIF capture script; optional Just recipes; regenerate `photos/`; update `docs/SCREENSHOTS.md` (ffmpeg host prereq, GIF section) |
| `badgerops.github.io` | `content/posts/introducing-cloudpam.md`; `static/images/cloudpam/*`; this design spec under `docs/superpowers/specs/` |

## Out of scope

- Rewriting CloudPAM README as the primary announcement  
- Public hosted demo instance  
- Implementing Azure collector, IPv6, multi-tenancy, or analysis UI  
- Adding ffmpeg to the Nix flake  
- Video/WebM primary embeds (GIF + PNG only for the post)

## Success criteria

- Post drafts in Hugo with outline sections above and BadgerOps voice  
- Real screenshots (not LFS stubs) and 3 GIFs render locally via `hugo server`  
- Capture runbook works end-to-end: `nix develop` → build/run throwaway server → stills + GIFs → copy to blog static  
- Known limits section present and accurate vs CURRENT_STATUS for the four called-out items  
- Reader can reproduce How-to A without cloud credentials; How-to B with seed path documented  

## Implementation follow-up

After this spec is approved, write an implementation plan via the writing-plans skill to `docs/superpowers/plans/2026-10-31-cloudpam-announcement.md` covering flake edits, capture scripts, media refresh, and the Hugo post.
