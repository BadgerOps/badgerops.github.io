+++
title = "Writing a custom Salt Grain"
date = "2017-04-23T22:55:05Z"
draft = false
+++

<!--kg-card-begin: markdown--><p>In this blog post, we'll talk about writing a custom Salt Grain, and why you might want to.</p>
<p>At my company we had some VM's that had multiple (private) IPv4 addresses set on them, and this broke <a href="https://www.consul.io/">Consul</a> as it can only bind to a <a href="https://www.consul.io/docs/agent/options.html#_bind">single Private IPv4 address</a>.</p>
<p>You might say &quot;Hey BadgerOps! You can use the grain <code>fqdn_ip4</code> to get this IP!&quot; and thus bask in your incredibly profound knowledge of Salt Grains. However, I'd rebut: &quot;Yes, but this assumes that whoever set up that VM configured /etc/hosts properly&quot; - And while I'd love to think that the individual who set the server up did it correctly, we live in the real world and we all know that often things aren't configured properly.</p>
<p>This knowledge coupled with my excellent grasp of Murphys Law gave me the idea to do the following: Write a custom grain for finding the 'real' IPv4 address on a server. (I consider the IPv4 address that is associated with the default route to be the 'real' address)</p>
<p>As is my custom, I'll first refer you to <a href="https://docs.saltstack.com/en/latest/topics/grains/#writing-grains">Documentation!</a> and state &quot;it's really good, you should read it!&quot; - And then I'll follow that with an example of how to do the thing.</p>
<hr>
<h5 id="exampleofhowtodothething">Example of how to do the thing:</h5>
<p>If you're using <a href="https://github.com/BadgerOps/salt-workspace">salt-workspace</a> you can checkout the 'custom_grain' branch to see the following.</p>
<p>Create a <a href="https://github.com/BadgerOps/salt-workspace/blob/custom_grain/salt/_grains">directory</a> underneath 'Salt' called <code>_grains</code> (but then you already knew this, because you read the <a href="https://docs.saltstack.com/en/latest/topics/grains/#writing-grains">Documentation!</a> right?)</p>
<p><a href="https://github.com/BadgerOps/salt-workspace/blob/custom_grain/salt/_grains/primary_ip4.py">This</a> is a (very simple) example of the contents of the primary_ipv4 Grain:</p>
<pre><code>#!/usr/bin/env python
import subprocess

def getipv4():
    grains = {}
    ipv4 = subprocess.check_output(&quot;ip route get 1 | awk '{print $NF;exit}'&quot;, shell=True)
    grains['primary_ipv4'] = ipv4
    return grains
</code></pre>
<p>You'll create a file at salt/_grains/primary_ipv4.py and put the contents of the example in there as seen <a href="https://github.com/BadgerOps/salt-workspace/blob/custom_grain/salt/_grains/primary_ip4.py">here</a>.</p>
<hr>
<h5 id="exampleofhowtotestthething">Example of how to test the thing</h5>
<p>Assuming you've got the <a href="__GHOST_URL__/2017/04/10/getting-started-with-salt-workspace/">salt-workspace</a> set up, you can start up the saltmaster and the linux-1 VM: <code>vagrant up saltmaster linux-1</code></p>
<p>Then, ensure you run <code>make</code> to build the salt structure and move it to ./dist/ which is sync'd to the saltmaster VM.</p>
<p>Log into the saltmaster and run <code>salt \* saltutil.sync_grains</code> which will synchronize the grains across all nodes. You should see the following output:</p>
<pre><code>[vagrant@saltmaster ~]$ sudo salt \* saltutil.sync_grains
saltmaster:
    - grains.primary_ip4
linux-1:
    - grains.primary_ip4
</code></pre>
<p>Then you should be able to run <code>salt \* grains.get primary_ipv4</code> as seen below:</p>
<pre><code>[vagrant@saltmaster ~]$ sudo salt \* grains.get primary_ipv4
saltmaster:
    10.0.2.15
linux-1:
    10.1.2.15
</code></pre>
<p>Thats it! Now, this example is very simplistic, and it obviously won't work with Windows minions (although the <a href="https://docs.saltstack.com/en/latest/ref/modules/all/salt.modules.win_ip.html">win_ip</a> module should be pretty useful here) but its a good initial example of what you can do to solve an issue with custom grains.</p>
<p>Thanks for reading!</p>
<p>-BadgerOps</p>
<!--kg-card-end: markdown-->