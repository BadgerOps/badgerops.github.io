+++
title = "GPG encrypting secrets with Saltstack"
date = "2017-05-31T03:09:53Z"
draft = false
+++

Hi there! If you've stumbled on this post, you've either been following along with my "Getting started with Saltstack" series using the [Salt Workspace](https://github.com/BadgerOps/salt-workspace) environment, or I got lucky with Google's scrapes.

In this post we'll discuss GPG encrypting secrets in Salt. Yes, there are other ways to store and look up secrets, like [Vault](https://www.vaultproject.io/) - but sometimes (well, often) its simpler to keep secret management in-house as it were.

GPG encrypted Pillar is similar to encrypted data bags if you're coming from Chef-land. 

As usual, I'll say: [Read.The.Docs](https://docs.saltstack.com/en/latest/ref/renderers/all/salt.renderers.gpg.html). (They're excellent!) But sometimes, its nice to be able to experiment with an environment hence why I'm sitting here sipping some delicious Laphroaig typing words with my fingers... But I'm getting sidetracked. On to the demo code!

Once again, assuming you've already set up your [salt workspace](__GHOST_URL__/2017/04/10/getting-started-with-salt-workspace/) you can follow along here by checking out the `minimal_base` branch, or the `feature/gpg_example` branch to see the completed setup.

The first thing you'll want to do is create the folder for the gpg key:
```
vagrant ssh saltmaster
sudo mkdir -p /etc/salt/gpgkeys
sudo chmod 0700 /etc/salt/gpgkeys
```
Next, we'll step through the options:
```
sudo gpg --gen-key --homedir /etc/salt/gpgkeys
gpg (GnuPG) 2.0.22; Copyright (C) 2013 Free Software Foundation, Inc.
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.

gpg: keyring `/etc/salt/gpgkeys/secring.gpg' created
gpg: keyring `/etc/salt/gpgkeys/pubring.gpg' created
Please select what kind of key you want:
   (1) RSA and RSA (default)
   (2) DSA and Elgamal
   (3) DSA (sign only)
   (4) RSA (sign only)
```
Choose #1, this uses [RSA](https://en.wikipedia.org/wiki/RSA_(cryptosystem)) for Signing as well as Encrypting the content. 

Optionally, you can use the DSA algorithm for Signing, and Elgamal for Encrypting and finally (not relevant here, we are wanting to encrypt, not sign) you could create a Signing only key using either RSA or DSA.

Next, we'll see keysize:
```
RSA keys may be between 1024 and 4096 bits long.
What keysize do you want? (2048)
```
The default can be taken here as well. Unless you're worried about certain 3 letter agencies, in which case I'd say you probably have bigger things to worry about than encrypting content in Pillar, but I digress. Moving on!

Key expiration:
```
Please specify how long the key should be valid.
         0 = key does not expire
      <n>  = key expires in n days
      <n>w = key expires in n weeks
      <n>m = key expires in n months
      <n>y = key expires in n years
Key is valid for? (0)
```

Personally I don't set these keys to expire. Ideally you'd have a secret rotation schedule and plan for stuff to expire. But lets face it, if you have the time and budget to pull that off, you're not reading this blog post. (That'd be the Scotch speaking)

Now for the user ID:
```
GnuPG needs to construct a user ID to identify your key.

Real name: Salt Master
Email address: salt@badgerops.net
Comment: "This is the Salt GPG key"
You selected this USER-ID:
    "Salt Master ("This is the Salt GPG key") <salt@badgerops.net>"

Change (N)ame, (C)omment, (E)mail or (O)kay/(Q)uit?
```
I enter 'Salt Master' here. Mostly because I'm not the *most* creative person I know. Also its far easier to remember than 'Gordon Freeman esq' which may or may not have been a GPG identity. Of someone. I knew. Once. A long time ago.

Email should be something reasonable for your org. Comment just makes it easier to parse when you do `gpg --list-keys`

