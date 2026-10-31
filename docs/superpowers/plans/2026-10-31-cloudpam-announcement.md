# CloudPAM Announcement Blog Post Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a Hugo post announcing CloudPAM (what it is / does / how to use it) with real Playwright stills and three short GIFs, captured via the CloudPAM Nix flake/shell.

**Architecture:** Capture tooling and flake live in `~/code/cloudpam`. Curated media is copied into `badgerops.github.io/static/images/cloudpam/`. The post is a single Markdown file under `content/posts/`. Shared Playwright auth/seed helpers are extracted once, then reused by still and GIF scripts.

**Tech Stack:** Nix flake (`playwright-driver.browsers`), Node Playwright, host `ffmpeg`, Hugo, Go CloudPAM binary (`DEV_MODE=1` in-memory)

## Global Constraints

- Spec: `docs/superpowers/specs/2026-10-31-cloudpam-announcement-design.md`
- Audience: platform/network engineers; hybrid story + how-to; How-to A then seeded discovery B
- Media: stills + exactly 3 GIFs (~8–12s); no WebM primary embeds
- Flake: add Playwright packages; **do not** add ffmpeg to the flake (host OS only)
- Honesty: short Known Limits — IPv4-only; Azure selectable but no collector; single-tenant; analysis mostly API-side
- Do not claim Azure collector, IPv6, multi-tenant isolation, full analysis UI, or “replaces NetBox”
- Voice: BadgerOps conversational (see `content/posts/people-are-actually-using-this-thing.md` for modern Markdown style)
- Capture only against throwaway `DEV_MODE=1` servers; seeding mutates the target
- Pin npm `playwright` to the same major.minor as nixpkgs `playwright-driver` on this flake lock
- Legacy still selectors are stale (Alpine-era); rewrite against SPA routes in `ui/src/navigation.ts` before regenerating blog media
- Commits: cloudpam changes in `~/code/cloudpam`; blog changes in this repo — separate commits per repo when the user asks to commit

## File Structure

| Path | Responsibility |
|------|----------------|
| `~/code/cloudpam/flake.nix` | Add `playwright-driver.browsers`; export `PLAYWRIGHT_BROWSERS_PATH` / skip-download env in `shellHook` |
| `~/code/cloudpam/package.json` | Pin `playwright` to nixpkgs driver version; add `gifs` script |
| `~/code/cloudpam/scripts/lib/capture_helpers.js` | Shared baseURL, auth/setup, CSRF, seed, dismiss banner, out dirs |
| `~/code/cloudpam/scripts/capture_screenshots.js` | Still captures; rewrite legacy group to SPA routes; keep discovery group |
| `~/code/cloudpam/scripts/capture_gifs.js` | Record 3 short WebMs → invoke host `ffmpeg` → GIFs under `photos/gifs/` |
| `~/code/cloudpam/Justfile` | `screenshots` + `gifs` recipes wrapping runbook |
| `~/code/cloudpam/docs/SCREENSHOTS.md` | Document flake Playwright env, host ffmpeg, GIF section, SPA selectors |
| `~/code/cloudpam/photos/*.png` | Regenerated LFS PNGs |
| `~/code/cloudpam/photos/gifs/*.gif` | New GIFs (decide LFS: add `photos/**/*.gif` to `.gitattributes` if committing in cloudpam) |
| `static/images/cloudpam/*` | Blog-facing copies (PNG + GIF) |
| `content/posts/introducing-cloudpam.md` | Announcement post |

---

### Task 1: Nix flake Playwright browsers + version pin

**Files:**
- Modify: `~/code/cloudpam/flake.nix`
- Modify: `~/code/cloudpam/package.json`
- Modify: `~/code/cloudpam/package-lock.json` (via npm install)
- Test: enter `nix develop` and print env + launch Chromium once

