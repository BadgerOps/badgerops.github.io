---
title: "Building an In-App Auto-Updater for a Containerized NixOS Deployment"
slug: "building-in-app-auto-updater-containerized-nixos-deployment"
date: 2026-02-10T16:16:00Z
lastmod: 2026-02-10T16:16:00Z
draft: false
description: "What started as a straightforward trigger-file mechanism has evolved through a dozen iterations into something with pre-upgrade backups, separate backend/frontend version tracking, step-by-step progress reporting, and post-upgrade…"
topics: ["Containers", "DevOps", "Homelab", "NixOS", "Podman"]
aliases: ["/2026/02/10/building-in-app-auto-updater-containerized-nixos-deployment/"]
migration_source: ghost
---
<p>I've been building <a href="https://github.com/BadgerOps/grapheon">Grapheon</a>, a network graph analysis and visualization tool, and deploying it as a pair of Podman containers on NixOS. The stack is pretty straightforward: a FastAPI backend, a React frontend, both published as container images to GitHub Container Registry (GHCR), and wired together with a NixOS module that manages everything through systemd services.</p>
<p>It works great. But every time I cut a new release I'd have to SSH into the box, pull the new images, restart the services. Not exactly the "set it and forget it" experience I was going for.</p>
<p>So I decided to build an in-app auto-updater — the kind where you see a little banner saying "hey, there's a new version" and you click a button and it just... upgrades itself. Sounds simple enough, right?</p>
<p>What started as a straightforward trigger-file mechanism has evolved through a dozen iterations into something with pre-upgrade backups, separate backend/frontend version tracking, step-by-step progress reporting, and post-upgrade health checks. Here's where it stands today.</p>
<h2 id="the-problem">The Problem</h2>
<p>Here's the thing about containerized deployments: the app running <em>inside</em> the container can't exactly restart itself. It doesn't have access to Podman, it doesn't know about systemd, and it definitely shouldn't be pulling its own replacement image. The container is a fish that needs to convince the ocean to swap it out for a different fish.</p>
<p>So the architecture needed two halves:</p>
<ol>
<li><strong>The app side</strong> — the backend checks GitHub for new releases, the frontend shows a banner and lets you click "upgrade"</li>
<li><strong>The NixOS side</strong> — a systemd path unit watches for a trigger file, kicks off an upgrade handler that backs up data, pulls new images from GHCR, restarts services, and verifies the health of the new deployment</li>
</ol>
<p>The container talks to the host through a shared volume. That's it. A file on disk is the entire IPC mechanism. Sometimes the simplest approach is the right one.</p>
<h2 id="the-app-side">The App Side</h2>
<h3 id="backend-checking-for-updates">Backend: Checking for Updates</h3>
<p>The backend has an <code>/api/updates</code> router with three endpoints:</p>
<ul>
<li><code>GET /api/updates</code> — checks GitHub Releases API for the latest version</li>
<li><code>POST /api/updates/upgrade</code> — writes a trigger file to kick off the host-side upgrade</li>
<li><code>GET /api/updates/status</code> — reads the upgrade status file so the frontend can poll progress</li>
</ul>
<p>One thing that matters here: Grapheon uses <strong>separate release tags</strong> for backend and frontend — <code>backend-v0.8.7</code> and <code>frontend-v0.9.1</code>, for example. The two components version independently, so the update check has to handle each one:</p>
<pre><code class="language-python">def _extract_latest_versions(releases: list[dict]) -&gt; tuple[Optional[str], Optional[str]]:
    """
    Extract the latest backend and frontend version tags from releases.
    Returns (backend_version, frontend_version) tuple.
    """
    backend_version = None
    frontend_version = None

    for release in releases:
        tag = release.get("tag_name", "")
        if release.get("prerelease", False):
            continue
        if tag.startswith("backend-v") and backend_version is None:
            backend_version = tag
        elif tag.startswith("frontend-v") and frontend_version is None:
            frontend_version = tag
        if backend_version and frontend_version:
            break

    return backend_version, frontend_version