Press `O` and do not enter a passphrase (we can't enter a passphrase on the salt master every time a minion tries to decrypt Pillar contents).

You'll have to tell GPG about 5 times that yes, you do not want a passphrase, then it will start generating entropy for the key.
###### Note: 
If you see this:
```
gpg: can't connect to the agent: IPC connect call failed
gpg: problem with the agent: No agent running
gpg: can't connect to the agent: IPC connect call failed
gpg: problem with the agent: No agent running
gpg: Key generation canceled.
```
you can run the following to re-start the gpg-agent with the desired home directory. 
```
sudo pkill -9 gpg-agent
source <( sudo gpg-agent --homedir=/etc/salt/gpgkeys --daemon)
```
This should get you back on track.

Entropy. Now is a ~~good~~ ok time to mention that a VM generally doesn't have a ton of entropy due to it not having any 'real' hardware.

You can open up a second session to the salt master and run `cat /proc/sys/kernel/random/entropy_avail` to see how much entropy you have:
```
[vagrant@saltmaster ~]$ cat /proc/sys/kernel/random/entropy_avail
12
```
As we can see, there is not a whole lot of entropy here (you want to see at least 100-200) so we can either wait, or try and make some extra entropy by doing other operations, like pinging hosts, running highstates, etc.

```
gpg: /etc/salt/gpgkeys/trustdb.gpg: trustdb created
gpg: key 6AD73E7C marked as ultimately trusted
public and secret key created and signed.

gpg: checking the trustdb
gpg: 3 marginal(s) needed, 1 complete(s) needed, PGP trust model
gpg: depth: 0  valid:   1  signed:   0  trust: 0-, 0q, 0n, 0m, 0f, 1u
pub   2048R/6AD73E7C 2017-05-31
      Key fingerprint = A745 9740 7E09 C45C D8BF  1467 9663 39CB 6AD7 3E7C
uid                  Salt Master (Salt Master) <salt@badgerops.net>
sub   2048R/C55AD152 2017-05-31
```

Success! We've got a GPG key now, and we can see the supporting files are in the directory we created:
```
sudo ls /etc/salt/gpgkeys/
private-keys-v1.d  pubring.gpg	pubring.gpg~  random_seed  secring.gpg	S.gpg-agent  trustdb.gpg
```
Now, to get the public key that we can use to encrypt the data:
```
sudo gpg --homedir /etc/salt/gpgkeys --armor --export Salt Master > salt_key.gpg
```

salt_key.gpg can be distributed (mine is committed in my git repo) as it is useless to anyone who doesn't have the private key. (Keep it secret! Keep it safe!)[the private key, that is]

Now, on the host that you're going to be doing the encrypted content generation from, you'll want to import the GPG key:
```
gpg --import salt_key.gpg
```
You should then be able to do: `gpg --list-keys`
```
[vagrant@saltmaster ~]$ gpg --list-keys
/home/vagrant/.gnupg/pubring.gpg
--------------------------------
pub   2048R/6AD73E7C 2017-05-31
uid                  Salt Master (Salt Master) <salt@badgerops.net>
sub   2048R/C55AD152 2017-05-31
```

Great success! Lets get to encrypting pillar contents now! We'll run this command to generate a brief message:
` echo -n 'This is encrypted!' | gpg --armor --encrypt -r 'Salt Master'`
```
[vagrant@saltmaster ~]$ echo -n 'This is encrypted!' | gpg --armor --encrypt -r 'Salt Master'
gpg: C55AD152: There is no assurance this key belongs to the named user

pub  2048R/C55AD152 2017-05-31 Salt Master (Salt Master) <salt@badgerops.net>
 Primary key fingerprint: A745 9740 7E09 C45C D8BF  1467 9663 39CB 6AD7 3E7C
      Subkey fingerprint: 6AB8 1F8A 8D7B B23F 04E1  93E8 C1BA 98F2 C55A D152

It is NOT certain that the key belongs to the person named
in the user ID.  If you *really* know what you are doing,
you may answer the next question with yes.

Use this key anyway? (y/N)

# press 'y' (duh!)

-----BEGIN PGP MESSAGE-----
Version: GnuPG v2.0.22 (GNU/Linux)

hQEMA8G6mPLFWtFSAQf/RQK9wCNIEU+rIvtniwaBx5FdrywOVN986w7V3VixdU+T
nHOj3hNWyZDqjRQHxki2x4clLtYSTs5OEP0JRKtcBa0G7m7mz1K8Daz1v5qqLpPo
2EdMIMdcOiw4cAef0n3jAn5CuinoreM/XESB5EM4QqqTZnQD4SMaQmTdJZVz0HS1
1xIgF6VDh9LeXNz0r5H3QJ8exGKtJIxDHpL537PMYC4wp9iSvFjRYW04S9cGYsEi
8hcQMNiaqJJS6Tw7oeUaBJflQI+HdssxOnRsKw3pSjGPPlH9dju4oi17crm5GYBK
8cZIDEQm3UIAMKbtCTN2UNv+3sPeGQqwPsecToiM59JLAU39LctFtPetiEkDAwxE
qIahkjlcjv0y/mSJvBd5jEjAVoKv3lp5Q8qNX7u0JKF9Bnz2A+Jvbf9jGqMzHaym
kcGLn53H0g4Rd0oC
=lhj7
-----END PGP MESSAGE-----
```

Boom, our very first encrypted file! Sweet!

In the `pillar/roles/base.sls` lets make a new line under our MOTD pillar and add the following:
```
encrypted:
  - file: |
      -----BEGIN PGP MESSAGE-----
      Version: GnuPG v2.0.22 (GNU/Linux)

      hQEMA8G6mPLFWtFSAQf/RQK9wCNIEU+rIvtniwaBx5FdrywOVN986w7V3VixdU+T
      nHOj3hNWyZDqjRQHxki2x4clLtYSTs5OEP0JRKtcBa0G7m7mz1K8Daz1v5qqLpPo
      2EdMIMdcOiw4cAef0n3jAn5CuinoreM/XESB5EM4QqqTZnQD4SMaQmTdJZVz0HS1
      1xIgF6VDh9LeXNz0r5H3QJ8exGKtJIxDHpL537PMYC4wp9iSvFjRYW04S9cGYsEi
      8hcQMNiaqJJS6Tw7oeUaBJflQI+HdssxOnRsKw3pSjGPPlH9dju4oi17crm5GYBK
      8cZIDEQm3UIAMKbtCTN2UNv+3sPeGQqwPsecToiM59JLAU39LctFtPetiEkDAwxE
      qIahkjlcjv0y/mSJvBd5jEjAVoKv3lp5Q8qNX7u0JKF9Bnz2A+Jvbf9jGqMzHaym
      kcGLn53H0g4Rd0oC
      =lhj7
      -----END PGP MESSAGE-----
```
*NOTE:* the indentation! It's super easy to have the encrypted text at the same indent level as `- file` which won't render properly.

(Mobile note: this example wont render right on mobile as the page width is compressed, it's best viewed on Desktop mode to see the indent)


Now that we've added GPG content to the pillar, we'll have to scroll to the top and ensure the `#!yaml|gpg` line exists, or else we'll get a rendering error because Salt doesn't know to render GPG unless we tell it to.

Excellent, now run `make` in the salt workspace folder (not in the vagrant VM) 
```
salt-workspace $ make
Salt is ready in ./dist. Enjoy!
```
and then you should be able to see the contents from the saltmaster VM:
```
[vagrant@saltmaster ~]$ sudo salt-call pillar.get encrypted:file
local:
    This is encrypted!
```

We can take this a step further, and create a file with the contents from pillar by adding a few lines to `salt/roles/base/init.sls`:
```
/tmp/encrypted_file.txt:
  file.managed:
    - contents: {{ salt['pillar.get']('encrypted:file') }}
```
then run `make`! Next, on the saltmaster `sudo salt-call state.highstate` should give the following result:

```
[vagrant@saltmaster ~]$ sudo salt-call state.highstate
local:
----------
          ID: motd
    Function: file.managed
        Name: /etc/motd
      Result: True
     Comment: File /etc/motd is in the correct state
     Started: 04:25:22.210978
    Duration: 6.1 ms
     Changes:
----------
          ID: /tmp/encrypted_file.txt
    Function: file.managed
      Result: True
     Comment: File /tmp/encrypted_file.txt updated
     Started: 04:25:22.217194
    Duration: 1.665 ms
     Changes:
              ----------
              diff:
                  New file

Summary for local
------------
Succeeded: 2 (changed=1)
Failed:    0
------------
Total states run:     2
Total run time:   7.765 ms
[vagrant@saltmaster ~]$ cat /tmp/encrypted_file.txt
This is encrypted!
```

This is the  [example code](https://github.com/BadgerOps/salt-workspace/commit/4e03669ca1f4039b41131ac4f010ece6bcd98fe0) - if you'd like to see the diff. I hope this post was helpful, and if there's any questions, feel free to comment below and let me know!

Thanks,

-BadgerOps