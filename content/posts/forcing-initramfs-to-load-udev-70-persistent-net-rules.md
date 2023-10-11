+++
title = "Forcing initramfs to load udev 70-persistent-net.rules"
date = "2018-02-14T22:48:18Z"
draft = false
+++

Hello fine readers,

Chances are you're scouring the googles much like I was all morning trying to figure out how to get `update-initramfs` to pull in the `70-persistent-net.rules` udev rule.

You may have stumbled on [this debian bug](https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=618420) or [this ubuntu bug](https://bugs.launchpad.net/ubuntu/+source/initramfs-tools/+bug/1471391) which coincidently ties in with my [remote LUKS unlocking](__GHOST_URL__/2018/01/16/using-dropbear-ssh-daemon-to-enable-remote-luks-unlocking/) post.

I quickly found that `NEED_PERSISTENT_NET=yes` needed to be set, but it wasn't immediately obvious _where_ that needed to be set as `update-initramfs` ignores environment variables. Well, I finally [tracked down](https://git.devuan.org/jaretcantu/eudev/blob/9dc53b6a06d64e349ee1aa9a69b022586eea95ab/debian/udev.README.Debian#L146)  a reference to where you can set that variable.
###### NOTE:
In the case that link dies, or that line is removed here is the necessary information:
> 
Usually network interfaces are renamed after the root file system has been mounted, so if the root file system is mounted over the network then the 70-persistent-net.rules file must be copied to the initramfs. In most cases this is done automatically, but some setups may require explicitly setting `"export NEED\_PERSISTENT_NET=yes" in a file in /etc/initramfs-tools/conf.d/ `. If 70-persistent-net.rules is copied to the initramfs then it must be updated every time a new interface is added.

and added it to my deployment script:
```
echo "export NEED_PERSISTENT_NET=yes" > /mnt/etc/initramfs-tools/conf.d/persistent_net_setup
```
which triggered the copying of  `70-persistent-net.rules` the next time I ran `update-initramfs`

Hopefully this helps you out!

-BadgerOps