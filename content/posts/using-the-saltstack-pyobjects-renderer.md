+++
title = "Using the Saltstack pyobjects renderer"
date = "2017-09-12T14:49:27Z"
draft = false
+++

I've been using the default yaml/jinja combo for most of the time that I've used Saltstack, which can get really frustrating when you're moving away from simple templating and actually starting to develop code in jinja. The biggest issue here: jinja is a *templating* engine, not a programming language. It is not easy to debug, and frankly, it is incredibly ugly!

Enter [pyobjects](https://docs.saltstack.com/en/latest/ref/renderers/all/salt.renderers.pyobjects.html#module-salt.renderers.pyobjects) - one of the most pythonic renderers available, providing the power and flexibility of python to your configurations! It doesn't hurt that SaltStack is written in python, making this renderer very simple to implement. 

UPDATE: [here](https://github.com/BadgerOps/salt-workspace/tree/feature/pyobjects_host_example) is a branch in [salt-workspace](__GHOST_URL__/2017/04/10/getting-started-with-salt-workspace/) that shows example code that you can download and run yourself!

----

Initially, I created a template for my `/etc/hosts` file with jinja:
```
# set local ip/hostname by looking at 2 grains, grabbing the ip associated with eth0 (returned as a list, so we have to pull [0])
# also grabbing the hostname from the 'host' grain. We set this here instead of using salt-mine just in case the salt-mine cache gets into a bad state
# we don't want to break local resolving.
{{ grains['ip4_interfaces'][interface][0] }} {{ grains['host'] }}

# Salt-Mine creates a dictionary with hostnames and IP's. Here we iterate through all the IP's/hosts in salt-mine and set them
# We'll filter out our local hostname so we don't re-set it. Salt-Mine returns the dictionary based on searching either hostname or grain
# in this example we search for '*' aka all salt minions. We could easily split this out to only do prod or dev, etc.

{% for hostname, ip in salt['mine.get']('*', 'network.ip_addrs')|dictsort() -%}
{% if hostname != grains['host'] -%}
{{ ip[0] }} {{ hostname }}
{% endif -%}
{% endfor %}
```

What we do here with [salt-mine](https://docs.saltstack.com/en/latest/topics/mine/) is have the minions register their IP addresses using a pillar declaration:
```
mine_functions:
  # we build our /etc/hosts file off the private IP's
  network.ip_addrs:
    interface: eth0
```
This allows us to do a mine lookup `salt['mine.get']('*', 'network.ip_addrs')` which would return a dictionary that looks something like this:

```
>>> salt('*', 'mine.get', ('*', 'network.ip_addrs'))
{'saltmaster': {'saltmaster': ['192.168.50.4'], 'linux-1': ['192.168.50.5']}, 'linux-1': {'saltmaster': ['192.168.50.4'], 'linux-1': ['192.168.50.5']}}
```

breaking this down: `salt('*'` is functionally the same as `salt '*'` meaning we run the command on all minions. Then we have the `mine.get` function, where we pass in `('*', 'network.ip_addrs')` as arguments. This mean's we're requesting network.ip_addrs from all the minions. As usual, if you [read the documentation](https://docs.saltstack.com/en/latest/topics/mine/#example) you should have a better understanding of how to get information back out of salt-mine.

We could technically run that against a single machine, say `saltmaster` for example:

```
>>> salt('saltmaster', 'mine.get', ('*', 'network.ip_addrs'))
{'saltmaster': {'saltmaster': ['192.168.50.4'], 'linux-1': ['192.168.50.5']}
```
we'd just get a single dictionary back with the same values (assuming they all registered correctly)

If you were running this from the command line, it would look like:

```
salt 'saltmaster' mine.get '*' network.ip_addrs
```
or:

```
salt 'saltmaster' mine.get 'saltmaster' network.ip_addrs
```

Back to the `/etc/hosts` template file. Jinja is kind of tricky to work with, and is really difficult to debug, which is something I ran into when working with this project.

I decided to give the `#!pyobjects` renderer a shot, and was pleased to find it was really easy to mock out using the [idle](https://docs.python.org/3/tutorial/interpreter.html#) interpreter.

Here is the file I ended up with, which enabled me to dynamically add/remove hosts using straight up python syntax. I've added a bunch of documentation so hopefully it should be fairly obvious what is going on, but feel free to add a comment or feel free to reach out `@badgerops` on the twitters.

```
#!pyobjects

# the purpose of this builder is to create a hostfile in the following format:
# 1.2.3.4    hostname    hostname.domain
# we have a couple custom grains that register the domain, and the IP of minions
# we'll use salt-mine to grab these grains and use them to build the host file

# first, set the network dictionary (key/value stores) from information stored in salt-mine
# the syntax is mine('host or grain lookup' 'mine_function')
# in this case we're matching on '*' for all hosts
# example of the dictionary are as follows:
# network = {'saltmaster': ['192.168.50.4'], 'linux-1': ['192.168.50.5']}
# first: ensure the mine is up-to-date
__salt__['mine.update']('*')

# create a dictionary 'network' with the key/values we get from salt-mine. 
network = mine('*', 'network.ip_addrs')

for hostname in network.keys():
    hostname_short = hostname.split('.')[0] # set the non-fqdn hostname
    domain = hostname.split('.')[1] # pull out the domain, does not include .com
    # finally, build the hostfile
    Host.present(
      hostname_short,
      ip=network[hostname], # network.ip_addrs returns a list of IP's, even if its only 1 addr
      names=[
            '%s.%s.com' % (hostname_short, domain), # hostname.domain aka FQDN
            '%s' % hostname_short # just hostname
            ]
    )

```

Hope this was helpful!

-BadgerOps