</code></pre>
<p>The actual GitHub API call is straightforward — hit the releases endpoint, cache for an hour, fall back to stale cache if the API fails:</p>
<pre><code class="language-python">CACHE_TTL_SECONDS = 3600  # 1 hour

async def _fetch_github_releases() -&gt; Optional[list[dict]]:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/repos/BadgerOps/grapheon/releases",
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()
</code></pre>
<p>The version comparison is tuple-based — parse <code>"backend-v0.8.7"</code> into <code>(0, 8, 7)</code>, compare with the current version, done. The parser strips the <code>backend-v</code> or <code>frontend-v</code> prefix before splitting on dots.</p>
<p>One fun bug I hit early on: the frontend version kept coming back as <code>None</code> because the update check was only reading the <code>FRONTEND_VERSION</code> environment variable, which isn't always set. The fix was adding a <code>_detect_frontend_version()</code> function that checks the env var first, then falls back to reading <code>frontend/package.json</code>. Small thing, but it meant the update check was silently skipping the frontend comparison entirely.</p>
<h3 id="backend-triggering-an-upgrade">Backend: Triggering an Upgrade</h3>
<p>When a user clicks "Upgrade now" in the UI, the backend writes a JSON file to <code>/data/upgrade-requested</code>. The key evolution from the initial version is that it now writes <strong>separate version fields</strong> for backend and frontend:</p>
<pre><code class="language-python">@router.post("/upgrade")
async def trigger_upgrade():
    # Check if already upgrading
    status_file = os.path.join(DATA_DIR, "upgrade-status.json")
    if os.path.exists(status_file):
        status_data = json.load(open(status_file))
        if status_data.get("status") == "running":
            raise HTTPException(status_code=409, detail="An upgrade is already in progress")

    # Extract separate backend/frontend target versions
    backend_tag, frontend_tag = _extract_latest_versions(releases)

    upgrade_request = {
        "requested_at": datetime.utcnow().isoformat() + "Z",
        "current_version": settings.APP_VERSION,
        "target_backend_version": target_backend_version,
        "target_frontend_version": target_frontend_version,
    }
    with open(os.path.join(DATA_DIR, "upgrade-requested"), "w") as f:
        json.dump(upgrade_request, f, indent=2)
</code></pre>
<p>That <code>/data</code> directory is a bind mount from the host's <code>/srv/grapheon/data</code>. So when the container writes <code>upgrade-requested</code>, it appears on the host filesystem. And that's where systemd picks it up.</p>
<p>Writing separate version fields fixed a real problem — when backend was at v0.8.6 and frontend was at v0.9.1, the old code would try to pull <code>grapheon-frontend:v0.8.6</code>, which didn't exist. "Manifest unknown" errors at 11pm are not fun.</p>
<h3 id="frontend-the-update-banner">Frontend: The Update Banner</h3>
<p>The React frontend has two places where updates surface. First, an <code>UpdateBanner</code> component that lives at the top of the app and polls <code>/api/updates</code> every 60 minutes:</p>
<pre><code class="language-jsx">const POLL_INTERVAL = 60 * 60 * 1000; // 60 minutes

