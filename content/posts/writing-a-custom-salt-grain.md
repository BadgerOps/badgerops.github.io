+++
title = "Writing a custom Salt Grain"
date = "2017-04-23T22:55:05Z"
draft = false
+++

In this blog post, we'll talk about writing a custom Salt Grain, and why you might want to.

At my company we had some VM's that had multiple (private) IPv4 addresses set on them, and this broke [Consul](https://www.consul.io/) as it can only bind to a [single Private IPv4 address](https://www.consul.io/docs/agent/options.html#_bind).

You might say "Hey BadgerOps! You can use the grain `fqdn_ip4` to get this IP!" and thus bask in your incredibly profound knowledge of Salt Grains. However, I'd rebut: "Yes, but this assumes that whoever set up that VM configured /etc/hosts properly" - And while I'd love to think that the individual who set the server up did it correctly, we live in the real world and we all know that often things aren't configured properly.

This knowledge coupled with my excellent grasp of Murphys Law gave me the idea to do the following: Write a custom grain for finding the 'real' IPv4 address on a server. (I consider the IPv4 address that is associated with the default route to be the 'real' address)

As is my custom, I'll first refer you to [Documentation!](https://docs.saltstack.com/en/latest/topics/grains/#writing-grains) and state "it's really good, you should read it!" - And then I'll follow that with an example of how to do the thing.

---
##### Example of how to do the thing:
If you're using [salt-workspace](https://github.com/BadgerOps/salt-workspace) you can checkout the 'custom_grain' branch to see the following.

Create a [directory](https://github.com/BadgerOps/salt-workspace/blob/custom_grain/salt/_grains) underneath 'Salt' called `_grains` (but then you already knew this, because you read the [Documentation!](https://docs.saltstack.com/en/latest/topics/grains/#writing-grains) right?)

[This](https://github.com/BadgerOps/salt-workspace/blob/custom_grain/salt/_grains/primary_ip4.py) is a (very simple) example of the contents of the primary_ipv4 Grain:

```python
#!/usr/bin/env python
import subprocess

def getipv4():
    grains = {}
    ipv4 = subprocess.check_output("ip route get 1 | awk '{print $NF;exit}'", shell=True)
    grains['primary_ipv4'] = ipv4
    return grains
```
You'll create a file at salt/\_grains/primary\_ipv4.py and put the contents of the example in there as seen [here](https://github.com/BadgerOps/salt-workspace/blob/custom_grain/salt/_grains/primary_ip4.py).


---

##### Example of how to test the thing

Assuming you've got the [salt-workspace](https://blog.badgerops.net/2017/04/10/getting-started-with-salt-workspace/) set up, you can start up the saltmaster and the linux-1 VM: `vagrant up saltmaster linux-1`

Then, ensure you run `make` to build the salt structure and move it to ./dist/ which is sync'd to the saltmaster VM.

Log into the saltmaster and run `salt \* saltutil.sync_grains` which will synchronize the grains across all nodes. You should see the following output:

```bash
[vagrant@saltmaster ~]$ sudo salt \* saltutil.sync_grains
saltmaster:
    - grains.primary_ip4
linux-1:
    - grains.primary_ip4
```

Then you should be able to run `salt \* grains.get primary_ipv4` as seen below:

```bash
[vagrant@saltmaster ~]$ sudo salt \* grains.get primary_ipv4
saltmaster:
    10.0.2.15
linux-1:
    10.1.2.15
```

Thats it! Now, this example is very simplistic, and it obviously won't work with Windows minions (although the [win_ip](https://docs.saltstack.com/en/latest/ref/modules/all/salt.modules.win_ip.html) module should be pretty useful here) but its a good initial example of what you can do to solve an issue with custom grains.

Thanks for reading!

-BadgerOps