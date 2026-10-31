---
title: "Introducing CloudPAM: IPAM that knows about your cloud"
slug: "introducing-cloudpam"
date: 2026-10-31T12:00:00Z
draft: true
description: "CloudPAM keeps planned address pools and discovered AWS and GCP resources in the same place, so overlaps and drift show up before deployment."
topics: ["networking", "IPAM", "AWS", "GCP", "open-source", "tools"]
---

I have lost count of the spreadsheets named `ip-plan-FINAL-v7.xlsx`.

The spreadsheet says `10.20.0.0/16` belongs to production. Meanwhile, a VPC in an account nobody added to the spreadsheet is already using `10.20.4.0/24`. Everything looks fine until two teams try to connect their networks and discover that they picked the same address space.

That gap between the plan and the cloud is why I wrote [CloudPAM](https://github.com/BadgerOps/cloudpam). I wanted one place to keep the ranges we intended to use, the resources the cloud providers say actually exist, and the differences between the two.

## So, what is CloudPAM?

CloudPAM is an IP address management tool for AWS and GCP environments. You build a hierarchy of managed pools, then discovery records what the cloud APIs return without adding those resources to the plan.

The server is written in Go, with the React UI embedded in the same binary. The container packages that binary in a minimal runtime image. PostgreSQL is the production store, SQLite works for a single-node deployment, and the development server can run entirely in memory.

Today, CloudPAM can:

* Build hierarchical address pools and reject child ranges outside their parent or overlapping sibling ranges.
* Discover VPCs, subnets, Elastic IPs, and AWS Organizations accounts. The GCP collector handles networks, subnetworks, and external IPs.
* Compare discovered resources with managed pools and record whether you resolved or ignored each drift item.
* Lay out a hierarchy in the Schema Planner, check it for conflicts, and apply it.
* Authenticate local users or use OIDC, with sessions, API keys, and custom roles.
* Manage pools and cloud accounts through the Terraform provider.

The AWS discovery agent is a separate binary for accounts where running discovery from the CloudPAM server does not make sense. GCP discovery currently runs from the server using Application Default Credentials. More on that below.

## Run it locally

You do not need an AWS or GCP account for this part. The development server uses an in-memory store, so it is a safe way to poke at the pool model without setting up a database.

```bash
git clone https://github.com/BadgerOps/cloudpam.git
cd cloudpam
nix develop
just ui-build
just dev
```

Do not skip `just ui-build` on a fresh clone. The Go binary embeds whatever is under `web/dist`, and the repository only carries a placeholder page. `just ui-build` compiles the React application before `just dev` starts the server at [http://localhost:8080](http://localhost:8080).

If you do not use Just, the server command is:

```bash
DEV_MODE=1 go run ./cmd/cloudpam
```

That still needs the UI build first. Also, the data disappears when you stop the process. That is useful for this walkthrough and less useful for anything you care about keeping.

The first visit gives you a setup form. Create the initial admin user, sign in, and CloudPAM drops you on the Address Pools page.

<img src="/images/cloudpam/setup-login.gif" alt="First-boot setup and sign-in" width="1280" height="720" loading="lazy" decoding="async">

Start with a root pool. I used `Corp Supernet` with `10.0.0.0/8` and no parent. Then create a second pool with a CIDR inside that range and select `Corp Supernet` as its parent.

<img src="/images/cloudpam/pools.png" alt="Address pools hierarchy in CloudPAM" width="2560" height="1800" loading="lazy" decoding="async">

The clip below uses my seeded demo data and adds `Demo App Tier` (`10.20.10.0/24`) below `Prod East VPC`. One small UI oddity: the table starts by showing root pools. Searching for the new child brings it into the table after it is created.

<img src="/images/cloudpam/create-pool.gif" alt="Creating a child pool" width="1280" height="720" loading="lazy" decoding="async">

Allocated Blocks shows the address space you meant to hand out. Cloud discovery stays separate, which is important because finding a subnet in AWS should not automatically make that subnet part of your IP plan.

<img src="/images/cloudpam/blocks.png" alt="Allocated blocks in CloudPAM" width="2560" height="1800" loading="lazy" decoding="async">

## Managing pools with Terraform

If you would rather keep the plan in code, the Terraform provider currently manages pools and cloud accounts. Create an API key under **Administration > API Keys** (`/config/api-keys`), then configure the provider with the endpoint and key:

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

You can also set `CLOUDPAM_ENDPOINT` and `CLOUDPAM_API_KEY` instead of putting those values in the provider block. CloudPAM keys start with `cpam_`.

The other v1 resource is `cloudpam_account`. Discovery runs, drift items, users, and other operational state stay outside Terraform.

## Trying cloud discovery without cloud credentials

The rest of the screenshots use a throwaway server with seeded data. I loaded managed pools named `Corp Supernet`, `Prod East VPC`, and `Edge Transit`, along with discovered resources attached to a fake account named `prod-platform`. Nothing in this walkthrough contacted a real AWS or GCP account.

A real AWS account uses the default credential chain, an IAM role, or the standalone agent. GCP uses Application Default Credentials on the CloudPAM server. The setup details and required permissions are in [docs/DISCOVERY.md](https://github.com/BadgerOps/cloudpam/blob/master/docs/DISCOVERY.md).

<img src="/images/cloudpam/accounts.png" alt="Seeded cloud accounts" width="2560" height="1800" loading="lazy" decoding="async">

On **Cloud Discovery**, select the account and the resources you want to import, then click **Preview Import**. Nothing becomes a managed pool until you apply that preview.

<img src="/images/cloudpam/discovery-import-selection.png" alt="Resources selected for import" width="2560" height="2400" loading="lazy" decoding="async">

The preview labels each resource as importable, conflicting, blocked, or link-only. This is the part I care about: you get to see what CloudPAM plans to do before it changes the managed pool tree.

<img src="/images/cloudpam/discovery-import-preview.png" alt="Import preview" width="2048" height="856" loading="lazy" decoding="async">

**Apply import** writes the rows that passed the checks. This clip runs through the whole selection, preview, and import against the seeded account:

<img src="/images/cloudpam/discovery-import.gif" alt="Selecting seeded resources and applying the import" width="1280" height="720" loading="lazy" decoding="async">

After the import, the Network tab puts managed pools and discovered objects into one hierarchy. The Conflicts view calls out duplicate CIDRs and broken nesting instead of leaving you to find them during a routing change.

<img src="/images/cloudpam/discovery-network-hierarchy.png" alt="Merged network hierarchy" width="2560" height="3400" loading="lazy" decoding="async">

<img src="/images/cloudpam/discovery-network-conflicts.png" alt="Conflict review" width="2560" height="4600" loading="lazy" decoding="async">

Drift Detection compares the two sides again and reports unmanaged resources, CIDR mismatches, and discovered pools that no longer have a matching resource. **Resolve** and **Ignore** record your decision. CloudPAM does not edit the cloud resource or managed pool behind your back.

## Current sharp edges

I would rather write these down than pretend the project is finished:

* Managed pools are IPv4 only. GCP discovery can ingest an IPv6 address, but CloudPAM cannot turn it into a managed pool.
* The account form accepts Azure, but there is no Azure collector. A sync fails with `no collector registered for provider`; you can only track the account and its pools by hand.
* CloudPAM is a single-tenant appliance. The database contains some organization scaffolding, but it does not enforce tenant isolation.
* Gap and fragmentation results appear in the pool detail panel. Compliance and the full analysis report are still API-only, and there is no dedicated Analysis page.

There are more details in the repository's [current status document](https://github.com/BadgerOps/cloudpam/blob/master/docs/CURRENT_STATUS.md). That file is deliberately less optimistic than a feature list.

## Give it a try

The repository is [github.com/BadgerOps/cloudpam](https://github.com/BadgerOps/cloudpam). The [deployment guide](https://github.com/BadgerOps/cloudpam/blob/master/docs/DEPLOYMENT.md) covers Compose, Cloud Run, ECS, and Kubernetes when you are ready to keep the data.

If the quickstart breaks, or discovery does something different from what the documentation says, please [file an issue](https://github.com/BadgerOps/cloudpam/issues). Include the provider, the error, and what you expected to happen. That will save me a good amount of guessing.

Hopefully this is useful to somebody else dealing with one too many cloud accounts and one too many IP planning spreadsheets.

Thanks for reading!

-BadgerOps