useEffect(() =&gt; {
    checkForUpdatesHandler();
    pollIntervalRef.current = setInterval(checkForUpdatesHandler, POLL_INTERVAL);
    return () =&gt; clearInterval(pollIntervalRef.current);
}, []);
</code></pre>
<p>When an update is available, you get a blue gradient banner with "What's new" (expands to show release notes) and "Upgrade now." The banner is dismissible per-version via localStorage, so it won't nag you if you choose to skip a release.</p>
<p>The upgrade flow goes through a few states: <code>null</code> → <code>confirm</code> → <code>in_progress</code> → <code>completed</code> (auto-refresh after 3 seconds) or <code>error</code> (with retry). What changed since the first version is the <code>in_progress</code> state — it now shows a <strong>step-by-step progress timeline</strong> instead of just a spinner:</p>
<pre><code class="language-jsx">statusPollIntervalRef.current = setInterval(async () =&gt; {
    const statusResponse = await getUpgradeStatus();

    if (statusResponse.status === 'running') {
        // upgradeProgress is now a structured object
        setUpgradeProgress({
            message: statusResponse.message,
            step: statusResponse.step,
            totalSteps: statusResponse.total_steps,
            progress: statusResponse.progress,
        });
    } else if (statusResponse.status === 'completed') {
        clearInterval(statusPollIntervalRef.current);
        setUpgradeStep('completed');
        setTimeout(() =&gt; window.location.reload(), 3000);
    } else if (statusResponse.status === 'failed') {
        clearInterval(statusPollIntervalRef.current);
        setUpgradeStep('error');
    }
}, 5000);
</code></pre>
<p>The UI renders an animated progress bar showing completion percentage, a "Step N/5" counter, and a visual timeline with checkmarks for completed steps, a pulsing dot for the active step, and dimmed indicators for pending steps. It's a much better experience than staring at "Upgrading..." and wondering if anything is happening.</p>
<p>Second, there's a "Check for Updates" button on the Settings page with a modal that shows version comparison (with separate badges for UI and API versions), release notes, release date, and a GitHub link. Same upgrade flow, just triggered manually instead of by the polling interval.</p>
<h2 id="the-nixos-side">The NixOS Side</h2>
<p>This is where the real fun begins. The NixOS module (<code>grapheon.nix</code>) manages everything: the Podman network, both containers, a cloudflared tunnel, authentication credentials, and the auto-update machinery.</p>
<h3 id="dynamic-tags-the-version-state-file">Dynamic Tags: The Version State File</h3>
<p>The first thing I had to sort out was how to avoid hardcoding image tags in the nix config. If the NixOS module says <code>ghcr.io/badgerops/grapheon-backend:v0.1.0</code>, then that's what systemd starts, and you'd need a <code>nixos-rebuild</code> to change it. That defeats the whole point of an auto-updater.</p>
<p>The solution is a version state file. The nix module defines a <code>defaultTag</code> (used only on first boot), but after that, everything reads from <code>/srv/grapheon/data/current-tag</code>:</p>
<pre><code class="language-nix">let
  defaultTag = "v0.3.0";
  versionFile = "${dataDirDb}/current-tag";

  readTag = ''
    if [ -f "${versionFile}" ]; then
      GRAPHEON_TAG="$(${pkgs.coreutils}/bin/cat "${versionFile}" | ${pkgs.coreutils}/bin/tr -d '[:space:]')"
    else
      GRAPHEON_TAG="${defaultTag}"
    fi
  '';
</code></pre>
<p>Each container service uses a wrapper script instead of inlining the <code>podman run</code> command. The wrapper reads the tag at start time:</p>
<pre><code class="language-nix">backendStartScript = pkgs.writeShellScript "grapheon-backend-start" ''
    set -euo pipefail
    ${readTag}
    echo "Starting grapheon-backend with tag: $GRAPHEON_TAG"
    exec ${pkgs.podman}/bin/podman run \
      --rm \
      --name=grapheon-backend \
      --network=${grapheonNetwork} \
      --network-alias=grapheon-backend \
      --hostname=grapheon-backend \
      -v ${dataDirDb}:/data:Z \
      --env-file ${grapheonAuthEnvFile} \
      -e DATABASE_URL=sqlite:////data/network.db \
      -e APP_NAME=Grapheon \
      -e AUTH_ENABLED=True \
      -e ENFORCE_AUTH=True \
      -e JWT_ALGORITHM=HS256 \
      -e JWT_EXPIRATION_MINUTES=60 \
      --label io.containers.autoupdate=registry \
      ${backendImageBase}:$GRAPHEON_TAG
