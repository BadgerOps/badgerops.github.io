+++
title = "Getting started with Salt Structure"
date = "2017-04-09T00:49:51Z"
draft = false
+++

<!--kg-card-begin: markdown--><h6 id="notepleasecompletethegettingstartedwithsaltworkspacepostfirst">Note: please complete the <a href="__GHOST_URL__/2017/04/10/getting-started-with-salt-workspace/">getting started with salt workspace</a> post first!</h6>
<h6 id="note2">Note #2:</h6>
<p>This post is designed to work with the 'minimal_base' branch of the salt workspace, so once you've cloned it run this:</p>
<pre><code>git checkout minimal_workspace
</code></pre>
<p>This will ensure you're following along with the exact same code I'm using for examples.</p>
<p>Lets look at some structure now. Upstream <a href="https://docs.saltstack.com/en/latest/topics/best_practices.html">best practices</a> show what the structure should look like. I follow pretty closely to this.</p>
<hr>
<h5 id="folderstructure">Folder structure</h5>
<p>Lets look at the 'tree' of the top level folders as seen from the 'root' of the salt-workspace directory. The 3 Salt specific folders are <code>formulas</code>, <code>pillar</code> and <code>salt</code>. The <code>build</code>, <code>config</code> and <code>test</code> folders are all supporting and we'll discuss them later.</p>
<pre><code class="language-bash">├── build &lt;- contains a python script to build ./dist 
├── config &lt;- master and minion config for Vagrant to copy in
├── formulas &lt;- formulas go in here
│   └── motd
│       └── tests &lt;- we can have tests per formula
├── pillar &lt;- configuration variables go here
│   └── base &lt;- this is the default environment 'base'
├── salt
│   └── roles &lt;- roles go here!
└── tests &lt;- everyone should have tests!
</code></pre>
<p>In later lessons we'll discuss how to support multiple environments with Salt, both in a single repo and split repo deployment.</p>
<hr>
<h5 id="states">States</h5>
<p>The core concept in Salt is enforcing a specific 'State' on the target system. This can be something like installing a specific package, creating a directory structure, or adding a configuration file with contents specified in Pillar (more on this later).</p>
<p>Salt <a href="https://docs.saltstack.com/en/latest/topics/tutorials/starting_states.html">States</a> are generally formed from combinations of YAML files containing instructions, and Jinja2 templates. The upstream example of a State that installs the Apache package is pretty straightforward:</p>
<pre><code class="language-bash">apache:
  pkg.installed: []
  service.running:
    - require:
      - pkg: apache
</code></pre>
<p>It uses the <a href="https://docs.saltstack.com/en/latest/ref/states/all/salt.states.pkg.html">pkg.installed</a> State - and also the <a href="https://docs.saltstack.com/en/latest/ref/states/all/salt.states.service.html">service.running</a> State.</p>
<p>Lets break this down into its two separate pieces.</p>
<pre><code class="language-bash">apache:
  pkg.installed: []
</code></pre>
<p>the <code>pkg.installed</code> State can accept its own list of commands, but in this case we're giving it an empty list <code>[]</code> saying we'll accept the upstream package managers defaults. We could do something like the following:</p>
<pre><code class="language-yaml">apache:
  pkg.installed:
    - version: 2.4.2
    - fromrepo: mycustomrepo
    - allow_updates: True
</code></pre>
<p>Notice how we define the values in the list with a <code>-</code> for each item. The default <a href="https://docs.saltstack.com/en/latest/ref/renderers/">yaml</a> renderer will serialize the specified data into a json object which Salt will then pass to the <code>pkg.installed</code> State.</p>
<p>The second half of the upstream example is the <code>service.running</code> State:</p>
<pre><code class="language-bash">apache:
  service.running:
    - require:
      - pkg: apache
</code></pre>
<p>Now, in practice this would not render as we've defined <code>apache</code> twice, so we could do something like this:</p>
<pre><code class="language-yaml">apache_pkg:
  pkg.installed:
    - name: apache
    - version: 2.4.2
    - fromrepo: mycustomrepo
    - allow_updates: True

apache_service:
  service.running:
    - name: apache
    - require:
      - pkg: apache_pkg
