---
title: "Treating OpenClaw Like a Junior Sysadmin"
slug: "treating-openclaw-like-a-junior-sysadmin"
date: 2026-05-20T20:10:59Z
lastmod: 2026-10-04T19:40:41Z
draft: false
description: "(Or, yet another blog post on playing around with openclaw, just much less hype)"
topics: ["AI", "Homelab", "Monitoring", "NixOS"]
aliases: ["/2026/05/20/treating-openclaw-like-a-junior-sysadmin/"]
migration_source: ghost
---
<p></p><blockquote>Edit: <br>As of August 2026 I no longer  use OpenClaw, primarily now I use pi.dev, claude code, codex, and Hermes these  days. Things move fast, and I didn't really like the amount of time I was doing care and feeding of OpenClaw.</blockquote><p>I wanted to kick the tires on <a href="https://openclaw.ai/">OpenClaw</a>, but I did not want to install it directly on my primary workstation.</p><p>That's not a knock on OpenClaw specifically. It is just the normal posture I try to keep with new automation tools, especially ones that are designed to sit close to my workflow, read context, talk to services, and take actions on my behalf. Before I hand something the keys to my actual daily-driver environment, I want to see how it behaves in a smaller, more boring box.</p><p>So the question became: how do I evaluate an AI companion without turning it into a trusted endpoint?</p><p>The answer I settled on was to treat it like a junior sysadmin.</p><p>Give it an identity. Give it a "workstation". Give it limited access to logs, metrics, chat, and a couple of source-control systems. Let it observe. Let it help troubleshoot. Do not give it my shell, my browser profile, my SSH agent, or a wide-open view of the homelab.</p><h2 id="the-first-attempt">The First Attempt</h2><p>The first pass was a small VM on one of my internal servers: <code>guiltyspark</code>. That made sense at the time: isolated guest, disposable disk, a narrow network path, and a firewall policy that only allowed what I explicitly needed. The VM was built around a Debian guest with OpenClaw bootstrapped inside it, and the network policy was intentionally grumpy about internal access. Matrix was allowed. The rest of RFC1918 was mostly not.</p><pre><code># This was the original guiltyspark VM shape.
# The bridge could talk to itself, and Matrix was allowed.
# Everything else in RFC1918 got rejected before the final allow.

${iptables} -I FORWARD 1 \
  -i ${openclaw.network.bridge} \
  -o ${openclaw.network.bridge} \
  -j ACCEPT

${iptables} -I FORWARD 2 \
  -i ${openclaw.network.bridge} \
  -d ${openclaw.matrix.ip}/32 \
  -p tcp -m multiport --dports 80,443 \
  -j ACCEPT

${iptables} -I FORWARD 3 -i ${openclaw.network.bridge} -d 10.0.0.0/8 -j REJECT
${iptables} -I FORWARD 4 -i ${openclaw.network.bridge} -d 172.16.0.0/12 -j REJECT
${iptables} -I FORWARD 5 -i ${openclaw.network.bridge} -d 192.168.0.0/16 -j REJECT

# After the explicit internal rejects, normal outbound traffic was okay.
${iptables} -I FORWARD 6 -i ${openclaw.network.bridge} -j ACCEPT
</code></pre><pre><code>                   allowed: tcp/80,443
+---------------+ ------------------------&gt; +-------------------+
| openclaw VM   |                           | matrix.badger.lan |
| Debian guest  |                           | Synapse           |
+---------------+                           +-------------------+
        |
        | blocked: 10/8, 172.16/12, 192.168/16
        v
+---------------------------------------------------------------+
| the rest of the internal network                              |
+---------------------------------------------------------------+
</code></pre><p>That worked well as a security model, but it did not work well as an evaluation environment. The VM (1 core, 4gb ram) felt cramped, and I wanted more horsepower without moving the experiment onto my primary workstation.</p><p>I had a spare laptop sitting around and deployed NixOS, then as a Halo nerd, named it <code>cortana</code>. Good enough. It had actual hardware, it was not my main machine, and it was now part of the NixOS fleet. So Cortana became the OpenClaw host.</p><h2 id="cortana-becomes-the-intern-desk">Cortana Becomes the Intern Desk</h2><p>The first step was, obviously, infrastructure work - Cortana got a real DNS name, <code>cortana.badger.lan</code>, and a static management address from the internal pool.</p><pre><code># common/system/common.nix
# Keep hostnames and management addresses in one shared inventory.