'';
</code></pre>
<p>Notice there's no <code>-e APP_VERSION</code> being injected. That was actually a bug in my first iteration — the nix config was passing the hardcoded version as an env var, which overrode whatever version the container image had baked in. The backend's <code>config.py</code> already reads a <code>VERSION</code> file from inside the container, so we just let it do its thing.</p>
<p>Also notice the auth-related environment variables and <code>--env-file</code> — Grapheon picked up OIDC and local admin authentication along the way, and those credentials get injected from a separate env file on the host that the NixOS activation script creates on first deploy.</p>
<h3 id="the-auto-update-script-daily-timer">The Auto-Update Script (Daily Timer)</h3>
<p>The NixOS module has an inline auto-update script for the daily timer that handles the GHCR query and image pull:</p>
<pre><code class="language-nix">autoUpdateScript = pkgs.writeShellScript "grapheon-auto-update" ''
    set -euo pipefail

    # GHCR requires an anonymous bearer token even for public images
    token="$(${pkgs.curl}/bin/curl -fsSL \
      'https://ghcr.io/token?scope=repository:badgerops/grapheon-backend:pull' \
      | ${pkgs.jq}/bin/jq -r '.token' \
    )"

    latest_tag="$(${pkgs.curl}/bin/curl -fsSL \
      -H "Authorization: Bearer $token" \
      https://ghcr.io/v2/badgerops/grapheon-backend/tags/list \
      | ${pkgs.jq}/bin/jq -r '.tags[]' \
      | ${pkgs.gnugrep}/bin/grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' \
      | ${pkgs.coreutils}/bin/sort -V \
      | ${pkgs.coreutils}/bin/tail -n1 \
    )"

    # Compare against what we're running
    ${readTag}
    if [ "$GRAPHEON_TAG" = "$latest_tag" ]; then
      echo "Already running $latest_tag — nothing to do"
      exit 0
    fi

    # Pull both images
    ${pkgs.podman}/bin/podman pull ${backendImageBase}:$latest_tag
    ${pkgs.podman}/bin/podman pull ${frontendImageBase}:$latest_tag

    # Persist the new tag — services read this on next start
    ${pkgs.coreutils}/bin/echo "$latest_tag" &gt; "${versionFile}"

    # Restart picks up the new tag from the state file
    systemctl restart podman-grapheon-backend.service
    systemctl restart podman-grapheon-frontend.service
'';
</code></pre>
<p>Note the fully-qualified Nix store paths (<code>${pkgs.curl}/bin/curl</code> instead of bare <code>curl</code>) — this is how NixOS scripts ensure they use the exact versions of tools declared in the system configuration, not whatever happens to be on <code>$PATH</code>.</p>
<h3 id="the-upgrade-handler-script-grapheon-upgradesh">The Upgrade Handler Script (grapheon-upgrade.sh)</h3>
<p>The in-app upgrade trigger runs through a more evolved path than the daily auto-update. The Grapheon repo includes a standalone <code>scripts/grapheon-upgrade.sh</code> that implements a <strong>five-step upgrade process</strong> with granular status reporting:</p>
<pre><code class="language-bash">#!/usr/bin/env bash
# grapheon-upgrade.sh — Host-level upgrade watcher script
set -euo pipefail

