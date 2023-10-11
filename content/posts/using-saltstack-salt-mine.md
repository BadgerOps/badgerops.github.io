+++
title = "Using Saltstack salt-mine"
date = "2017-09-12T15:09:18Z"
draft = false
+++

##### Edit in March of 2020: Hello! This is one of my more popular posts even in 2020, but I'm curious if you came across this post looking for slightly different information than is presented. If so, shoot me a message on twitter: `@badgerops` or send an email to `blog@badgerops.net` with what you're looking for so I can update this post! Thank you.
-----------------------------------
Today we're going to talk about using salt-mine to help gather information from salt minions. This is a sister post to [Using the #!pyobjects renderer](__GHOST_URL__/2018/02/09/using-the-saltstack-pyobjects-renderer/) as we're consuming mine data to create a custom hosts file.

In this example, we're going to register our IP addresses that match a specific IP address pattern, or [CIDR](https://en.wikipedia.org/wiki/Classless_Inter-Domain_Routing) using [salt-mine](https://docs.saltstack.com/en/latest/topics/mine/)
 
 using a pillar declaration as seen here: (NOTE: this is explained in great detail [in the documentation](https://docs.saltstack.com/en/latest/topics/mine/)
```
mine_functions:
  # we build our /etc/hosts file off the 'private/non routable' IP's
  network.ip_addrs:
    cidr: 192.168.0.0/16
```
This allows us to do a mine lookup `salt['mine.get']('*', 'network.ip_addrs')` which would return a dictionary that looks something like this:

```
>>> salt('*', 'mine.get', ('*', 'network.ip_addrs'))
{'saltmaster': {'saltmaster': ['192.168.50.4'], 'linux-1': ['192.168.50.5']}, 'linux-1': {'saltmaster': ['192.168.50.4'], 'linux-1': ['192.168.50.5']}}
```

breaking this down: `salt('*'` is functionally the same as `salt '*'` meaning we run the command on all minions. Then we have the `mine.get` function, where we pass in `('*', 'network.ip_addrs')` as arguments. This mean's we're requesting network.ip_addrs from all the minions. As usual, if you [read the documentation](https://docs.saltstack.com/en/latest/topics/mine/#example) you should have a better understanding of how to get information back out of salt-mine.

We could omit the cidr to register all IP's [except loopback](https://docs.saltstack.com/en/latest/ref/modules/all/salt.modules.network.html#salt.modules.network.ipaddrs) but that would be functionally equivalent to `salt-call grains.get network.ipaddrs` (to be clear, that is exactly what is happening under the hood, we're just storing that return in the salt-mine)

There are many other things we could store in the salt-mine, essentially any grain you can look up, or set, can be stored in the salt-mine, one huge reason for this is you can look up data about one minion from another minion, which is something that you cannot do with pillar or grains (they're minion specific), this is why I chose to use salt-mine to create my custom /etc/hosts file.

Hope this brief post was helpful, feel free to comment or hit up `@badgerops` on twitter!

-BadgerOps
