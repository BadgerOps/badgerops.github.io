+++
title = "Getting started with salt-workspace"
date = "2017-04-08T23:26:05Z"
draft = false
+++

<!--kg-card-begin: markdown--><p>Welcome to 'getting started with salt-workspace'. Hopefully this, in combination with <a href="https://github.com/BadgerOps/salt-workspace">the salt-workspace git repo</a> will help you get familiar with Salt and its structure in an easy to follow manner.</p>
<p>If you haven't already, follow the <a href="https://github.com/BadgerOps/salt-workspace/blob/master/README.md">Readme instructions</a> to get the workspace pre-requisites done, then come back here for the first lesson.</p>
<hr>
<h5 id="workspacenotes">Workspace Notes:</h5>
<p>you can look in the <a href="https://github.com/BadgerOps/salt-workspace/blob/master/Vagrantfile">Vagrantfile</a> for more information; this workspace will support:</p>
<ul>
<li>Centos 6 or 7 (bento/centos-7.3 is the default)</li>
<li>Ubuntu 14.04 or 16.04</li>
<li>Windows Server 2012r2</li>
<li>Default ram is 512mb, but can be configured with the <code>LINUX_BOX_RAM</code> environment variable, for example to have 1gb ram:</li>
</ul>
<pre><code class="language-bash">LINUX_BOX_RAM=1024mb
</code></pre>
<ul>
<li>Default is 1 'linux' VM, but you can use the <code>LINUX_MINION_COUNT</code> environment variable to spin up as many as you have resources for, for example you can have 3 linux VM's by typing:</li>
</ul>
<pre><code class="language-bash">LINUX_MINION_COUNT=3
</code></pre>
<ul>
<li>Salt version can be overridden with <code>SALT_VERSION</code> like this:</li>
</ul>
<pre><code class="language-bash">SALT_VERSION=2016.11.3
</code></pre>
<p>These are the most common changes you might want to make, again you can reference the <a href="https://github.com/BadgerOps/salt-workspace/blob/master/Vagrantfile">Vagrantfile</a> for the rest of the available options.</p>
<hr>
<p>Now that you've got the workspace environment variables set up, try the following:</p>
<pre><code class="language-bash">make all
</code></pre>
<p>The <a href="https://github.com/BadgerOps/salt-workspace/blob/master/Makefile#L7">make all</a> command copies the salt files to ./dist which is <a href="https://github.com/BadgerOps/salt-workspace/blob/master/Vagrantfile#L62">sync'd to the salt master</a> /srv directory, which is then designated by the <a href="https://github.com/BadgerOps/salt-workspace/blob/master/config/master#L3">file roots</a> in the salt master configuration file. After you see <code>Salt is ready in ./dist. Enjoy!</code> you can do the following:</p>
<pre><code class="language-bash">vagrant up saltmaster linux-1
</code></pre>
<p>This will bring up a centos 7 based salt master and minion VM (Assuming you didn't change the <code>LINUX_DISTRO</code> or <code>LINUX_VERSION</code> env variables). Note, that you can do everything on one VM (the saltmaster) if you're constrained on resources. However for the purposes of this tutorial, I'll assume you're running the two VM's.</p>
<p>Next, to verify things are running properly, you can type <code>vagrant status</code></p>
<pre><code class="language-bash">$ vagrant status
Chose image bento/centos-7.3 from (default) args LINUX_DISTRO=centos LINUX_VERSION=7
Current machine states:

saltmaster                running
linux-1                   running
</code></pre>
<p>Notice how we default to the bento/centos-7.3 image, and as I've got no env variables set, we only have a 'saltmaster' and 'linux-1' minion up.</p>
<p>Next, lets go log into the salt master and poke around a bit</p>
<pre><code class="language-bash">vagrant ssh saltmaster

[vagrant@saltmaster ~]$ sudo salt \* test.ping
linux-1:
    True
saltmaster:
    True
</code></pre>
<p>The Vagrant up process deploys salt onto the VM's, and we also <a href="https://github.com/BadgerOps/salt-workspace/blob/master/Vagrantfile#L72">copy in</a> a base <a href="https://github.com/BadgerOps/salt-workspace/blob/master/config/minion">minion config</a> and <a href="https://github.com/BadgerOps/salt-workspace/blob/master/config/master">master config</a> - feel free to peruse both to see the structure.</p>
<p>Next, we ensure the highstate runs properly - run it first like this:<br>
<code>sudo salt \* state.highstate</code> (the \* tells it to run on all minions)</p>
<pre><code class="language-bash">[vagrant@saltmaster ~]$ sudo salt \* state.highstate
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

</code></pre>
<p>As you can see here, we only have 1 state being applied, which is setting an MOTD, using a very basic <a href="https://github.com/BadgerOps/salt-workspace/tree/master/formulas/motd">formula</a>, <a href="https://github.com/BadgerOps/salt-workspace/blob/master/pillar/base/init.sls">pillar</a> and example of a <a href="https://github.com/BadgerOps/salt-workspace/blob/master/salt/roles/init.sls">role</a>. In later blog posts we'll discuss each of these pieces in depth.</p>
<p>Once you're happy with the ability to spin up and log into (and tinker around with!) your Vagrant boxes, you can log out of the salt master by pressing ctrl+D or, typing <code>exit</code>. Once you're back at your computers command prompt you can type <code>vagrant destroy saltmaster linux-1</code> to remove the old VM's.</p>
<p>This concludes the getting started blog post. If you have any issues spinning up  this environment you can submit an <a href="https://github.com/BadgerOps/salt-workspace/issues">issue</a> or comment below with the error you're experiencing.</p>
<p>Next up, a look at the difference between Formulas and Roles, and how we can use Pillar data to modify both.</p>
<p>Thanks for checking this guide out!</p>
<p>-BadgerOps</p>
<!--kg-card-end: markdown-->