hostnames.cortana = "cortana.badger.lan";

hosts.cortana = {
  mgmt = "10.170.0.117"; # get it? 117? ok...
};

# modules/infrastructure/coredns.nix
# CoreDNS then renders the LAN A record from that inventory.

cortana IN A ${infraCommon.hosts.cortana.mgmt}

# hosts/cortana/networking.nix
# The host gets the same address statically, instead of relying on DHCP luck.

addresses = "${common.hosts.cortana.mgmt}/24";
</code></pre><p>Secrets are handled through SOPS. The rendered OpenClaw configuration lands in <code>/home/cortana/.openclaw/openclaw.json</code> with the Matrix credentials and gateway token injected by the system configuration. No room IDs, passwords, or tokens are baked into the repo.</p><pre><code># hosts/cortana/openclaw.nix
# These secret names exist in Git, but the values live encrypted in SOPS.

sops.secrets = {
  "openclaw/matrix-user-id" = { };
  "openclaw/matrix-password" = { };
  "openclaw/matrix-room-id" = { };
  "openclaw/gateway-token" = { };
};

# Render the runtime config as the cortana user.
# The actual token/password placeholders are replaced by sops-nix at activation time.

sops.templates."openclaw.json" = {
  owner = "cortana";
  group = "users";
  mode = "0400";
};
</code></pre><p>The OpenClaw gateway itself is not running as a user systemd service. That was one of the early pain points. On NixOS, the installer expected a more conventional Linux environment, then we ran into user-bus and package-manager assumptions. The quickstart wanted Node. The Node installer wanted a package manager it recognized. The gateway service wanted systemd user-bus behavior that was not present in the way I was invoking it. Then rootless container namespace setup had its own <code>newuidmap</code> complaints after a reboot.</p><p>None of those problems were individually shocking. They were just enough friction to make the native NixOS path feel like the wrong thing to evaluate first.</p><p>This is primarily because I chose to deploy inside of Distrobox. Cortana is still NixOS, but OpenClaw runs inside a Fedora Distrobox named <code>openclaw</code> because... it's obvious?. The NixOS module owns the outer lifecycle, creates the box if needed, installs the normal Fedora-side dependencies, runs the OpenClaw installer there, and starts the gateway under a system service on the host.</p><pre><code># Host: NixOS
# Container userland: Fedora via Distrobox
# OpenClaw sees a managable Linux host it expects; NixOS still owns the service lifecycle.

boxName = "openclaw";
boxImage = "quay.io/fedora/fedora:latest";

if ! podman container exists ${boxName}; then
  distrobox-create \
    --yes \
    --name ${boxName} \
    --image ${boxImage} \
    --additional-packages "nodejs npm make gcc gcc-c++ cmake python3 chromium git curl tar gzip xz which procps-ng diffutils findutils"
fi

distrobox-enter --name ${boxName} -- bash -lc '
  set -euo pipefail

  # Keep npm global installs under the cortana home directory.
  mkdir -p ${npmPrefix}
  npm config set prefix ${npmPrefix}
  export PATH="${npmPrefix}/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

  # Let OpenClaw install itself in the Fedora userland.
  if ! openclaw --version &gt;/dev/null 2&gt;&amp;1; then
    curl -fsSL https://openclaw.ai/install.sh | bash
  fi
'
</code></pre><pre><code>+-------------------------------------------------------------+
| cortana.badger.lan                                          |
| NixOS                                                       |
|                                                             |
|  systemd: openclaw-gateway.service                          |
|      |                                                      |
|      v                                                      |
|  distrobox-enter openclaw                                   |
|      |                                                      |
|      v                                                      |
|  Fedora userland: node, npm, chromium, openclaw             |
|                                                             |
|  gateway bind: 127.0.0.1:18789                              |
+-------------------------------------------------------------+
</code></pre><pre><code># The host service is intentionally simple.
# NixOS owns start/stop/restart. OpenClaw runs as cortana.

