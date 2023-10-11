+++
title = "Getting started with Salt Grains"
date = "2017-04-23T22:26:05Z"
draft = false
+++

If you've been following along with the last few blog posts, we've looked at some basic Salt structure, as well as a [Vagrant based environment](__GHOST_URL__/2017/04/10/getting-started-with-salt-workspace/) where you can experiment, and follow along with these blog posts.

In this post we'll talk about Salt Grains. [Salt Grains](https://docs.saltstack.com/en/latest/topics/grains) are a way to get information about the underlying system. If you've got your Vagrant environment running you can log into the saltmaster and run `sudo salt saltmaster grains.items` to see all of the grains that are available to you. You could also do `sudo salt linux-1 grains.items` to see what the Linux-1 Minion has available, assuming you booted both VM's.

You'll see theres a lot of basic information about the VM's, we can utilize this information to help modify our Salt States. 

For example, lets say we've got a mixed environment of Linux and Windows VM's. You might have a base State that enforces MOTD - but as we know from [the last post](__GHOST_URL__/2017/04/22/getting-started-with-salt-structure-2/) the [motd Formula](https://github.com/BadgerOps/salt-workspace/blob/master/formulas/motd/init.sls) only knows about setting `/etc/motd` which obviously wont work on Windows, which means we'll get a failing State on the Windows hosts. 

