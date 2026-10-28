---
title: "smtp socket: malformed response on a FIPS 140-2 system"
slug: "smtp-socket-malformed-response-on-a-fips140-2-sytstem"
date: 2024-01-06T16:56:24Z
lastmod: 2024-01-06T16:56:24Z
draft: false
description: "Ok, this is a very highly specific post - but I hope it is useful for that sysadmin who's tearing their hair out trying to figure out wtf is going on with smtp failing with a vague error message. Recently, I was configuring a Postfix…"
topics: []
aliases: ["/2024/01/06/smtp-socket-malformed-response-on-a-fips140-2-sytstem/"]
migration_source: ghost
---
<p>Ok, this is a very highly specific post - but I hope it is useful for that sysadmin who's tearing their hair out trying to figure out wtf is going on with smtp failing with a vague error message.</p><p>Recently, I was configuring a Postfix SMTP relay on a FIPS140-2 enabled system, and had a weird error that I hadn't ever seen before:</p><pre><code class="language-bash">warning: private/smtp socket: malformed response
warning: transport smtp failure -- see a previous warning/fatal/panic logfile record for the problem description
warning: process /usr/libexec/postfix/smtp pid  killed by signal 11
warning: /usr/libexec/postfix/smtp: bad command startup -- throttling
</code></pre>
<p>The <code>warning: private/smtp socket: malformed response</code> line is specifically what the error was. </p><p>Googling this issue turns up mostly chrooted postfix issues, or incorrect permissions on the <code>/etc/services</code> file. Not a lot of useful information for my specific issue!</p><p>In <a href="https://access.redhat.com/solutions/6958957" rel="noreferrer">this Red Hat Knowledgebase article</a> I finally found the correct answer! Now, it's obviously paywalled behind a Red Hat subscription, however knowing the magic string to search for turns up this <a href="https://unix.stackexchange.com/questions/440665/postfix-configuration-issue-with-fips-on-centos-7-mailgun-relay" rel="noreferrer">stackoverflow article</a> and we see that converting the hashing function from <code>md5</code> which is disabled on a FIPS 140-2 enabled system to <code>sha256</code> by running the following commands:</p><pre><code class="language-bash"># postconf -e smtp_tls_fingerprint_digest=sha256
# postconf -e smtpd_tls_fingerprint_digest=sha256
# systemctl restart postfix
</code></pre>
<p>You can also just add the two lines to your <code>/etc/postfix/main.cf</code> file, whatever floats your boat. It would be <em>super</em> if they were in that file commented out, but they're not (at least not on RHEL 8.x)</p><p>That's it, that's the blog post. Go forth and send emails.</p><p>-BadgerOps</p>
