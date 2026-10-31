---
title: "Introducing CloudPAM: IPAM that knows about your cloud"
slug: "introducing-cloudpam"
date: 2026-10-31T12:00:00Z
draft: true
description: "CloudPAM is cloud-native IP address management for multi-account AWS and GCP — hierarchical pools, discovery, drift, and a Terraform provider — without pretending spreadsheets are a plan."
topics: ["networking", "IPAM", "AWS", "GCP", "open-source", "tools"]
---

I have lost count of the spreadsheets named `ip-plan-FINAL-v7.xlsx`.

The sheet says `10.20.0.0/16` belongs to prod. Somewhere in AWS, a VPC in an account nobody added to the sheet is already using `10.20.4.0/24`. The IPAM tool, when there is one, still treats the cloud as a column a person types into. By the time the overlap shows up, two teams have built on it.

That is the job I wanted a tool for. The plan and the cloud, in the same place, with the difference written down.

## What it is

[CloudPAM](https://github.com/BadgerOps/cloudpam) is IP address management for multi-account AWS and GCP. You keep a hierarchy of pools, which is the plan, and a separate record of what the cloud APIs actually returned. The server is Go. The UI is React, compiled into that same binary, and the container image is that binary. PostgreSQL is the production store. SQLite covers a single node. The dev server can run entirely in memory.

## What it does

* **Hierarchical pools.** Supernets, regions, app tiers: whatever shape matches the network. A child CIDR has to sit inside its parent, and sibling ranges are checked for overlap.
* **Discovery for AWS and GCP.** AWS covers VPCs, subnets, Elastic IPs, and Organizations, including a standalone agent. GCP covers networks, subnetworks, and external IPs through the server collector.
* **Drift.** Compare discovered resources with managed pools. The Drift Detection page lists unmanaged resources, CIDR mismatches, and orphaned discovered pools. Resolve and ignore record your decision on each item.
* **Schema Planner.** Lay out a hierarchy, run the conflict check, and apply it.
* **Auth.** Local users, sessions, API keys, custom roles, and optional OIDC.
* **Terraform.** A separate provider manages pools and accounts. `endpoint` and `api_key` are the provider settings (or `CLOUDPAM_ENDPOINT` and `CLOUDPAM_API_KEY`). Keys use the `cpam_` prefix. Create one under **Administration → API Keys** (`/config/api-keys`).

```hcl
provider "cloudpam" {
  endpoint = "https://cloudpam.example.com"
  api_key  = var.cloudpam_api_key
}

resource "cloudpam_pool" "corp" {
  name = "Corp Supernet"
  cidr = "10.0.0.0/8"
}
```

`cloudpam_account` is the other v1 resource, for the cloud accounts those pools belong to. Discovery runs, drift items, and users stay outside the provider.

## Run it locally

This part needs no cloud credentials.

```bash
git clone https://github.com/BadgerOps/cloudpam.git
cd cloudpam
nix develop
just ui-build
just dev
```

`just ui-build` compiles the React UI into `web/dist`, which the binary embeds. A fresh clone ships a placeholder page and no built assets, so `just dev` alone comes up with an empty UI. `just dev` sets `DEV_MODE=1` and starts the in-memory server at [http://localhost:8080](http://localhost:8080). From the same shell, after that UI build, `DEV_MODE=1 go run ./cmd/cloudpam` is the same server without Just. Quit it and the data is gone. That is what dev mode is for.

First boot is a setup form. Create the admin account, sign in, and you land on Address Pools.

![First-boot setup and sign-in](/images/cloudpam/setup-login.gif)

A fresh server has an empty tree. Use **New Pool** for the supernet (`Corp Supernet`, `10.0.0.0/8`, no parent), then **New Pool** again for a child inside it. Fill in the name, the CIDR, and the parent, then **Create Pool**.

The stills and the clip below were captured on the seeded demo, so the tree is already populated. The clip adds `Demo App Tier` (`10.20.10.0/24`) under the seeded `Prod East VPC`. The dialog is the same one you get on a fresh server. The pools table lists root pools until the search box has text, which is why the clip searches for the new name before the child row appears.

![Address pools hierarchy in CloudPAM](/images/cloudpam/pools.png)

![Creating a child pool](/images/cloudpam/create-pool.gif)

Allocated Blocks is the designed space: the ranges you meant to hand out, separate from what discovery later observes.

![Allocated blocks in CloudPAM](/images/cloudpam/blocks.png)

## Discovery, with seeded data

Everything in this section comes from a seeded demo. Playwright loaded a throwaway in-memory server with managed pools (`Corp Supernet`, `Prod East VPC`, `Edge Transit`) and discovered resources on a cloud account named `prod-platform`. I did that so the import and conflict views had something to show. It is a recording of demo data.

A real AWS or GCP account is a different setup. AWS uses an IAM role or the standalone agent. GCP uses Application Default Credentials with the server collector. That lives in [docs/DISCOVERY.md](https://github.com/BadgerOps/cloudpam/blob/master/docs/DISCOVERY.md).

![Seeded cloud accounts](/images/cloudpam/accounts.png)

On **Cloud Discovery**, choose `prod-platform`, select the resources, and click **Preview Import** before anything becomes a pool. The preview marks each row importable, conflict, blocked, or link-only.

![Resources selected for import](/images/cloudpam/discovery-import-selection.png)

![Import preview](/images/cloudpam/discovery-import-preview.png)

**Apply import** writes the rows that are clear. The clip does that against the seed and stops on the import summary.

![Selecting seeded resources and applying the import](/images/cloudpam/discovery-import.gif)

Network then shows managed pools and discovered objects in one hierarchy. Conflicts is where duplicate CIDRs and broken nesting show up. The seed is built to trip those cases.

![Merged network hierarchy](/images/cloudpam/discovery-network-hierarchy.png)

![Conflict review](/images/cloudpam/discovery-network-conflicts.png)

Drift Detection is the next page. Run a detection pass and you get the list: unmanaged resources, CIDR mismatches, orphaned discovered pools. **Resolve** and **Ignore** mark the item. There is no automatic reconciliation that edits the pool or the cloud for you.

## Known limits

* **IPv4 only.** IPv6 addresses are rejected for managed pools. GCP discovery can still ingest an IPv6 address, and that address cannot become a pool.
* **Azure is selectable and cannot sync.** The account form accepts Azure. There is no Azure collector, so a sync fails with `no collector registered for provider`. You can still track an Azure account and its pools by hand.
* **Single-tenant.** One appliance, one organization. Tenant isolation is not enforced.
* **Analysis is an API.** Gap, fragmentation, and compliance reports are `POST /api/v1/analysis` and the routes under it. The UI has no analysis page.

## If you want to try it

The repo is [github.com/BadgerOps/cloudpam](https://github.com/BadgerOps/cloudpam). Production options — Compose, Cloud Run, ECS, Kubernetes — are in the [deployment guide](https://github.com/BadgerOps/cloudpam/blob/master/docs/DEPLOYMENT.md).

If the quickstart misbehaves, or discovery against a real account does not match the docs, [file an issue](https://github.com/BadgerOps/cloudpam/issues). Include the provider, the error, and what you expected the pool tree to do.

All for now,

-BadgerOps