**Interfaces:**
- Consumes: existing `devShells.default`
- Produces: `PLAYWRIGHT_BROWSERS_PATH`, `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1`, `PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true` in the shell; npm `playwright` version matching nixpkgs driver

- [ ] **Step 1: Discover the flake’s playwright-driver version**

```bash
cd ~/code/cloudpam
nix develop --command bash -c 'nix eval --raw --impure --expr "(import (builtins.getFlake (toString ./.)).inputs.nixpkgs { system = builtins.currentSystem; }).playwright-driver.version"'
# Alternative if the above is awkward inside the shell:
nix eval --raw "$(pwd)#devShells.$(nix eval --impure --raw --expr builtins.currentSystem).default" 2>/dev/null || true
# Practical one-liner from repo root:
nix develop --command bash -c 'node -e "console.log(require(\"playwright/package.json\").version)"' 2>/dev/null || true
# Prefer:
nix eval --impure --expr 'let flake = builtins.getFlake "'"$PWD"'"; pkgs = import flake.inputs.nixpkgs { system = builtins.currentSystem; }; in pkgs.playwright-driver.version'
```

Expected: a semver string such as `1.55.0` or `1.61.1`. Record it as `DRIVER_VERSION`.

- [ ] **Step 2: Add browsers to `flake.nix` `devShells.default`**

In `packages = with pkgs; [ ... ]`, add:

```nix
playwright-driver.browsers
```

Append to `shellHook` (after the existing Go PATH block):

```bash
export PLAYWRIGHT_BROWSERS_PATH="${pkgs.playwright-driver.browsers}"
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true
echo "Playwright browsers: $PLAYWRIGHT_BROWSERS_PATH"
```

Note: `pkgs` is in scope in the `let`/`mkShell` attrset — use string interpolation of the store path in Nix, not bash `${pkgs...}` inside a single-quoted hook. Correct pattern:

```nix
shellHook = ''
  # ... existing go_root / PS1 ...
  export PLAYWRIGHT_BROWSERS_PATH=${pkgs.playwright-driver.browsers}
  export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
  export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true
  echo "Playwright browsers: $PLAYWRIGHT_BROWSERS_PATH"
'';
```

- [ ] **Step 3: Pin npm playwright to `DRIVER_VERSION`**

```bash
cd ~/code/cloudpam
nix develop --command bash -c "npm install --save-dev playwright@$DRIVER_VERSION"
```

Replace `$DRIVER_VERSION` with the exact version from Step 1. Update `package.json` scripts later in Task 4; for now ensure `devDependencies.playwright` is exact (no caret) matching the driver.

- [ ] **Step 4: Verify Chromium launches**

```bash
cd ~/code/cloudpam
nix develop --command bash -c 'node -e "
const { chromium } = require(\"playwright\");
(async () => {
  const b = await chromium.launch();
  console.log(\"chromium ok\", b.version());
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
"'
```

Expected: prints `chromium ok` and a version string. If it fails with browser revision mismatch, align npm version again or fall back per spec (document missing libs + `npx playwright install chromium`) — prefer fixing the pin first.

- [ ] **Step 5: Commit in cloudpam** (when user asks, or as part of execution session)

```bash
cd ~/code/cloudpam
git add flake.nix package.json package-lock.json
git commit -m "$(cat <<'EOF'
chore: wire Playwright browsers into nix develop shell

Pin the npm playwright package to the flake's playwright-driver so screenshot capture works without ad-hoc browser installs.
EOF
)"
```

---

### Task 2: Extract shared capture helpers + rewrite SPA still captures

**Files:**
- Create: `~/code/cloudpam/scripts/lib/capture_helpers.js`
- Modify: `~/code/cloudpam/scripts/capture_screenshots.js`
- Modify: `~/code/cloudpam/docs/SCREENSHOTS.md` (legacy rot section → SPA routes)
- Test: run discovery + legacy groups against throwaway server; confirm non-stub PNG sizes

