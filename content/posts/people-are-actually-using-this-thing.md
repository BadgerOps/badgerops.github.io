---
title: "People Are Actually Using This Thing"
slug: "people-are-actually-using-this-thing"
date: 2026-10-28T12:35:00Z
lastmod: 2026-10-28T12:35:00Z
draft: false
description: "The UniFi provider went from 153 downloads in May to about 23,600. Here is what broke once people started running it against controllers I do not own."
topics: ["Homelab", "Open Source", "Terraform", "UniFi"]
aliases: ["/2026/10/28/people-are-actually-using-this-thing/"]
migration_source: ghost
---

*(Or, how my homelab provider turned into actual open source maintenance)*

Back in May I [wrote about shipping a UniFi Terraform provider](/why-i-wrote-a-new-terraform-provider-for-unifi/). It had been out for about a week and the Terraform Registry showed 153 downloads. I was pretty happy with that. The provider worked against my controller, a couple of folks in Matrix had kicked the tires, and I could finally manage my firewall rules without clicking through the Network UI.

I checked the Registry this week.

23,600 downloads.

So. People are actually using this thing.

That is extremely cool, and maybe a little terrifying. Somewhere along the way my homelab project turned into a maintenance job. People have controller versions I do not have, WiFi configurations I had never tried, Site Manager connector URLs, OpenTofu packaging requirements, and a much higher tolerance than I do for filing useful bug reports.

The provider is better for it. Quite a bit better, actually.

## First: thank you

I want to call out a few people before getting into the code:

