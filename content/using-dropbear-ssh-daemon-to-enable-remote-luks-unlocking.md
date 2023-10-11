+++
title = "Using Dropbear ssh daemon to enable remote LUKS unlocking"
date = "2018-01-16T15:33:06Z"
draft = false
+++

<!--kg-card-begin: markdown--><p>Wow, that title is a mouthful - but if you're here, chances are you've been scouring the internet trying to figure out how to get remote LUKS unlock enabled, much like I was a few weeks ago. I finally got all the different parts working as expected, so here you go, the definitive guide to getting remote LUKS unlock enabled over SSH. (<em>definitive for my specific circumstances, with Ubuntu servers both on metal, and virtual, YMMV</em>)</p>
<p>For the purpose of this post, I'm assuming you've already got LUKS set up, my example container name is 'cryptroot'.</p>
<h6 id="thetldrsteps">The TL;DR steps:</h6>
<p>(if you'd like a deeper explanation, I'm happy to chat, feel free to reach out!)</p>
<p>1: Install dropbear: <code>apt-get install dropbear</code></p>
<p>2: Create <code>/etc/initramfs-tools/root/.ssh/authorized_keys</code> and insert any needed ssh public keys (anyone who needs to be able to access this ssh daemon)</p>
<p>3: Add network hardware module to <code>/etc/initramfs-tools/modules</code> - you can find it by typing <code>grep DRIVER /sys/class/net/eth0/device/uevent</code></p>
<h6 id="note">NOTE:</h6>
<p>For reference, we're taking advantage of the kernel parameter that allows you to do 'netboot' from an NFS server: <a href="https://www.kernel.org/doc/Documentation/filesystems/nfs/nfsroot.txt">https://www.kernel.org/doc/Documentation/filesystems/nfs/nfsroot.txt</a></p>
<p>4: Create <code>/etc/initramfs-tools/conf.d/network_config</code> with the contents of <code>export IP=&lt;client-ip&gt;:&lt;nfs-server-ip(not required)&gt;:&lt;gw-ip&gt;:&lt;netmask&gt;:&lt;hostname&gt;:&lt;device&gt;:&lt;autoconf&gt;</code></p>
<ul>
<li>
<p>(for the POC I did <code>export IP=dhcp</code> as I've got DHCP internally)<br>
Static IP example:<br>
<code>export IP=192.168.1.2::192.168.1.1:255.255.255.0:hostname:eth0:off</code></p>
</li>
<li>
<p>Another note: the nfs-server-ip is omitted with a double :: between the client(host) IP and the GW IP. Any value can be omitted, but will require a :: (empty spot between the colon's) as a placeholder.</p>
</li>
<li>
<p>Full example:<br>
<code>export IP=&lt;client-ip&gt;:&lt;nfs-server-ip&gt;:&lt;gw-ip&gt;:&lt;netmask&gt;:&lt;hostname&gt;:&lt;device&gt;:&lt;autoconf&gt;:&lt;dns0-ip&gt;:&lt;dns1-ip&gt;</code></p>
</li>
</ul>
<p>5: To fix a issue where sometimes the network gets into a funky state when setting an IP in the initramfs and not resetting it on boot, add this to <code>/etc/network/interfaces</code>:</p>
<p><code>pre-up ip addr flush dev eth0</code> so it looks like:</p>
<pre><code>auto eth0
iface eth0 inet dhcp
    pre-up ip addr flush dev eth0
</code></pre>
<p>6: Create <code>/etc/initramfs-tools/hooks/mount_cryptroot</code> with the contents:</p>
<pre><code>#!/bin/sh  
# This script generates 2 scripts
# /root/mount_cryptroot.sh and /root/.profile 
 
 
if [ -z ${DESTDIR} ]; then
    exit
fi
 
SCRIPT=&quot;${DESTDIR}/root/mount_cryptroot.sh&quot;
cat &gt; &quot;${SCRIPT}&quot; &lt;&lt; 'EOF'
#!/bin/sh
CMD=
while [ -z &quot;$CMD&quot; -o -z &quot;`pidof askpass plymouth`&quot; ]; do
  # we need to get the full command out of PS, which looks like this:
  # S     0   208   191 39316  4548 0:0   15:19 00:00:00 /sbin/cryptsetup -T 1 --allow-discards luksOpen /dev/disk/by-uuid/&lt;uuid&gt; cryptroot --key-file=-
  # So we cut
  CMD=`ps | grep cryptsetup | grep -v grep | cut -d'&lt;' -f2`
  sleep 0.1
done
while [ -n &quot;`pidof askpass plymouth`&quot; ]; do
  $CMD &amp;&amp; kill -9 `pidof askpass plymouth` &amp;&amp; echo &quot;Success&quot;
done
EOF
 
chmod +x &quot;${SCRIPT}&quot;
 
cat &gt; &quot;${DESTDIR}/root/.profile&quot; &lt;&lt; EOF
echo &quot;Unlocking rootfs on `hostname`...&quot;
 
/root/mount_cryptroot.sh &amp;&amp; exit 1 || echo &quot;Run ./mount_cryptroot.sh to try unlocking again&quot;
echo &quot;if you see the cryptroot error 'already exists', just press ctrl-d - not sure why it throws that error, but I'm booting!&quot;
EOF
</code></pre>
<p>The purpose of this is to automatically fire up a listener so you can ssh to the ip:port and immediately be prompted to enter the LUKS password.</p>
<h6 id="important">IMPORTANT:</h6>
<p><code>chmod +x /etc/initramfs-tools/hooks/mount_cryptroot</code> so it will actually run (ask me how I know how important this is...)</p>
<p>If you want the daemon to listen on a different port, which is helpful, for example if you want a monitor to alert when a server is in 'waiting to unlock status' you can do the following:</p>
<p>6a/optional: Edit <code>/usr/share/initramfs-tools/scripts/init-premount/dropbear</code> and replace the startup line near the bottom, adding a <code>-p &lt;portnumber&gt;</code> flag:</p>
<pre><code>- /sbin/dropbear
+ /sbin/dropbear -p 2222
</code></pre>
<p>7: Update your initramfs <code>update-initramfs -u</code></p>
<p>8: Reboot to test!</p>
<p>Once the box has rebooted initramfs will start the dropbear daemon and run the script we set ssh to the box and you should get the following prompt:</p>
<pre><code>ssh &lt;hostname&gt;:&lt;port&gt;                                                                                                                            


BusyBox v1.21.1 (Ubuntu 1:1.21.0-1ubuntu1) built-in shell (ash)
Enter 'help' for a list of built-in commands.

Unlocking rootfs on &lt;hostname&gt;...
Enter passphrase:
</code></pre>
<p>This is the <code>/root/mount_cryptroot.sh</code> script we had fire off using <code>/root/.profile</code></p>
<p>Hopefully this was helpful to you! Feel free to add a comment or tweet me <code>@badgerops</code> if you've got questions/pointers.</p>
<p>Thanks for reading!</p>
<p>-BadgerOps</p>
<!--kg-card-end: markdown-->