**Interfaces:**
- Consumes: Task 1 Playwright env; existing seed payload / auth flow from current script
- Produces: `module.exports` helpers: `baseURL`, `outDir`, `username`, `password`, `seedEnabled`, `wants`, `login`, `seed`, `dismissUpdateBanner`, `VIEWPORTS`, `SEED_ACCOUNT_NAME`, `makeShot`

- [ ] **Step 1: Create `scripts/lib/capture_helpers.js`**

Move from `capture_screenshots.js` without behavior change: env parsing, `setupIfNeeded`, `login`, `csrfToken`, `SEED_POOLS`, `seedIngestPayload`, `seed`, `makeShot`, `dismissUpdateBanner`, `VIEWPORTS`, constants. Export them. Keep comments about `needs_setup` and future `last_seen_at`.

- [ ] **Step 2: Rewrite `captureLegacy` against SPA routes**

Replace Alpine selectors. Use routes from `ui/src/navigation.ts`:

```javascript
async function captureLegacy(page, shot) {
  await page.goto(`${baseURL}/pools`, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('h1:has-text("Address Pools")', { timeout: 15000 });
  await dismissUpdateBanner(page);
  await shot('pools.png', page);

  await page.goto(`${baseURL}/blocks`, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('h1', { timeout: 15000 });
  await shot('blocks.png', page);

  await page.goto(`${baseURL}/accounts`, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('h1:has-text("Cloud Accounts"), h1:has-text("Accounts")', { timeout: 15000 });
  await shot('accounts.png', page);

  // Drop visualization.png / bulk-actions-pools.png / analytics.png from the curated blog set.
  // Keep capturing analytics only if an Analytics page still exists; otherwise omit.
}
```

Adjust the accounts `h1` text to match `AccountsPage.tsx` after a quick `rg 'h1' ui/src/pages/AccountsPage.tsx`. Do **not** rely on sidebar `button:has-text("Pools")` — use `page.goto` paths.

Keep `captureDiscovery` logic as-is (already SPA).

- [ ] **Step 3: Wire main() to helpers**

`capture_screenshots.js` requires `./lib/capture_helpers`, keeps `captureLegacy` / `captureDiscovery` / `main`.

- [ ] **Step 4: Build UI + start throwaway server**

```bash
cd ~/code/cloudpam
nix develop --command bash -c '
  set -euo pipefail
  command -v ffmpeg >/dev/null || echo "WARN: ffmpeg missing on host (needed in Task 3)"
  cd ui && npm install && npm run build && cd ..
  go build -o /tmp/cloudpam-shots ./cmd/cloudpam
  DEV_MODE=1 RATE_LIMIT_RPS=0 CLOUDPAM_LOG_LEVEL=warn /tmp/cloudpam-shots -addr :8195 &
  echo $! > /tmp/cloudpam-shots.pid
  sleep 2
  curl -sf http://localhost:8195/healthz
'
```

Expected: JSON health payload.

- [ ] **Step 5: Run still captures**

```bash
cd ~/code/cloudpam
nix develop --command bash -c '
  APP_URL=http://localhost:8195 \
  SCREENSHOT_USERNAME=screenshot-admin \
  SCREENSHOT_PASSWORD="ScreenshotDev12345!" \
  npm run screenshots
'
```

Expected: logs `Saved .../photos/pools.png` (and discovery set). File sizes ≫ 1KB (not LFS pointer-only working tree issues — if `git lfs` smudge is off, still verify with `file photos/pools.png` → PNG image data).

- [ ] **Step 6: Stop server; update SCREENSHOTS.md**

Kill `/tmp/cloudpam-shots.pid`. Rewrite the “Known rot: legacy captures” section: legacy group is SPA-based; list new selectors/routes; note blog curated set omits visualization/bulk/analytics unless re-added.

- [ ] **Step 7: Commit in cloudpam** (when appropriate)

