+++
title = "Using the Saltstack pyobjects renderer"
date = "2017-09-12T14:49:27Z"
draft = false
+++

<!--kg-card-begin: markdown--><p>I've been using the default yaml/jinja combo for most of the time that I've used Saltstack, which can get really frustrating when you're moving away from simple templating and actually starting to develop code in jinja. The biggest issue here: jinja is a <em>templating</em> engine, not a programming language. It is not easy to debug, and frankly, it is incredibly ugly!</p>
<p>Enter <a href="https://docs.saltstack.com/en/latest/ref/renderers/all/salt.renderers.pyobjects.html#module-salt.renderers.pyobjects">pyobjects</a> - one of the most pythonic renderers available, providing the power and flexibility of python to your configurations! It doesn't hurt that SaltStack is written in python, making this renderer very simple to implement.</p>
<p>UPDATE: <a href="https://github.com/BadgerOps/salt-workspace/tree/feature/pyobjects_host_example">here</a> is a branch in <a href="__GHOST_URL__/2017/04/10/getting-started-with-salt-workspace/">salt-workspace</a> that shows example code that you can download and run yourself!</p>
<hr>
<p>Initially, I created a template for my <code>/etc/hosts</code> file with jinja:</p>
<pre><code># set local ip/hostname by looking at 2 grains, grabbing the ip associated with eth0 (returned as a list, so we have to pull [0])
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
</code></pre>
<p>What we do here with <a href="https://docs.saltstack.com/en/latest/topics/mine/">salt-mine</a> is have the minions register their IP addresses using a pillar declaration:</p>
<pre><code>mine_functions:
  # we build our /etc/hosts file off the private IP's
  network.ip_addrs:
    interface: eth0
</code></pre>
<p>This allows us to do a mine lookup <code>salt['mine.get']('*', 'network.ip_addrs')</code> which would return a dictionary that looks something like this:</p>
<pre><code>&gt;&gt;&gt; salt('*', 'mine.get', ('*', 'network.ip_addrs'))
{'saltmaster': {'saltmaster': ['192.168.50.4'], 'linux-1': ['192.168.50.5']}, 'linux-1': {'saltmaster': ['192.168.50.4'], 'linux-1': ['192.168.50.5']}}
</code></pre>
<p>breaking this down: <code>salt('*'</code> is functionally the same as <code>salt '*'</code> meaning we run the command on all minions. Then we have the <code>mine.get</code> function, where we pass in <code>('*', 'network.ip_addrs')</code> as arguments. This mean's we're requesting network.ip_addrs from all the minions. As usual, if you <a href="https://docs.saltstack.com/en/latest/topics/mine/#example">read the documentation</a> you should have a better understanding of how to get information back out of salt-mine.</p>
<p>We could technically run that against a single machine, say <code>saltmaster</code> for example:</p>
<pre><code>&gt;&gt;&gt; salt('saltmaster', 'mine.get', ('*', 'network.ip_addrs'))
{'saltmaster': {'saltmaster': ['192.168.50.4'], 'linux-1': ['192.168.50.5']}
</code></pre>
<p>we'd just get a single dictionary back with the same values (assuming they all registered correctly)</p>
<p>If you were running this from the command line, it would look like:</p>
<pre><code>salt 'saltmaster' mine.get '*' network.ip_addrs
</code></pre>
<p>or:</p>
<pre><code>salt 'saltmaster' mine.get 'saltmaster' network.ip_addrs
</code></pre>
<p>Back to the <code>/etc/hosts</code> template file. Jinja is kind of tricky to work with, and is really difficult to debug, which is something I ran into when working with this project.</p>
<p>I decided to give the <code>#!pyobjects</code> renderer a shot, and was pleased to find it was really easy to mock out using the <a href="https://docs.python.org/3/tutorial/interpreter.html#">idle</a> interpreter.</p>
<p>Here is the file I ended up with, which enabled me to dynamically add/remove hosts using straight up python syntax. I've added a bunch of documentation so hopefully it should be fairly obvious what is going on, but feel free to add a comment or feel free to reach out <code>@badgerops</code> on the twitters.</p>
<pre><code>#!pyobjects

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

</code></pre>
<p>Hope this was helpful!</p>
<p>-BadgerOps</p>
<!--kg-card-end: markdown-->