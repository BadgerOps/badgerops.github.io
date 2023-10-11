+++
title = "Getting started with Salt Grains"
date = "2017-04-23T22:26:05Z"
draft = false
+++

<!--kg-card-begin: markdown--><p>If you've been following along with the last few blog posts, we've looked at some basic Salt structure, as well as a <a href="__GHOST_URL__/2017/04/10/getting-started-with-salt-workspace/">Vagrant based environment</a> where you can experiment, and follow along with these blog posts.</p>
<p>In this post we'll talk about Salt Grains. <a href="https://docs.saltstack.com/en/latest/topics/grains">Salt Grains</a> are a way to get information about the underlying system. If you've got your Vagrant environment running you can log into the saltmaster and run <code>sudo salt saltmaster grains.items</code> to see all of the grains that are available to you. You could also do <code>sudo salt linux-1 grains.items</code> to see what the Linux-1 Minion has available, assuming you booted both VM's.</p>
<p>You'll see theres a lot of basic information about the VM's, we can utilize this information to help modify our Salt States.</p>
<p>For example, lets say we've got a mixed environment of Linux and Windows VM's. You might have a base State that enforces MOTD - but as we know from <a href="__GHOST_URL__/2017/04/22/getting-started-with-salt-structure-2/">the last post</a> the <a href="https://github.com/BadgerOps/salt-workspace/blob/master/formulas/motd/init.sls">motd Formula</a> only knows about setting <code>/etc/motd</code> which obviously wont work on Windows, which means we'll get a failing State on the Windows hosts.</p>
<!--kg-card-end: markdown-->