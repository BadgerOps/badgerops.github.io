+++
title = "Getting started with Salt Structure"
date = "2017-04-09T00:49:51Z"
draft = false
+++

###### Note: please complete the [getting started with salt workspace](blog.badgerops.net/2017/04/10/getting-started-with-salt-workspace/) post first!

###### Note #2: 

This post is designed to work with the 'minimal_base' branch of the salt workspace, so once you've cloned it run this:
```
git checkout minimal_workspace
```
This will ensure you're following along with the exact same code I'm using for examples.

Lets look at some structure now. Upstream [best practices](https://docs.saltstack.com/en/latest/topics/best_practices.html) show what the structure should look like. I follow pretty closely to this.

--- 
##### Folder structure

Lets look at the 'tree' of the top level folders as seen from the 'root' of the salt-workspace directory. The 3 Salt specific folders are `formulas`, `pillar` and `salt`. The `build`, `config` and `test` folders are all supporting and we'll discuss them later. 
```bash
├── build <- contains a python script to build ./dist 
├── config <- master and minion config for Vagrant to copy in
├── formulas <- formulas go in here
│   └── motd
│       └── tests <- we can have tests per formula
├── pillar <- configuration variables go here
│   └── base <- this is the default environment 'base'
├── salt
│   └── roles <- roles go here!
└── tests <- everyone should have tests!
```

In later lessons we'll discuss how to support multiple environments with Salt, both in a single repo and split repo deployment.

--- 
##### States

The core concept in Salt is enforcing a specific 'State' on the target system. This can be something like installing a specific package, creating a directory structure, or adding a configuration file with contents specified in Pillar (more on this later).

Salt [States](https://docs.saltstack.com/en/latest/topics/tutorials/starting_states.html) are generally formed from combinations of YAML files containing instructions, and Jinja2 templates. The upstream example of a State that installs the Apache package is pretty straightforward:

```bash
apache:
  pkg.installed: []
  service.running:
    - require:
      - pkg: apache
```
It uses the [pkg.installed](https://docs.saltstack.com/en/latest/ref/states/all/salt.states.pkg.html) State - and also the [service.running](https://docs.saltstack.com/en/latest/ref/states/all/salt.states.service.html) State.

Lets break this down into its two separate pieces. 

```bash
apache:
  pkg.installed: []
```
the `pkg.installed` State can accept its own list of commands, but in this case we're giving it an empty list `[]` saying we'll accept the upstream package managers defaults. We could do something like the following:

```yaml
apache:
  pkg.installed:
    - version: 2.4.2
    - fromrepo: mycustomrepo
    - allow_updates: True
```

Notice how we define the values in the list with a `-` for each item. The default [yaml](https://docs.saltstack.com/en/latest/ref/renderers/) renderer will serialize the specified data into a json object which Salt will then pass to the `pkg.installed` State.

The second half of the upstream example is the `service.running` State:
```bash
apache:
  service.running:
    - require:
      - pkg: apache
```

Now, in practice this would not render as we've defined `apache` twice, so we could do something like this:

```yaml
apache_pkg:
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
```

As you can see this, while more specific and verbose, takes far more lines than the initial example. (I'd argue that its far easier to understand, however)
Now that  we've looked at what a State is, we'll move on to Formulas!

---
##### Formulas
Formulas are pre-defined (sharable!) States. If you come from Chef or Puppet, this should be a familiar concept. If not, [upstream documentation](https://docs.saltstack.com/en/latest/topics/development/conventions/formulas.html) is incredibly useful. Formulas generally serve a single purpose - install and configure a specific application, or file as we'll examine below.

As noted in the documentation and above (seeing a theme here? The docs are good!) a Formula is simply a pre-defined state. For example, we may want to have a "Message of the Day" or MOTD so when someone logs into this server they get alerted that we're using Salt to manage it.

Inside every formula, we have at least an `init.sls`, and a `pillar.example`. In this formula, we also have an example of a test, with its own `init.sls`:
```bash
├── init.sls
├── pillar.example
└── tests
    └── init.yaml
```
the Formula `init.sls` looks like this:
```yaml
motd:
  file.managed:
    - name: /etc/motd
    - user: root
    - group: root
    - mode: '0644'
    - contents_pillar: motd:content
```
it uses the [file.managed](https://docs.saltstack.com/en/latest/ref/states/all/salt.states.file.html) State to create the `/etc/motd` file with contents that we'll pull from the Pillar file.

The [pillar.example](https://github.com/BadgerOps/salt-workspace/blob/master/formulas/motd/pillar.example) file is where we tell the user of the formula what the configuration variable options are. In this case its a very simple formula, with an equally simple Pillar.

We'll discuss testing in a later post, but the [test](https://github.com/BadgerOps/salt-workspace/blob/master/formulas/motd/tests/init.yaml) is a simple example of verifying the file gets created as expected.

---
##### Top files

Top files are, unsurprisingly the 'top' file in each directory. You'll have a top file in the Salt (States live here!) directory, and a top file in the Pillar directory. Their job is to manage what the Salt Minions are able to access.

I highly recommend reading (and then reading again!) the [documentation](https://docs.saltstack.com/en/latest/ref/states/top.html#a-basic-example) on top files. This is one part of your environment where things can - and will - get complicated quick. 

In the first example workspace, the top files look like this:

###### [./salt/top.sls](https://github.com/BadgerOps/salt-workspace/blob/master/salt/top.sls)
```
base:
  '*':
    - roles
```

Our initial environment is called 'base' - and we're matching on all VM's, and adding a layer of management with 'roles'. Lets look at what we do with the [roles](https://github.com/BadgerOps/salt-workspace/blob/master/salt/roles/init.sls) - its pretty simple initially, all we're doing is:

```
include:
  - base
```
and, in turn, base does:
```
include:
  - motd
```

While this may seem overly complex right now for a single Formula, we'll build on it and show how it adds flexibility in the future.

On the Pillar side, the [top.sls](https://github.com/BadgerOps/salt-workspace/blob/master/pillar/top.sls) is similar to the top.sls for the States (Salt) directory.

We could target Minions directly with top files, hopefully you already got your [workspace](blog.badgerops.net/2017/04/10/getting-started-with-salt-workspace/) up and running because now its time to get your hands dirty! (Take a second to ensure its up and you're logged in to the saltmaster VM) 

###### Note: 
if you're not using a directory watch tool as noted in the Readme.md, you'll have to manually run 'make' to push any code changes to the saltmaster VM. Open up a second tab and cd to the salt-workspace directory so you can easily run the make command without having to constantly log in and out of the saltmaster VM.

Now, in your [pillar/top.sls](https://github.com/BadgerOps/salt-workspace/blob/master/pillar/top.sls) lets specify *only* the `linux-1` VM:
```
base:
  'linux-1':
    - base

```
Don't forget to run `make` !

Now, from the saltmaster VM run `sudo salt \* state.highstate` and note the output:

```
[vagrant@saltmaster ~]$ sudo salt \* state.highstate
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
```

Uh, oh we ran into an error here. We updated the *Pillar* top file, but what about the State top file in the 'salt' directory? This is a common error to run into if your top files aren't matched. We tell the Salt Minion that it needs to run the `motd` state, but we don't give it any values in Pillar, so its errors out.

Easy fix, modify the [state top.sls](https://github.com/BadgerOps/salt-workspace/blob/master/salt/top.sls) to look like:

```
base:
  'linux-1':
    - base
```

Run `make` !

```
[vagrant@saltmaster ~]$ sudo salt \* state.highstate
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
```

Thats more like it! We can see that saltmaster still errors out, but this is because we're telling it to run [highstate](https://docs.saltstack.com/en/latest/ref/modules/all/salt.modules.state.html#salt.modules.state.highstate) which collects any assigned States and runs them all. If there are no States assigned to a Minion, we'll get an error telling us that, as we see with the saltmaster Minion.

Note, that we can apply a State to a Minion even if its not assigned, by ensuring it has access to pillar like this:

[pillar/top.sls](https://github.com/BadgerOps/salt-workspace/blob/master/pillar/top.sls) lets switch back to matching all Minions:
```
base:
  '*':
    - base

```
Run `make`!

```
[vagrant@saltmaster ~]$ sudo salt \* state.apply base
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
```
Even though we didn't explicitly tell the State top.sls to assign a state to the Minion, we can still apply it by directly calling [state.apply](https://docs.saltstack.com/en/latest/ref/modules/all/salt.modules.state.html#salt.modules.state.apply) and giving it the correct pillar. 
###### Note:
We can actually [inject pillar from the command line](https://docs.saltstack.com/en/latest/topics/tutorials/pillar.html#setting-pillar-data-on-the-command-line) by doing something like the following:

```
[vagrant@saltmaster ~]$ sudo salt saltmaster state.apply base pillar='{"motd": {"content": "Hello, world!"}}'
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
```

Hopefully these examples help clarify some of what you've seen in the upstream documentation. Comment below if you have any questions or clarification for me.

Thanks for following along!

-BadgerOps