+++
title = "Getting started with salt-workspace"
date = "2017-04-08T23:26:05Z"
draft = false
+++

Welcome to 'getting started with salt-workspace'. Hopefully this, in combination with [the salt-workspace git repo](https://github.com/BadgerOps/salt-workspace) will help you get familiar with Salt and its structure in an easy to follow manner.

If you haven't already, follow the [Readme instructions](https://github.com/BadgerOps/salt-workspace/blob/master/README.md) to get the workspace pre-requisites done, then come back here for the first lesson.

---

##### Workspace Notes:
you can look in the [Vagrantfile](https://github.com/BadgerOps/salt-workspace/blob/master/Vagrantfile) for more information; this workspace will support:

 - Centos 6 or 7 (bento/centos-7.3 is the default)
 - Ubuntu 14.04 or 16.04
 - Windows Server 2012r2
 - Default ram is 512mb, but can be configured with the `LINUX_BOX_RAM` environment variable, for example to have 1gb ram:
```bash
LINUX_BOX_RAM=1024mb
```
  - Default is 1 'linux' VM, but you can use the `LINUX_MINION_COUNT` environment variable to spin up as many as you have resources for, for example you can have 3 linux VM's by typing:

```bash
LINUX_MINION_COUNT=3
```

  - Salt version can be overridden with `SALT_VERSION` like this:
```bash
SALT_VERSION=2016.11.3
```
These are the most common changes you might want to make, again you can reference the [Vagrantfile](https://github.com/BadgerOps/salt-workspace/blob/master/Vagrantfile) for the rest of the available options.

---
Now that you've got the workspace environment variables set up, try the following:
```bash
make all
```
The [make all](https://github.com/BadgerOps/salt-workspace/blob/master/Makefile#L7) command copies the salt files to ./dist which is [sync'd to the salt master](https://github.com/BadgerOps/salt-workspace/blob/master/Vagrantfile#L62) /srv directory, which is then designated by the [file roots](https://github.com/BadgerOps/salt-workspace/blob/master/config/master#L3) in the salt master configuration file. After you see `Salt is ready in ./dist. Enjoy!` you can do the following:

```bash
vagrant up saltmaster linux-1
```
This will bring up a centos 7 based salt master and minion VM (Assuming you didn't change the `LINUX_DISTRO` or `LINUX_VERSION` env variables). Note, that you can do everything on one VM (the saltmaster) if you're constrained on resources. However for the purposes of this tutorial, I'll assume you're running the two VM's.

Next, to verify things are running properly, you can type `vagrant status`
```bash
$ vagrant status
Chose image bento/centos-7.3 from (default) args LINUX_DISTRO=centos LINUX_VERSION=7
Current machine states:

saltmaster                running
linux-1                   running
```
Notice how we default to the bento/centos-7.3 image, and as I've got no env variables set, we only have a 'saltmaster' and 'linux-1' minion up.

Next, lets go log into the salt master and poke around a bit

```bash
vagrant ssh saltmaster

[vagrant@saltmaster ~]$ sudo salt \* test.ping
linux-1:
    True
saltmaster:
    True
```
The Vagrant up process deploys salt onto the VM's, and we also [copy in](https://github.com/BadgerOps/salt-workspace/blob/master/Vagrantfile#L72) a base [minion config](https://github.com/BadgerOps/salt-workspace/blob/master/config/minion) and [master config](https://github.com/BadgerOps/salt-workspace/blob/master/config/master) - feel free to peruse both to see the structure.

Next, we ensure the highstate runs properly - run it first like this:
`sudo salt \* state.highstate` (the \\* tells it to run on all minions)
```bash
[vagrant@saltmaster ~]$ sudo salt \* state.highstate
saltmaster:
----------
          ID: motd
    Function: file.managed
        Name: /etc/motd
      Result: True
     Comment: File /etc/motd is in the correct state
     Started: 05:13:13.237969
    Duration: 4.902 ms
     Changes:

Summary for saltmaster
------------
Succeeded: 1
Failed:    0
------------
Total states run:     1
Total run time:   4.902 ms
linux-1:
----------
          ID: motd
    Function: file.managed
        Name: /etc/motd
      Result: True
     Comment: File /etc/motd is in the correct state
     Started: 05:13:13.697753
    Duration: 3.259 ms
     Changes:

Summary for linux-1
------------
Succeeded: 1
Failed:    0
------------
Total states run:     1
Total run time:   3.259 ms

```
As you can see here, we only have 1 state being applied, which is setting an MOTD, using a very basic [formula](https://github.com/BadgerOps/salt-workspace/tree/master/formulas/motd), [pillar](https://github.com/BadgerOps/salt-workspace/blob/master/pillar/base/init.sls) and example of a [role](https://github.com/BadgerOps/salt-workspace/blob/master/salt/roles/init.sls). In later blog posts we'll discuss each of these pieces in depth.

Once you're happy with the ability to spin up and log into (and tinker around with!) your Vagrant boxes, you can log out of the salt master by pressing ctrl+D or, typing `exit`. Once you're back at your computers command prompt you can type `vagrant destroy saltmaster linux-1` to remove the old VM's.

This concludes the getting started blog post. If you have any issues spinning up  this environment you can submit an [issue](https://github.com/BadgerOps/salt-workspace/issues) or comment below with the error you're experiencing.

Next up, a look at the difference between Formulas and Roles, and how we can use Pillar data to modify both.

Thanks for checking this guide out!

-BadgerOps
