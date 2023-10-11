+++
title = "Using Saltstack salt-mine"
date = "2017-09-12T15:09:18Z"
draft = false
+++

<!--kg-card-begin: markdown--><h5 id="editinmarchof2020hellothisisoneofmymorepopularpostsevenin2020butimcuriousifyoucameacrossthispostlookingforslightlydifferentinformationthanispresentedifsoshootmeamessageontwitterbadgeropsorsendanemailtoblogbadgeropsnetwithwhatyourelookingforsoicanupdatethispostthankyou">Edit in March of 2020: Hello! This is one of my more popular posts even in 2020, but I'm curious if you came across this post looking for slightly different information than is presented. If so, shoot me a message on twitter: <code>@badgerops</code> or send an email to <code>blog@badgerops.net</code> with what you're looking for so I can update this post! Thank you.</h5>
<hr>
<p>Today we're going to talk about using salt-mine to help gather information from salt minions. This is a sister post to <a href="__GHOST_URL__/2018/02/09/using-the-saltstack-pyobjects-renderer/">Using the #!pyobjects renderer</a> as we're consuming mine data to create a custom hosts file.</p>
<p>In this example, we're going to register our IP addresses that match a specific IP address pattern, or <a href="https://en.wikipedia.org/wiki/Classless_Inter-Domain_Routing">CIDR</a> using <a href="https://docs.saltstack.com/en/latest/topics/mine/">salt-mine</a></p>
<p>using a pillar declaration as seen here: (NOTE: this is explained in great detail <a href="https://docs.saltstack.com/en/latest/topics/mine/">in the documentation</a></p>
<pre><code>mine_functions:
  # we build our /etc/hosts file off the 'private/non routable' IP's
  network.ip_addrs:
    cidr: 192.168.0.0/16
</code></pre>
<p>This allows us to do a mine lookup <code>salt['mine.get']('*', 'network.ip_addrs')</code> which would return a dictionary that looks something like this:</p>
<pre><code>&gt;&gt;&gt; salt('*', 'mine.get', ('*', 'network.ip_addrs'))
{'saltmaster': {'saltmaster': ['192.168.50.4'], 'linux-1': ['192.168.50.5']}, 'linux-1': {'saltmaster': ['192.168.50.4'], 'linux-1': ['192.168.50.5']}}
</code></pre>
<p>breaking this down: <code>salt('*'</code> is functionally the same as <code>salt '*'</code> meaning we run the command on all minions. Then we have the <code>mine.get</code> function, where we pass in <code>('*', 'network.ip_addrs')</code> as arguments. This mean's we're requesting network.ip_addrs from all the minions. As usual, if you <a href="https://docs.saltstack.com/en/latest/topics/mine/#example">read the documentation</a> you should have a better understanding of how to get information back out of salt-mine.</p>
<p>We could omit the cidr to register all IP's <a href="https://docs.saltstack.com/en/latest/ref/modules/all/salt.modules.network.html#salt.modules.network.ipaddrs">except loopback</a> but that would be functionally equivalent to <code>salt-call grains.get network.ipaddrs</code> (to be clear, that is exactly what is happening under the hood, we're just storing that return in the salt-mine)</p>
<p>There are many other things we could store in the salt-mine, essentially any grain you can look up, or set, can be stored in the salt-mine, one huge reason for this is you can look up data about one minion from another minion, which is something that you cannot do with pillar or grains (they're minion specific), this is why I chose to use salt-mine to create my custom /etc/hosts file.</p>
<p>Hope this brief post was helpful, feel free to comment or hit up <code>@badgerops</code> on twitter!</p>
<p>-BadgerOps</p>
<!--kg-card-end: markdown-->