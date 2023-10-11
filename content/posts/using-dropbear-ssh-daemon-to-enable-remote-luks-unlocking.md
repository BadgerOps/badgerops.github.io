+++
title = "Using Dropbear ssh daemon to enable remote LUKS unlocking"
date = "2018-01-16T15:33:06Z"
draft = false
+++

Wow, that title is a mouthful - but if you're here, chances are you've been scouring the internet trying to figure out how to get remote LUKS unlock enabled, much like I was a few weeks ago. I finally got all the different parts working as expected, so here you go, the definitive guide to getting remote LUKS unlock enabled over SSH. (*definitive for my specific circumstances, with Ubuntu servers both on metal, and virtual, YMMV*)

For the purpose of this post, I'm assuming you've already got LUKS set up, my example container name is 'cryptroot'.
###### The TL;DR steps: 
(if you'd like a deeper explanation, I'm happy to chat, feel free to reach out!)

1: Install dropbear: `apt-get install dropbear`

2: Create `/etc/initramfs-tools/root/.ssh/authorized_keys` and insert any needed ssh public keys (anyone who needs to be able to access this ssh daemon)

3: Add network hardware module to `/etc/initramfs-tools/modules` - you can find it by typing `grep DRIVER /sys/class/net/eth0/device/uevent`

###### NOTE: 
For reference, we're taking advantage of the kernel parameter that allows you to do 'netboot' from an NFS server: https://www.kernel.org/doc/Documentation/filesystems/nfs/nfsroot.txt

4: Create `/etc/initramfs-tools/conf.d/network_config` with the contents of `export IP=<client-ip>:<nfs-server-ip(not required)>:<gw-ip>:<netmask>:<hostname>:<device>:<autoconf>` 

- (for the POC I did `export IP=dhcp` as I've got DHCP internally)
        Static IP example: 
`export IP=192.168.1.2::192.168.1.1:255.255.255.0:hostname:eth0:off` 

- Another note: the nfs-server-ip is omitted with a double :: between the client(host) IP and the GW IP. Any value can be omitted, but will require a :: (empty spot between the colon's) as a placeholder.

- Full example:
`export IP=<client-ip>:<nfs-server-ip>:<gw-ip>:<netmask>:<hostname>:<device>:<autoconf>:<dns0-ip>:<dns1-ip>`


5: To fix a issue where sometimes the network gets into a funky state when setting an IP in the initramfs and not resetting it on boot, add this to `/etc/network/interfaces`:

  `pre-up ip addr flush dev eth0` so it looks like: 

    auto eth0
    iface eth0 inet dhcp
        pre-up ip addr flush dev eth0

6: Create `/etc/initramfs-tools/hooks/mount_cryptroot` with the contents: 
   
    #!/bin/sh  
    # This script generates 2 scripts
    # /root/mount_cryptroot.sh and /root/.profile 
     
     
    if [ -z ${DESTDIR} ]; then
        exit
    fi
     
    SCRIPT="${DESTDIR}/root/mount_cryptroot.sh"
    cat > "${SCRIPT}" << 'EOF'
    #!/bin/sh
    CMD=
    while [ -z "$CMD" -o -z "`pidof askpass plymouth`" ]; do
      # we need to get the full command out of PS, which looks like this:
      # S     0   208   191 39316  4548 0:0   15:19 00:00:00 /sbin/cryptsetup -T 1 --allow-discards luksOpen /dev/disk/by-uuid/<uuid> cryptroot --key-file=-
      # So we cut
      CMD=`ps | grep cryptsetup | grep -v grep | cut -d'<' -f2`
      sleep 0.1
    done
    while [ -n "`pidof askpass plymouth`" ]; do
      $CMD && kill -9 `pidof askpass plymouth` && echo "Success"
    done
    EOF
     
    chmod +x "${SCRIPT}"
     
    cat > "${DESTDIR}/root/.profile" << EOF
    echo "Unlocking rootfs on `hostname`..."
     
    /root/mount_cryptroot.sh && exit 1 || echo "Run ./mount_cryptroot.sh to try unlocking again"
    echo "if you see the cryptroot error 'already exists', just press ctrl-d - not sure why it throws that error, but I'm booting!"
    EOF



The purpose of this is to automatically fire up a listener so you can ssh to the ip:port and immediately be prompted to enter the LUKS password.     
###### IMPORTANT:
 `chmod +x /etc/initramfs-tools/hooks/mount_cryptroot` so it will actually run (ask me how I know how important this is...)

If you want the daemon to listen on a different port, which is helpful, for example if you want a monitor to alert when a server is in 'waiting to unlock status' you can do the following:

6a/optional: Edit `/usr/share/initramfs-tools/scripts/init-premount/dropbear` and replace the startup line near the bottom, adding a `-p <portnumber>` flag:

    - /sbin/dropbear
    + /sbin/dropbear -p 2222


7: Update your initramfs `update-initramfs -u`

8: Reboot to test!


Once the box has rebooted initramfs will start the dropbear daemon and run the script we set ssh to the box and you should get the following prompt:

    ssh <hostname>:<port>                                                                                                                            
 
 
    BusyBox v1.21.1 (Ubuntu 1:1.21.0-1ubuntu1) built-in shell (ash)
    Enter 'help' for a list of built-in commands.
 
    Unlocking rootfs on <hostname>...
    Enter passphrase:

This is the `/root/mount_cryptroot.sh` script we had fire off using `/root/.profile`


Hopefully this was helpful to you! Feel free to add a comment or tweet me `@badgerops` if you've got questions/pointers.

Thanks for reading!

-BadgerOps