</code></pre>
<p>As you can see this, while more specific and verbose, takes far more lines than the initial example. (I'd argue that its far easier to understand, however)<br>
Now that  we've looked at what a State is, we'll move on to Formulas!</p>
<hr>
<h5 id="formulas">Formulas</h5>
<p>Formulas are pre-defined (sharable!) States. If you come from Chef or Puppet, this should be a familiar concept. If not, <a href="https://docs.saltstack.com/en/latest/topics/development/conventions/formulas.html">upstream documentation</a> is incredibly useful. Formulas generally serve a single purpose - install and configure a specific application, or file as we'll examine below.</p>
<p>As noted in the documentation and above (seeing a theme here? The docs are good!) a Formula is simply a pre-defined state. For example, we may want to have a &quot;Message of the Day&quot; or MOTD so when someone logs into this server they get alerted that we're using Salt to manage it.</p>
<p>Inside every formula, we have at least an <code>init.sls</code>, and a <code>pillar.example</code>. In this formula, we also have an example of a test, with its own <code>init.sls</code>:</p>
<pre><code class="language-bash">├── init.sls
├── pillar.example
└── tests
    └── init.yaml
</code></pre>
<p>the Formula <code>init.sls</code> looks like this:</p>
<pre><code class="language-yaml">motd:
  file.managed:
    - name: /etc/motd
    - user: root
    - group: root
    - mode: '0644'
    - contents_pillar: motd:content
</code></pre>
<p>it uses the <a href="https://docs.saltstack.com/en/latest/ref/states/all/salt.states.file.html">file.managed</a> State to create the <code>/etc/motd</code> file with contents that we'll pull from the Pillar file.</p>
<p>The <a href="https://github.com/BadgerOps/salt-workspace/blob/master/formulas/motd/pillar.example">pillar.example</a> file is where we tell the user of the formula what the configuration variable options are. In this case its a very simple formula, with an equally simple Pillar.</p>
<p>We'll discuss testing in a later post, but the <a href="https://github.com/BadgerOps/salt-workspace/blob/master/formulas/motd/tests/init.yaml">test</a> is a simple example of verifying the file gets created as expected.</p>
<hr>
<h5 id="topfiles">Top files</h5>
<p>Top files are, unsurprisingly the 'top' file in each directory. You'll have a top file in the Salt (States live here!) directory, and a top file in the Pillar directory. Their job is to manage what the Salt Minions are able to access.</p>
<p>I highly recommend reading (and then reading again!) the <a href="https://docs.saltstack.com/en/latest/ref/states/top.html#a-basic-example">documentation</a> on top files. This is one part of your environment where things can - and will - get complicated quick.</p>
<p>In the first example workspace, the top files look like this:</p>
<h6 id="salttopsls"><a href="https://github.com/BadgerOps/salt-workspace/blob/master/salt/top.sls">./salt/top.sls</a></h6>
<pre><code>base:
  '*':
    - roles
</code></pre>
<p>Our initial environment is called 'base' - and we're matching on all VM's, and adding a layer of management with 'roles'. Lets look at what we do with the <a href="https://github.com/BadgerOps/salt-workspace/blob/master/salt/roles/init.sls">roles</a> - its pretty simple initially, all we're doing is:</p>
<pre><code>include:
  - base
</code></pre>
<p>and, in turn, base does:</p>
<pre><code>include:
  - motd
</code></pre>
<p>While this may seem overly complex right now for a single Formula, we'll build on it and show how it adds flexibility in the future.</p>
<p>On the Pillar side, the <a href="https://github.com/BadgerOps/salt-workspace/blob/master/pillar/top.sls">top.sls</a> is similar to the top.sls for the States (Salt) directory.</p>
<p>We could target Minions directly with top files, hopefully you already got your <a href="__GHOST_URL__/2017/04/10/getting-started-with-salt-workspace/">workspace</a> up and running because now its time to get your hands dirty! (Take a second to ensure its up and you're logged in to the saltmaster VM)</p>
<h6 id="note">Note:</h6>
<p>if you're not using a directory watch tool as noted in the Readme.md, you'll have to manually run 'make' to push any code changes to the saltmaster VM. Open up a second tab and cd to the salt-workspace directory so you can easily run the make command without having to constantly log in and out of the saltmaster VM.</p>
<p>Now, in your <a href="https://github.com/BadgerOps/salt-workspace/blob/master/pillar/top.sls">pillar/top.sls</a> lets specify <em>only</em> the <code>linux-1</code> VM:</p>
<pre><code>base:
  'linux-1':
    - base

</code></pre>
<p>Don't forget to run <code>make</code> !</p>
<p>Now, from the saltmaster VM run <code>sudo salt \* state.highstate</code> and note the output:</p>
<pre><code>[vagrant@saltmaster ~]$ sudo salt \* state.highstate
saltmaster:
----------
          ID: motd
    Function: file.managed
        Name: /etc/motd
      Result: False
     Comment: Pillar motd:content does not exist
     Started: 17:31:59.629042
    Duration: 1.709 ms
     Changes:

Summary for saltmaster
------------
Succeeded: 0
Failed:    1
------------
Total states run:     1
Total run time:   1.709 ms
linux-1:
----------
          ID: motd
    Function: file.managed
        Name: /etc/motd
      Result: True
     Comment: File /etc/motd is in the correct state
     Started: 17:31:59.821670
    Duration: 2.582 ms
     Changes:

Summary for linux-1
------------
Succeeded: 1
Failed:    0
------------
Total states run:     1
Total run time:   2.582 ms
ERROR: Minions returned with non-zero exit code
</code></pre>
<p>Uh, oh we ran into an error here. We updated the <em>Pillar</em> top file, but what about the State top file in the 'salt' directory? This is a common error to run into if your top files aren't matched. We tell the Salt Minion that it needs to run the <code>motd</code> state, but we don't give it any values in Pillar, so its errors out.</p>
<p>Easy fix, modify the <a href="https://github.com/BadgerOps/salt-workspace/blob/master/salt/top.sls">state top.sls</a> to look like:</p>
<pre><code>base:
  'linux-1':
    - base
</code></pre>
<p>Run <code>make</code> !</p>
<pre><code>[vagrant@saltmaster ~]$ sudo salt \* state.highstate
saltmaster:
----------
          ID: states
    Function: no.None
      Result: False
     Comment: No Top file or external nodes data matches found.
     Changes:

Summary for saltmaster
------------
Succeeded: 0
Failed:    1
------------
Total states run:     1
Total run time:   0.000 ms
linux-1:
----------
          ID: motd
    Function: file.managed
        Name: /etc/motd
      Result: True
     Comment: File /etc/motd is in the correct state
     Started: 17:36:30.869217
    Duration: 2.874 ms
     Changes:

Summary for linux-1
------------
Succeeded: 1
Failed:    0
------------
Total states run:     1
Total run time:   2.874 ms
</code></pre>
<p>Thats more like it! We can see that saltmaster still errors out, but this is because we're telling it to run <a href="https://docs.saltstack.com/en/latest/ref/modules/all/salt.modules.state.html#salt.modules.state.highstate">highstate</a> which collects any assigned States and runs them all. If there are no States assigned to a Minion, we'll get an error telling us that, as we see with the saltmaster Minion.</p>
<p>Note, that we can apply a State to a Minion even if its not assigned, by ensuring it has access to pillar like this:</p>
<p><a href="https://github.com/BadgerOps/salt-workspace/blob/master/pillar/top.sls">pillar/top.sls</a> lets switch back to matching all Minions:</p>
<pre><code>base:
  '*':
    - base

</code></pre>
<p>Run <code>make</code>!</p>
<pre><code>[vagrant@saltmaster ~]$ sudo salt \* state.apply base
saltmaster:
----------
          ID: motd
    Function: file.managed
        Name: /etc/motd
      Result: True
     Comment: File /etc/motd is in the correct state
     Started: 17:39:13.688375
    Duration: 3.955 ms
     Changes:

Summary for saltmaster
------------
Succeeded: 1
Failed:    0
------------
Total states run:     1
Total run time:   3.955 ms
linux-1:
----------
          ID: motd
    Function: file.managed
        Name: /etc/motd
      Result: True
     Comment: File /etc/motd is in the correct state
     Started: 17:39:13.824098
    Duration: 2.545 ms
     Changes:

Summary for linux-1
------------
Succeeded: 1
Failed:    0
------------
Total states run:     1
Total run time:   2.545 ms
</code></pre>
<p>Even though we didn't explicitly tell the State top.sls to assign a state to the Minion, we can still apply it by directly calling <a href="https://docs.saltstack.com/en/latest/ref/modules/all/salt.modules.state.html#salt.modules.state.apply">state.apply</a> and giving it the correct pillar.</p>
<h6 id="note">Note:</h6>
<p>We can actually <a href="https://docs.saltstack.com/en/latest/topics/tutorials/pillar.html#setting-pillar-data-on-the-command-line">inject pillar from the command line</a> by doing something like the following:</p>
<pre><code>[vagrant@saltmaster ~]$ sudo salt saltmaster state.apply base pillar='{&quot;motd&quot;: {&quot;content&quot;: &quot;Hello, world!&quot;}}'
saltmaster:
----------
          ID: motd
    Function: file.managed
        Name: /etc/motd
      Result: True
     Comment: File /etc/motd updated
     Started: 17:47:02.252779
    Duration: 3.348 ms
     Changes:
              ----------
              diff:
                  ---
                  +++
                  @@ -1,6 +1 @@
                  -
                  -#########################################################################################################
                  -#                                                                                                       #
                  -#            This host is managed by Salt. Configuration changes made directly will be lost.            #
                  -#                                                                                                       #
                  -#########################################################################################################
                  +Hello, world!

Summary for saltmaster
------------
Succeeded: 1 (changed=1)
Failed:    0
------------
Total states run:     1
Total run time:   3.348 ms
</code></pre>
<p>Hopefully these examples help clarify some of what you've seen in the upstream documentation. Comment below if you have any questions or clarification for me.</p>
<p>Thanks for following along!</p>
<p>-BadgerOps</p>
<!--kg-card-end: markdown-->