* [thewhit](https://github.com/thewhit) added Enterprise WiFi, WPA2 PPSK, and a configurable HTTP timeout. Those were substantial additions, complete with tests and examples.
* [dreh23](https://github.com/dreh23) fixed the Site Manager cloud connector URL handling and found GNU-specific `awk` hiding in the documentation scripts.
* [michaelpeterswa](https://github.com/michaelpeterswa) filed the kind of bug reports maintainers dream about: config, output, controller behavior, and enough detail to reproduce the problem.
* [hectellian](https://github.com/hectellian) helped with OpenTofu Registry and GPG signing support.

There have been plenty of other issues, comments, and test results along the way. Thank you for taking the time to send them. Every controller behaves slightly differently, and I only own so many UniFi devices. (Still too many, according to my wife.)

## The provider config grew a timeout

One of the first community fixes was delightfully practical. A UniFi Network application can stop answering the API for a few minutes while it reprovisions devices after a WiFi change. The controller stays up, the port stays open, and the provider sits there until the hardcoded 30 second HTTP timeout expires.

You end up with this:

```text
context deadline exceeded (Client.Timeout exceeded while awaiting headers)
```

The controller may have accepted the change already, which makes the next plan extra fun.

Wilson added `request_timeout_seconds`, so my provider configuration now looks more like this:

```hcl
terraform {
  required_providers {
    unifi = {
      source  = "badgerops/unifi"
      version = "~> 0.5"
    }
  }
}

provider "unifi" {
  api_url        = var.unifi_api_url
  api_key        = var.unifi_api_key
  allow_insecure = false

  # Some WiFi changes make the Network application disappear for a while.
  request_timeout_seconds = 300
}
```

The implementation passes that value down to the normal Go HTTP client:

```go
requestTimeout := config.RequestTimeout
if requestTimeout == 0 {
	requestTimeout = DefaultRequestTimeout
}

httpClient := &http.Client{
	Timeout:   requestTimeout,
	Transport: transport,
}
```

Simple fix. Very useful. Exactly the sort of thing I would not have noticed while testing against my own controller on my own network.

## Enterprise WiFi and PPSK

The big feature contribution was Enterprise WiFi and private pre-shared keys. I had neither in my original setup, so they were very much outside the first version of the provider.

Enterprise WiFi looks up an existing RADIUS profile and references it from the broadcast:

```hcl
data "unifi_radius_profile" "corp" {
  site_id = data.unifi_site.main.id
  name    = "Corporate RADIUS"
}

resource "unifi_wifi_broadcast" "corp" {
  site_id                                 = data.unifi_site.main.id
  type                                    = "STANDARD"
  name                                    = "staff-wpa2-enterprise"
  enabled                                 = true
  client_isolation_enabled                = false
  hide_name                               = false
  uapsd_enabled                           = true
  multicast_to_unicast_conversion_enabled = false
  broadcasting_frequencies_ghz            = [2.4, 5]
  advertise_device_name                   = false
  arp_proxy_enabled                       = false
  band_steering_enabled                   = true
  bss_transition_enabled                  = true

  network = { type = "NATIVE" }

  security_configuration = {
    type = "WPA2_ENTERPRISE"
    radius_configuration = {
      profile_id = data.unifi_radius_profile.corp.id
      nas_id     = { type = "DERIVED", source = "DEVICE_NAME" }
    }
    coa_enabled          = true
    fast_roaming_enabled = true
    pmf_mode             = "OPTIONAL"
  }
}
```

PPSK is a little stranger. Each key carries its own network assignment, and the controller rejects a broadcast-level `network` when `preshared_keys` is present. That required making `network` optional in the Terraform schema, then validating the combinations during plan.

Here is the working shape:

```hcl
variable "iot_local_psk" {
  type      = string
  sensitive = true
}

variable "iot_internet_psk" {
  type      = string
  sensitive = true
}

resource "unifi_wifi_broadcast" "iot_ppsk" {
  site_id                                 = data.unifi_site.main.id
  type                                    = "STANDARD"
  name                                    = "iot-ppsk"
  enabled                                 = true
  client_isolation_enabled                = true
  hide_name                               = false
  uapsd_enabled                           = true
  multicast_to_unicast_conversion_enabled = false
  broadcasting_frequencies_ghz            = [2.4, 5]
  advertise_device_name                   = false
  arp_proxy_enabled                       = false
  band_steering_enabled                   = true
  bss_transition_enabled                  = true

  security_configuration = {
    type                 = "WPA2_PERSONAL"
    fast_roaming_enabled = true
    preshared_keys = [
      {
        passphrase = var.iot_local_psk
        network = {
          type       = "SPECIFIC"
          network_id = unifi_network.trusted.id
        }
      },
      {
        passphrase = var.iot_internet_psk
        network    = { type = "NATIVE" }
      }
    ]
  }
}
```

UniFi may omit PPSK passphrases when it returns the broadcast. The provider keeps the known secret from state during refresh. Imports need the passphrases supplied in configuration, because I have not yet figured out how to recover a password the controller refuses to return. (Shocking, I know.)

## 2.4 GHz is apparently a difficult number

Michael opened an issue where a WiFi broadcast planned an update immediately after a successful apply. The relevant configuration was about as exciting as you would expect:

```hcl
broadcasting_frequencies_ghz = [2.4, 5]
```

The config said `2.4`. The controller returned `2.4`. Their float64 representations differed just enough for Terraform's set comparison to see a change every single time.

Computers were a mistake.

The fix canonicalizes values near the three bands UniFi supports:

```go
var knownWifiFrequenciesGHz = []float64{2.4, 5, 6}

const wifiFrequencyMatchEpsilon = 0.05

func canonicalizeWifiFrequency(value float64) (float64, bool) {
	for _, known := range knownWifiFrequenciesGHz {
		if math.Abs(value-known) < wifiFrequencyMatchEpsilon {
			return known, true
		}
	}
	return value, false
}
```

There is also a set plan modifier that keeps the existing state when config and state identify the same bands:

```go
func (m wifiFrequenciesPlanModifier) PlanModifySet(
	ctx context.Context,
	request planmodifier.SetRequest,
	response *planmodifier.SetResponse,
) {
	if request.ConfigValue.IsNull() || request.ConfigValue.IsUnknown() ||
		request.StateValue.IsNull() || request.StateValue.IsUnknown() {
		return
	}

	var configValues []float64
	var stateValues []float64

	response.Diagnostics.Append(
		request.ConfigValue.ElementsAs(ctx, &configValues, false)...,
	)
	response.Diagnostics.Append(
		request.StateValue.ElementsAs(ctx, &stateValues, false)...,
	)

	if response.Diagnostics.HasError() {
		return
	}

	if wifiFrequenciesSemanticallyEqual(configValues, stateValues) {
		response.PlanValue = request.StateValue
	}
}
```

And, because I do not want to debug this twice, the regression test applies the config, plans again, imports it, and plans one more time:

```go
Steps: []resource.TestStep{
	{Config: config},
	{Config: config, PlanOnly: true},
	{
		ResourceName:      "unifi_wifi_broadcast.test",
		ImportState:       true,
		ImportStateVerify: true,
	},
	{Config: config, PlanOnly: true},
}
```

That one issue produced a small pile of tests and a much better understanding of how Terraform Plugin Framework compares sets of numbers.

## The boolean that came back as `false`

The firewall bug was another controller round-trip surprise. A user left `destination_filter.port_filter.match_opposite` unset. Terraform represented it as null. UniFi returned an explicit `false` after apply. Plugin Framework correctly complained that the provider had produced an inconsistent result.

The configuration can be perfectly reasonable without spelling out the default:

```hcl
destination_filter = {
  type = "NETWORK"
  network_ids = [unifi_network.apps.id]
  port_filter = {
    type  = "PORTS"
    ports = ["443"]
  }
}
```

The schema now supplies the same value UniFi returns:

```go
"match_opposite": schema.BoolAttribute{
	Optional: true,
	Computed: true,
	Default:  booldefault.StaticBool(false),
},
```

There are round-trip tests for null and explicit values now. This was another excellent bug report from Michael, and it was much faster to fix with a real configuration and the exact post-apply error attached.

## Site Manager has its own URL rules

Local consoles normally expose legacy Network endpoints below `/proxy/network/api`. The Site Manager cloud connector forwards directly into the Network application, so its legacy endpoints sit below `/api`.

For example:

```text
# Integration API base
https://api.ui.com/v1/connector/consoles/CONSOLE-ID/network/integration

# Legacy API base used by DHCP reservations and port forwards
https://api.ui.com/v1/connector/consoles/CONSOLE-ID/network/api
```

My original URL normalization added `/proxy/network/api` everywhere. The connector answered that with a 404. Johannes tested the real paths against a live console and sent the fix, including cases for the base URL, the `/integration` URL, and a trailing slash:

```go
var siteManagerConnectorRE = regexp.MustCompile(
	`^(.*/v1/connector/consoles/[^/]+/network)(?:/integration)?$`,
)

func siteManagerConnectorPath(path string) (string, bool) {
	match := siteManagerConnectorRE.FindStringSubmatch(path)
	if match == nil {
		return "", false
	}
	return match[1], true
}
```

This is why community testing matters. I do not use the cloud connector for my normal workflow, so I could have happily kept shipping a broken path forever.

## My `awk` worked, of course

The documentation generator reads the current provider version from `CHANGELOG.md`. I used the three-argument form of `match()`, which works with GNU awk. GitHub Actions has GNU awk. My workstation has GNU awk. Everything looked fine.

Then somebody ran it on macOS.

The portable version is less clever and works everywhere we care about:

```awk
/^## \[[0-9]+\.[0-9]+\.[0-9]+\]/ {
  version = $0
  sub(/^## \[/, "", version)
  sub(/\].*$/, "", version)
  print version
  exit
}
```

Wilson fixed the first script. Johannes found the same GNU-ism in two more release scripts and fixed those too. Apparently copying a bad idea makes it portable only in the sense that it breaks in more places.

## Documentation became part of the work

The Registry page used to be mostly generated schema. That gets a resource published. It does not help much when somebody is staring at a controller URL and wondering what belongs in `api_url`.

The repo now has guides for getting started, zone-based firewall quirks, importing existing configuration, and moving from the older UniFi providers. There is also a complete example under `examples/basic-site` with networks, WiFi, firewall zones, policy ordering, DNS, and ACLs.

I even managed to break the guide links in release `0.5.4`. Terraform Registry serves the provider overview from a path ending in `/docs` without a trailing slash. Links like `./guides/getting-started` resolved one directory higher and returned 404.

Release `0.5.5` exists because URLs are hard.

## Sharp edges, because UniFi is still UniFi

Here is the current list I would want somebody to read before trying the provider against an important controller:

* Zone-based firewall must already be enabled in the Network UI.
* WiFi reprovisioning can leave the API unresponsive for minutes. Raise `request_timeout_seconds` when needed.
* PPSK passphrases may be absent from controller responses. Supply them in configuration after an import.
* DHCP reservations and port forwards use carefully contained legacy API paths because the Integration API does not expose those writes.
* Controller versions disagree about fields, defaults, and response shapes. Include the Network version when filing an issue.
* A few useful Network UI knobs still need resources, including device naming, switch port overrides, and AP groups/device tags.

There are also open bugs where I need to model the API more carefully. I am taking the time to understand those. A `lifecycle { ignore_changes = [...] }` block would hide the symptom and leave the controller behavior waiting for somebody else.

## What is next

For now I am going to keep working through the issues, keep adding the real controller cases to the test suite, and keep expanding coverage where the API supports it.

If you are using the provider and something breaks, please file an issue with the Terraform config, the controller version, and the plan/apply output. Redact the secrets, obviously. That combination usually saves me an hour of guessing.

Also, if it works, I would not mind hearing that too. Maintainers mostly hear about the exciting failures.

Registry: [registry.terraform.io/providers/BadgerOps/unifi](https://registry.terraform.io/providers/BadgerOps/unifi/latest)

GitHub: [github.com/BadgerOps/terraform-provider-unifi](https://github.com/BadgerOps/terraform-provider-unifi)

All for now,

-BadgerOps