DATA_DIR="${DATA_DIR:-/data}"
REQUEST_FILE="${DATA_DIR}/upgrade-requested"
STATUS_FILE="${DATA_DIR}/upgrade-status.json"
BACKUP_DIR="${DATA_DIR}/backups"
HEALTH_URL="http://localhost:8000/api/health"
TOTAL_STEPS=5
</code></pre>
<p>The script reads <strong>separate backend and frontend versions</strong> from the trigger file, with backward-compat fallback to the old single <code>target_version</code> field:</p>
<pre><code class="language-bash">read -r BACKEND_VERSION FRONTEND_VERSION &lt; &lt;(python3 -c "
import json, sys
try:
    data = json.load(open('${REQUEST_FILE}'))
    bv = data.get('target_backend_version', data.get('target_version', ''))
    fv = data.get('target_frontend_version', bv)
    print(bv, fv)
except Exception as e:
    print('', file=sys.stderr)
    sys.exit(1)
" 2&gt;/dev/null || echo "")
</code></pre>
<p>Then it runs through five steps, writing structured JSON status after each one so the frontend can track progress:</p>
<p><strong>Step 1: Back up data.</strong> Before touching anything, tar up the SQLite database, WAL, config, and env files to <code>/data/backups/grapheon-backup-YYYY-MM-DD-HHMMSS.tar.gz</code>. If the upgrade goes sideways, you've got a snapshot.</p>
<p><strong>Step 2: Pull backend image.</strong> <code>podman pull ghcr.io/badgerops/grapheon-backend:v${BACKEND_VERSION}</code> with a 5-minute timeout.</p>
<p><strong>Step 3: Pull frontend image.</strong> <code>podman pull ghcr.io/badgerops/grapheon-frontend:v${FRONTEND_VERSION}</code> — pulled separately with its own version tag.</p>
<p><strong>Step 4: Restart services.</strong> <code>systemctl restart</code> both containers.</p>
<p><strong>Step 5: Health check.</strong> Curl the <code>/api/health</code> endpoint every second for up to 30 seconds. If it never responds, the upgrade is marked as failed.</p>
<p>Each step writes a status update that includes step progress:</p>
<pre><code class="language-bash">write_status() {
    local status="$1" step="$2" msg="$3"
    local progress=$(( (step * 100) / TOTAL_STEPS ))
    [[ "${status}" == "completed" ]] &amp;&amp; progress=100
    cat &gt; "${STATUS_FILE}" &lt;&lt;EOF
{
    "status": "${status}",
    "message": "${msg}",
    "step": ${step},
    "total_steps": ${TOTAL_STEPS},
    "progress": ${progress},
    "updated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
}
</code></pre>
<h3 id="the-ghcr-authentication-saga">The GHCR Authentication Saga</h3>
<p>This one bit me. My first version of the script just curled the GHCR v2 API directly:</p>
<pre><code class="language-bash">curl -fsSL https://ghcr.io/v2/badgerops/grapheon-backend/tags/list
</code></pre>
<p>401 Unauthorized. Even though the images are public.</p>
<p>Turns out GHCR implements the <a href="https://docs.docker.com/registry/spec/auth/token/">Docker Registry v2 authentication spec</a>, which requires a token exchange even for anonymous access to public repositories. You have to:</p>
<ol>
<li>Hit <code>https://ghcr.io/token?scope=repository:OWNER/REPO:pull</code> to get an anonymous bearer token</li>
<li>Pass that token as <code>Authorization: Bearer $token</code> on subsequent API calls</li>
</ol>
<p>One of those things that makes total sense in retrospect but is completely non-obvious when you're staring at a 401 from a public registry at 11pm.</p>
<h3 id="systemd-path-unit-the-glue">Systemd Path Unit: The Glue</h3>
<p>The bridge between "container wrote a file" and "host pulls new images" is a systemd path unit:</p>
<pre><code class="language-nix">systemd.paths.grapheon-upgrade-trigger = {
    description = "Watch for Grapheon in-app upgrade request";
    wantedBy = [ "paths.target" ];
    pathConfig = {
        PathExists = "${dataDirDb}/upgrade-requested";
        Unit = "grapheon-upgrade-watcher.service";
    };
};
</code></pre>
<p>When <code>/srv/grapheon/data/upgrade-requested</code> appears, systemd activates the <code>grapheon-upgrade-watcher</code> service, which runs the upgrade handler. In the NixOS module, this is currently an inline wrapper that calls the auto-update script with status reporting:</p>
<pre><code class="language-nix">upgradeHandlerScript = pkgs.writeShellScript "grapheon-upgrade-handler" ''
    set -euo pipefail

    STATUS_FILE="${dataDirDb}/upgrade-status.json"
    TRIGGER_FILE="${dataDirDb}/upgrade-requested"

    write_status() {
      ${pkgs.coreutils}/bin/echo "$1" &gt; "$STATUS_FILE"
    }

    write_status "{\"status\":\"running\",\"message\":\"Pulling latest images from GHCR...\",\"started_at\":\"$(${pkgs.coreutils}/bin/date -Iseconds)\"}"

    # Remove trigger so the path unit re-arms
    ${pkgs.coreutils}/bin/rm -f "$TRIGGER_FILE"

    if ${autoUpdateScript}; then
      write_status "{\"status\":\"completed\",\"message\":\"Upgrade completed successfully.\",\"completed_at\":\"$(${pkgs.coreutils}/bin/date -Iseconds)\"}"
    else
      write_status "{\"status\":\"failed\",\"message\":\"Auto-update script exited with an error. Check journalctl -u grapheon-upgrade-watcher for details.\",\"completed_at\":\"$(${pkgs.coreutils}/bin/date -Iseconds)\"}"
    fi
'';
</code></pre>
<p>The next step is migrating this inline handler to call <code>grapheon-upgrade.sh</code> instead, which would bring the NixOS in-app upgrade path in line with the standalone script's five-step backup-pull-restart-healthcheck flow. For now, the daily timer uses the inline script (which queries GHCR for the latest tag), and the in-app path uses the wrapper above.</p>
<p>There's also a daily timer for unattended updates:</p>
<pre><code class="language-nix">systemd.timers.grapheon-auto-update = {
    description = "Daily Grapheon auto-update check";
    wantedBy = [ "timers.target" ];
    timerConfig = {
        OnCalendar = "daily";
        Unit = "grapheon-auto-update.service";
        Persistent = true;
    };
};
</code></pre>
<p>This runs the auto-update script on a schedule, so even if nobody is looking at the UI, the deployment stays current.</p>
<h2 id="two-tag-schemes">Two Tag Schemes</h2>
<p>One thing worth calling out: there are two different tag patterns in play.</p>
<p><strong>GHCR container tags</strong> use a plain <code>v</code> prefix: <code>v0.3.0</code>, <code>v0.8.7</code>. The NixOS daily auto-update script queries these from the GHCR v2 tags API and filters for <code>^v[0-9]+\.[0-9]+\.[0-9]+$</code>. Both backend and frontend containers get tagged with the same version when CI publishes them.</p>
<p><strong>GitHub release tags</strong> use component prefixes: <code>backend-v0.8.7</code>, <code>frontend-v0.9.1</code>. The in-app update check queries these from the GitHub Releases API. Backend and frontend can version independently here — the frontend might be at v0.9.1 while the backend is at v0.8.7.</p>
<p>The in-app upgrade writes the separate versions to the trigger file, and the upgrade handler pulls each image with its correct tag. The daily auto-update uses a single GHCR tag for both. This works because CI publishes matching images to GHCR under the unified tag, even while GitHub releases track them separately.</p>
<h2 id="the-full-picture">The Full Picture</h2>
<p>Here's the flow when someone clicks "Upgrade now":</p>
<ol>
<li>Frontend calls <code>POST /api/updates/upgrade</code></li>
<li>Backend writes <code>/data/upgrade-requested</code> with separate <code>target_backend_version</code> and <code>target_frontend_version</code> fields (bind-mounted from host)</li>
<li>Systemd path unit detects the file, activates the upgrade handler</li>
<li>Handler writes <code>{"status":"running","step":1,"total_steps":5,"progress":20}</code> — <strong>Step 1: Backing up data</strong></li>
<li>Handler creates a tar.gz backup of the database and config files</li>
<li>Handler deletes the trigger file (re-arms the path unit)</li>
<li><strong>Step 2:</strong> Pull backend image from GHCR with the backend version tag</li>
<li><strong>Step 3:</strong> Pull frontend image from GHCR with the frontend version tag</li>
<li><strong>Step 4:</strong> Restart both Podman services</li>
<li><strong>Step 5:</strong> Health check — poll <code>/api/health</code> until it responds (up to 30s)</li>
<li>Handler writes <code>{"status":"completed","step":5,"total_steps":5,"progress":100}</code></li>
<li>Frontend polls <code>GET /api/updates/status</code>, renders the progress bar and step timeline, sees "completed," auto-refreshes</li>
<li>User sees the new version. Hopefully.</li>
</ol>
<p>If any step fails, the handler writes <code>{"status":"failed","step":N}</code> with a message, and the frontend shows the error with a retry button.</p>
<p>The entire IPC is two files on a shared volume. No message queues, no sockets, no D-Bus. Just a trigger file and a status file. The container doesn't need any special privileges, and the host-side scripts are pure NixOS — fully declarative, reproducible, and auditable.</p>
<h2 id="lessons-learned">Lessons Learned</h2>
<p><strong>GHCR auth is not optional.</strong> Even for public images, you need the token dance. Don't assume anonymous access works like Docker Hub.</p>
<p><strong>File-based IPC is underrated.</strong> systemd path units are built for exactly this kind of thing. They're reliable, they re-arm automatically, and they require zero custom infrastructure.</p>
<p><strong>A version state file beats hardcoded tags.</strong> Instead of pinning an image tag in your nix config and retagging at runtime (gross) or requiring a <code>nixos-rebuild</code> for every release, just store the current tag in a file on disk. The service wrapper reads it at start time, and the auto-update script writes it before restarting. The nix module's <code>defaultTag</code> is only there for first boot.</p>
<p><strong>Don't override what the container already knows.</strong> My first pass had the nix config injecting <code>-e APP_VERSION=0.1.0</code> into the container. The backend already reads its version from a <code>VERSION</code> file baked into the image, but the env var trumped it. So even after a successful upgrade to v0.3.0, the UI still showed 0.1.0. The fix was just... deleting the env var and letting the container report its own version.</p>
<p><strong>Version your components independently.</strong> The backend and frontend don't always change in lockstep. Early on, I used a single version tag for both, which caused "manifest unknown" errors when they diverged. Now the trigger file carries <code>target_backend_version</code> and <code>target_frontend_version</code> separately, and the upgrade script pulls each with its own tag. The fallback to the old single <code>target_version</code> field keeps it backward-compatible.</p>
<p><strong>Back up before you upgrade.</strong> The pre-upgrade backup was added after a close call. It's a tar.gz of the SQLite database, WAL file, and config — takes milliseconds and gives you a rollback point. Cheap insurance.</p>
<p><strong>Health checks close the loop.</strong> The original version would restart the services and call it done. But "services restarted" doesn't mean "services healthy." Adding a 30-second health check loop that polls <code>/api/health</code> catches startup failures that would otherwise silently leave the app down.</p>
<p><strong>Show progress, not just status.</strong> The first version just showed "Upgrading..." with a spinner. Now the frontend renders a progress bar, a step counter ("Step 3/5"), and a visual timeline with checkmarks. Users don't wonder if it's stuck anymore.</p>
<p><strong>Cache with a fallback.</strong> The 1-hour cache on GitHub API responses means we're not rate-limited, and falling back to stale cache on API failure means the update check never hard-fails from the user's perspective.</p>
<p><strong>Status polling is fine.</strong> I considered WebSockets for the upgrade progress, but polling every 5 seconds is plenty responsive for an operation that takes 30-60 seconds. Keep it simple.</p>
<p>The whole thing has grown from the initial implementation to roughly 500 lines of Python, 550 lines of React, 170 lines of standalone shell script, and 300 lines of Nix. Not bad for a feature that means I never have to SSH in to deploy again.</p>
<p>This grew from just a whim 'hey, how can I make this auto-update' to 'hey, it would be cool if I could do in-app updates' to the current iteration. I think I'll create a git repo &amp; blog post around how to implement this in <em>your</em> application, for ease of reference.</p>
<p>All for now,</p>
<p>-BadgerOps</p>