```bash
git add scripts/lib/capture_helpers.js scripts/capture_screenshots.js docs/SCREENSHOTS.md photos/*.png
git commit -m "$(cat <<'EOF'
fix: rewrite screenshot captures for the React SPA

Share auth/seed helpers and regenerate PNGs against /pools, /blocks, /accounts, and discovery routes.
EOF
)"
```

---

### Task 3: GIF capture script + Just recipes

**Files:**
- Create: `~/code/cloudpam/scripts/capture_gifs.js`
- Modify: `~/code/cloudpam/package.json` (add `"gifs": "node scripts/capture_gifs.js"`)
- Modify: `~/code/cloudpam/Justfile`
- Modify: `~/code/cloudpam/docs/SCREENSHOTS.md`
- Modify: `~/code/cloudpam/.gitattributes` (add `photos/**/*.gif filter=lfs` if GIFs are committed to cloudpam)
- Test: three GIFs under `photos/gifs/`; host ffmpeg required

**Interfaces:**
- Consumes: helpers from Task 2; host `ffmpeg` on PATH
- Produces: `photos/gifs/setup-login.gif`, `photos/gifs/create-pool.gif`, `photos/gifs/discovery-import.gif`

- [ ] **Step 1: Confirm host ffmpeg**

```bash
ffmpeg -version | head -1
```

Expected: version line. If missing, stop and install on the OS (not the flake) before continuing.

- [ ] **Step 2: Implement `scripts/capture_gifs.js`**

Structure:

1. Require helpers; `mkdirSync` `photos/gifs` and `photos/gifs/raw`
2. `chromium.launch()`
3. For each scenario, `browser.newContext({ recordVideo: { dir: rawDir, size: { width: 1280, height: 720 } }, viewport: { width: 1280, height: 720 } })`
4. Drive UI; close page/context to finalize WebM
5. `child_process.spawnSync('ffmpeg', [...], { stdio: 'inherit' })` with palettegen/paletteuse
6. Unlink raw WebM after success (optional keep if `KEEP_GIF_RAW=1`)

Scenarios:

**GIF 1 — setup-login** (fresh server with `needs_setup`):

- Navigate `/setup` or rely on redirect; fill username/password/email; submit; land on app; brief pause on pools/dashboard

**GIF 2 — create-pool** (authenticated + seeded pools optional):

- Go `/pools`; open create UI (match `PoolsPage` button text, e.g. `New Pool` / `Create`); fill name `Demo App Tier`, CIDR `10.20.10.0/24`, parent Corp Supernet / Prod East if UI exposes parent select; submit; show new row

**GIF 3 — discovery-import**:

- `seed()` first; open `/discovery`; select account `prod-platform`; check 2–4 rows; click Preview Import; wait for modal; click Confirm/Import if safe on throwaway server (or end on preview if confirm navigates away too fast — prefer completing import on DEV_MODE)

Encode helper:

```javascript
function webmToGif(webmPath, gifPath) {
  const palette = webmPath + '.png';
  const vf = 'fps=12,scale=1280:-1:flags=lanczos';
  runFfmpeg(['-y', '-i', webmPath, '-vf', `${vf},palettegen=stats_mode=full`, palette]);
  runFfmpeg(['-y', '-i', webmPath, '-i', palette, '-lavfi', `${vf}[x];[x][1:v]paletteuse=dither=bayer`, gifPath]);
  fs.unlinkSync(palette);
}
```

Cap each recording ~12s with `page.waitForTimeout` sparingly; prefer waiting on selectors.

- [ ] **Step 3: Add Just recipes**