systemd.services.openclaw-gateway = {
  description = "OpenClaw Gateway (Distrobox)";
  wantedBy = [ "multi-user.target" ];
  wants = [ "network-online.target" ];
  after = [ "network-online.target" ];

  serviceConfig = {
    User = "cortana";
    Group = "users";
    WorkingDirectory = "/home/cortana";
    Type = "simple";
    ExecStartPre = openclawBootstrap;
    ExecStart = openclawGatewayStart;
    ExecStop = openclawGatewayStop;
    Restart = "always";
    RestartSec = "10s";
  };
};
</code></pre><p>The gateway binds to loopback on port <code>18789</code>. If I want the dashboard, I SSH tunnel to Cortana and open it locally (for now - eventually it may join the rest of my internal services on <a href="https://github.com/gethomepage/homepage">Homepage</a>. OpenClaw also gets a host-side wrapper, so from Cortana I can run <code>openclaw ...</code> and have it enter the Distrobox with the right PATH and internal CA trust.</p><pre><code># Local workstation
# Nothing exposed on the LAN; the dashboard is reached through SSH.

ssh -N -L 18789:127.0.0.1:18789 cortana@cortana.badger.lan

# Then open this locally:
# http://localhost:18789/
</code></pre><h2 id="identity-not-my-identity">Identity, Not My Identity</h2><p>The important bit for me was that OpenClaw should not <em>be</em> me.</p><p>I created separate identities for it: a GitHub profile and a Forgejo profile for my internal git service. Those accounts are intentionally scoped as service-style users. They can be invited to the things I want them to see, and they can be removed or rotated without touching my personal credentials.</p><pre><code># Conceptually, this is the access model I wanted:

human:badgerops
  - primary workstation
  - normal SSH agent
  - broad repo/admin access
  - browser sessions and personal tokens

assistant:openclaw
  - host: cortana
  - Unix user: cortana
  - GitHub user: &lt;wouldn't you like to know...&gt;
  - Forgejo user: cortana-bot
  - Matrix user: cortana
  - access: selected rooms, selected repos, selected logs/metrics
</code></pre><p>That distinction matters. If this is supposed to act like a junior sysadmin, it should have an account like a junior sysadmin. Not my browser cookies. Not my workstation SSH agent. Not my github or forgejo or <code>${service}</code> token because that is easiest. A little extra work = a little less future me pain. Maybe.</p><p>Right now the goal is not to let it autonomously administer everything. The goal is to let it participate in the troubleshooting loop with enough context to be useful.</p><h2 id="matrix-as-the-control-plane">Matrix As The Control Plane</h2><p>The chat side is Matrix, because that is already where my internal alerting and operational chat lives.</p><p>OpenClaw is configured against my internally hosted Synapse instance at <code>matrix.badger.lan</code>. The Matrix plugin is enabled, encrypted rooms are enabled, and direct messages use pairing. Group access is allowlisted, not open. That means the bot does not get to roam through arbitrary rooms just because it exists on the Matrix homeserver.</p><pre><code># Rendered shape of the Matrix channel config.
# Values shown as placeholders are injected from SOPS.

"channels": {
  "matrix": {
    "enabled": true,
    "homeserver": "https://matrix.badger.lan",
    "network": {
      "dangerouslyAllowPrivateNetwork": true # it's _on_ a private network
    },
    "userId": "${openclaw/matrix-user-id}",
    "password": "${openclaw/matrix-password}",
    "deviceName": "OpenClaw Gateway",
    "encryption": true,
    "dm": {
      "policy": "pairing"
    },
    "groupPolicy": "allowlist",
    "groups": {
      "${openclaw/matrix-room-id}": {
        "enabled": true
      }
    },
    "autoJoin": "allowlist",
    "autoJoinAllowlist": [
      "${openclaw/matrix-room-id}"
    ]
  }
}
</code></pre><p>For the first real room, I added it to the internal infra room. That is also where the Alertmanager-to-Matrix relay can post alerts, so OpenClaw can see the same operational noise I would normally react to: service health, host issues, OpenClaw's own gateway state, and the other homelab monitoring signals.</p><pre><code>+----------------+       webhook        +--------------------------+
| Prometheus     | ------------------&gt;  | Alertmanager             |
| alert rules    |                      |                          |
+----------------+                      +------------+-------------+
                                                   |
                                                   | Matrix relay
                                                   v
                                        +--------------------------+
                                        | #infra Matrix room       |
                                        | humans + OpenClaw        |
                                        +--------------------------+
</code></pre><p>There was a small gotcha here: pairing requests can time out. I spent a bit staring at the CLI saying there were no pending Matrix pairings while the chat UI still showed one. Eventually I realized: it had expired. Start over, pair again, move on.</p><h2 id="observability-for-the-assistant">Observability For The Assistant</h2><p>If I am going to run a helper that is supposed to help with operations, I need to be able to observe the helper too.</p><p>The Cortana module exports OpenClaw health into the Node Exporter textfile collector once per minute. It runs <code>openclaw health --json</code> as the <code>cortana</code> user and converts the output into Prometheus metrics. That gives me scrape success, gateway health, event loop delay, event loop utilization, agent sessions, and Matrix channel state.</p><pre><code># Timer: refresh the OpenClaw textfile metrics every minute.

systemd.timers.openclaw-node-exporter-textfile = {
  wantedBy = [ "timers.target" ];
  timerConfig = {
    OnBootSec = "2m";
    OnUnitActiveSec = "1m";
    Unit = "openclaw-node-exporter-textfile.service";
  };
};

# Collector: ask OpenClaw for health JSON as the cortana user.

health_json="$(${pkgs.util-linux}/bin/runuser -u cortana -- ${openclawWrapper}/bin/openclaw health --json 2&gt;/dev/null)"
</code></pre><pre><code># Example output written to node_exporter's textfile collector.
# Prometheus scrapes this like any other node metric.

openclaw_scrape_success 1
openclaw_gateway_health_ok 1
openclaw_event_loop_delay_p99_milliseconds 12
openclaw_event_loop_utilization 0.02
openclaw_channel_connected{channel="matrix",account="default"} 1
</code></pre><p>Prometheus scrapes Cortana's node exporter with <code>role=openclaw</code>. Alert rules watch for stale OpenClaw metrics, failed health scrapes, an unhealthy gateway, and disconnected channels. There is also a Grafana dashboard for the gateway, because eventually every little homelab experiment needs a dashboard. Apparently this is the law.</p><pre><code># Prometheus target. Cortana is just another node_exporter scrape,
# but it gets role=openclaw so dashboards and alerts can filter cleanly.

- targets: ['${globalCommon.hosts.cortana.mgmt}:9100']
  labels:
    host: cortana
    role: openclaw
</code></pre><pre><code># A few of the OpenClaw-specific alerts.
# These are less about paging me immediately and more about proving the assistant itself is observable.

- alert: OpenClawMetricsStale
  expr: (time() - openclaw_scrape_timestamp_seconds{job="node-exporter",host="cortana"}) &gt; 300
  for: 5m
  labels:
    severity: warning
    category: openclaw

- alert: OpenClawGatewayUnhealthy
  expr: openclaw_gateway_health_ok{job="node-exporter",host="cortana"} == 0
  for: 5m
  labels:
    severity: critical
    category: openclaw

- alert: OpenClawChannelDisconnected
  expr: openclaw_channel_connected{job="node-exporter",host="cortana"} == 0
  for: 5m
  labels:
    severity: warning
    category: openclaw
</code></pre><p>Logs go through <a href="https://vector.dev/">Vector</a> into Loki. OpenClaw writes JSON-ish logs under the Cortana user's home and temporary runtime paths, Vector normalizes the useful fields, and Loki labels them with host, service, unit, source, and level. One minor tradeoff: Vector runs as root on Cortana (for other host log reasons). I am not thrilled by that, but it is contained to this host and may be worth revisiting later.</p><pre><code># Vector reads both the temporary OpenClaw logs and the durable user logs.

sources.openclaw_files = {
  type = "file";
  include = [
    "/tmp/openclaw/openclaw-*.log"
    "/home/cortana/.openclaw/logs/*.jsonl"
  ];
  read_from = "end";
};

# Normalize the labels before sending to Loki.
# This makes queries like {service="openclaw",host="cortana"} work cleanly.

sinks.openclaw_loki = {
  type = "loki";
  endpoint = "http://loki.badger.lan";
  labels = {
    host = "{{ host }}";
    service = "{{ service }}";
    source = "{{ source_type }}";
    unit = "{{ unit }}";
    level = "{{ level }}";
  };
};
</code></pre><h2 id="what-worked">What Worked</h2><p>The model feels right so far.</p><p>OpenClaw is not sitting on my workstation. It does not inherit my local trust. It has its own host, its own account, its own chat identity, and its own source-control identities. It can see selected operational context, especially Matrix alerts and the logs/metrics I choose to expose.</p><p>Distrobox ended up being the right compromise for this stage. I still get a declarative NixOS host managing the lifecycle, DNS, users, SOPS secrets, systemd service, Prometheus integration, Vector integration, and Grafana provisioning. OpenClaw gets a normal Fedora-ish userland where its installer and Node assumptions are much less weird.</p><p>I’ve also been using Cortana as a lightweight engineering assistant around my GitHub and Forgejo work. The first pattern so far is automated <code>clawpatch</code> review: she picks an active repo, runs a read-only code review pass, turns the findings into a Markdown report, commits that report into a dedicated archive repo, and sends me the summary in Matrix.</p><pre><code>cron schedule
  -&gt; choose an active (commits in last year) BadgerOps repo
  -&gt; run clawpatch review
  -&gt; save Markdown report
  -&gt; commit report to forgejo:cortanabot/clawpatch-reports
  -&gt; send summary to Matrix
</code></pre><p>The important part is that this is review-only automation. It does not push branches, open PRs, or publish changes unless I explicitly ask. That keeps the loop useful without letting automation mutate production code behind my back.</p><h2 id="what-still-needs-cleanup">What Still Needs Cleanup</h2><p>The Matrix room configuration started as a single room and the current Nix template still renders a single SOPS-backed room ID into <code>groups</code> and <code>autoJoinAllowlist</code>. I have a multi-room secret shape ready, but the renderer still needs to consume that JSON before I can honestly say the room allowlist is multi-room in the deployed config.</p><pre><code># Current: one SOPS-backed room ID rendered into the allowlist.

"groups": {
  "${openclaw/matrix-room-id}": {
    "enabled": true
  }
}

# Next: render a SOPS-backed JSON object/list for multiple rooms.
# The secret exists, but the Nix template still needs to consume it.

openclaw/matrix-room-ids-json
</code></pre><p>I also want to tighten the source-control permissions further once I know which workflows are useful. The right shape is probably a tiny set of repos, branch-only write permissions where possible, and no credential that would be painful to rotate.</p><p>The next useful test is not whether OpenClaw can answer trivia in chat. I do not care much about that. The useful test is whether it can look at an alert, inspect the narrow set of logs and metrics I exposed, find the likely failing unit or regression, and propose a fix that I can review like any other pull request, same with codebase changes as I continue to work on projects.</p><h3 id="the-workflow-i-want-to-prove">The workflow I want to prove:</h3><pre><code>
1. Alertmanager posts an alert into Matrix
2. OpenClaw sees the alert in an allowlisted room
3. OpenClaw checks only the logs/metrics it has access to
4. OpenClaw proposes a diagnosis and patch
5. Human reviews the change like any other PR
</code></pre><h2 id="the-takeaway">The Takeaway</h2><p>I think this is the pattern I want for AI companion tools in my own infrastructure: do not install them into the most trusted place first. Give them a small desk, a badge with their own name on it, limited read access, and a very boring job.</p><p>In this case, that desk is Cortana. The badge is a Matrix account plus separate GitHub and Forgejo users. The boring job is watching alerts, reading selected logs and metrics, and helping me reason through operational issues.</p><p>That feels a lot better than installing a brand-new assistant directly onto my workstation and hoping the defaults line up with my threat model.</p><p>We'll see where things end up next!</p><p>All for now,</p><p>-BadgerOps</p>
