+++
title = "Forcing initramfs to load udev 70-persistent-net.rules"
date = "2018-02-14T22:48:18Z"
draft = false
+++

<!--kg-card-begin: markdown--><p>Hello fine readers,</p>
<p>Chances are you're scouring the googles much like I was all morning trying to figure out how to get <code>update-initramfs</code> to pull in the <code>70-persistent-net.rules</code> udev rule.</p>
<p>You may have stumbled on <a href="https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=618420">this debian bug</a> or <a href="https://bugs.launchpad.net/ubuntu/+source/initramfs-tools/+bug/1471391">this ubuntu bug</a> which coincidently ties in with my <a href="__GHOST_URL__/2018/01/16/using-dropbear-ssh-daemon-to-enable-remote-luks-unlocking/">remote LUKS unlocking</a> post.</p>
<p>I quickly found that <code>NEED_PERSISTENT_NET=yes</code> needed to be set, but it wasn't immediately obvious <em>where</em> that needed to be set as <code>update-initramfs</code> ignores environment variables. Well, I finally <a href="https://git.devuan.org/jaretcantu/eudev/blob/9dc53b6a06d64e349ee1aa9a69b022586eea95ab/debian/udev.README.Debian#L146">tracked down</a>  a reference to where you can set that variable.</p>
<h6 id="note">NOTE:</h6>
<p>In the case that link dies, or that line is removed here is the necessary information:</p>
<blockquote></blockquote>
<p>Usually network interfaces are renamed after the root file system has been mounted, so if the root file system is mounted over the network then the 70-persistent-net.rules file must be copied to the initramfs. In most cases this is done automatically, but some setups may require explicitly setting <code>&quot;export NEED\_PERSISTENT_NET=yes&quot; in a file in /etc/initramfs-tools/conf.d/ </code>. If 70-persistent-net.rules is copied to the initramfs then it must be updated every time a new interface is added.</p>
<p>and added it to my deployment script:</p>
<pre><code>echo &quot;export NEED_PERSISTENT_NET=yes&quot; &gt; /mnt/etc/initramfs-tools/conf.d/persistent_net_setup
</code></pre>
<p>which triggered the copying of  <code>70-persistent-net.rules</code> the next time I ran <code>update-initramfs</code></p>
<p>Hopefully this helps you out!</p>
<p>-BadgerOps</p>
<!--kg-card-end: markdown-->