```just
screenshots port="8195":
    #!/usr/bin/env bash
    set -euo pipefail
    cd ui && npm install && npm run build && cd ..
    go build -o /tmp/cloudpam-shots ./cmd/cloudpam
    DEV_MODE=1 RATE_LIMIT_RPS=0 CLOUDPAM_LOG_LEVEL=warn /tmp/cloudpam-shots -addr :{{port}} &
    pid=$!
    trap 'kill $pid' EXIT
    sleep 2
    APP_URL=http://localhost:{{port}} \
      SCREENSHOT_USERNAME=screenshot-admin \
      SCREENSHOT_PASSWORD='ScreenshotDev12345!' \
      npm run screenshots

gifs port="8196":
    #!/usr/bin/env bash
    set -euo pipefail
    command -v ffmpeg >/dev/null || { echo "ffmpeg required on host PATH"; exit 1; }
    cd ui && npm install && npm run build && cd ..
    go build -o /tmp/cloudpam-gifs ./cmd/cloudpam
    DEV_MODE=1 RATE_LIMIT_RPS=0 CLOUDPAM_LOG_LEVEL=warn /tmp/cloudpam-gifs -addr :{{port}} &
    pid=$!
    trap 'kill $pid' EXIT
    sleep 2
    APP_URL=http://localhost:{{port}} \
      SCREENSHOT_USERNAME=screenshot-admin \
      SCREENSHOT_PASSWORD='ScreenshotDev12345!' \
      npm run gifs
```

- [ ] **Step 4: Document GIF runbook in SCREENSHOTS.md**

Add sections: Host prerequisites (`ffmpeg`); `just gifs`; output paths; note GIFs are demo-seeded not live AWS.

- [ ] **Step 5: Run GIF capture**

```bash
cd ~/code/cloudpam
nix develop --command just gifs
```

Expected: three GIF files; each opens and shows motion; duration roughly 8–12s (`ffprobe`).

- [ ] **Step 6: Commit in cloudpam**

```bash
git add scripts/capture_gifs.js package.json package-lock.json Justfile docs/SCREENSHOTS.md photos/gifs .gitattributes
git commit -m "$(cat <<'EOF'
feat: add Playwright GIF capture for product demos

Record setup, pool create, and discovery import flows and encode GIFs with host ffmpeg.
EOF
)"
```

---

### Task 4: Copy curated media into the blog

**Files:**
- Create: `static/images/cloudpam/` (PNG + GIF copies)
- Test: files present; not HTML/LFS pointers

**Interfaces:**
- Consumes: regenerated `~/code/cloudpam/photos/*.png` and `photos/gifs/*.gif`
- Produces: blog-static assets listed below

- [ ] **Step 1: Copy curated set**

```bash
mkdir -p /home/badger/code/badgerops.github.io/static/images/cloudpam
cd ~/code/cloudpam
cp -v \
  photos/pools.png \
  photos/blocks.png \
  photos/accounts.png \
  photos/discovery-import-selection.png \
  photos/discovery-import-preview.png \
  photos/discovery-network-hierarchy.png \
  photos/discovery-network-conflicts.png \
  photos/gifs/setup-login.gif \
  photos/gifs/create-pool.gif \
  photos/gifs/discovery-import.gif \
  /home/badger/code/badgerops.github.io/static/images/cloudpam/
```

- [ ] **Step 2: Verify binaries**

```bash
cd /home/badger/code/badgerops.github.io/static/images/cloudpam
file *.png *.gif
wc -c *.png *.gif
```

Expected: PNG image / GIF image; sizes in tens or hundreds of KB+.

- [ ] **Step 3: Commit media in blog repo** (can combine with Task 5)

```bash
cd /home/badger/code/badgerops.github.io
git add static/images/cloudpam
git commit -m "$(cat <<'EOF'
assets: add CloudPAM announcement screenshots and GIFs

Curated Playwright captures for the introducing-cloudpam post.
EOF
)"
```

---

### Task 5: Write `introducing-cloudpam` Hugo post

**Files:**
- Create: `content/posts/introducing-cloudpam.md`
- Test: `hugo server` / `hugo` build; spot-check images

**Interfaces:**
- Consumes: media under `/images/cloudpam/`; product facts from CloudPAM README + CURRENT_STATUS Known Limits only as specified
- Produces: published-ready Markdown post (`draft: false` only when Sol is ready — default `draft: true` until review)

- [ ] **Step 1: Create front matter + skeleton**

```markdown
---
title: "Introducing CloudPAM: IPAM that knows about your cloud"
slug: "introducing-cloudpam"
date: 2026-10-31T12:00:00Z
draft: true
description: "CloudPAM is cloud-native IP address management for multi-account AWS and GCP — hierarchical pools, discovery, drift, and a Terraform provider — without pretending spreadsheets are a plan."
topics: ["networking", "IPAM", "AWS", "GCP", "open-source", "tools"]
---
```

Adjust `date` to publish day when undrafting.

- [ ] **Step 2: Write body sections** (BadgerOps voice; Markdown like the Oct 2026 UniFi follow-up post)

Required section order:

1. Hook — multi-account sprawl / IPAM that never saw the VPC  
2. What it is — one short paragraph + stack mention (Go, React, single binary/container)  
3. What it does — bullets: pools, discovery (AWS + GCP), drift, schema planner, auth/RBAC/API keys, Terraform provider  
4. How to use it (A) — `nix develop` / `just dev` (or documented equivalent); create supernet + child; embed `pools.png`, `create-pool.gif`, `blocks.png`  
5. How to use it (B) — seeded discovery walkthrough; say seeded explicitly; link to upstream `docs/DISCOVERY.md` for real creds; embed discovery stills + `discovery-import.gif`; mention drift page briefly  
6. Known limits — four bullets from the spec  
7. CTA — https://github.com/BadgerOps/cloudpam , deployment docs, file issues  

Image embed pattern:

```markdown
![Address pools hierarchy in CloudPAM](/images/cloudpam/pools.png)

![Creating a child pool](/images/cloudpam/create-pool.gif)
```

Include a short Terraform `cloudpam_pool` HCL snippet (from `docs/TERRAFORM_PROVIDER.md` / provider README) — do not invent resource fields.

- [ ] **Step 3: Build / preview**

```bash
cd /home/badger/code/badgerops.github.io
hugo server -D
# or: make / hugo
```

Expected: post renders at `/introducing-cloudpam/`; images and GIFs load; no broken links to local media.

- [ ] **Step 4: Self-check claims**

Re-read against Known Limits and CURRENT_STATUS: no Azure collector claims; IPv4-only stated; single-tenant; analysis API-not-UI.

- [ ] **Step 5: Commit post**

```bash
git add content/posts/introducing-cloudpam.md static/images/cloudpam
git commit -m "$(cat <<'EOF'
draft: introduce CloudPAM with walkthrough media

Announce what CloudPAM is, how to run the quickstart and seeded discovery path, and ship the Playwright stills/GIFs.
EOF
)"
```

Leave `draft: true` until Sol explicitly asks to publish.

---

## Self-review (plan vs spec)

1. **Spec coverage:** Outline sections → Task 5. Flake Playwright → Task 1. Stills + SPA rewrite → Task 2. GIFs + ffmpeg host → Task 3. Blog static copy → Task 4. Known limits / claims → Task 5 Step 4. Out of scope (README rewrite, live demo, Azure work) not tasked.  
2. **Placeholders:** No TBD steps; flake fallback only if pin fails (explicit). GIF button labels must be confirmed against `PoolsPage`/`DiscoveryPage` during Task 3 — use `rg` on those files before coding selectors.  
3. **Consistency:** Asset names aligned across Tasks 3–5 (`setup-login`, `create-pool`, `discovery-import`). Ports `8195` stills / `8196` gifs avoid clash.

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-10-31-cloudpam-announcement.md`. Two execution options:

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks  
**2. Inline Execution** — execute tasks in this session with executing-plans checkpoints  

Which approach?
