+++
title = "Debugging a PHP app in Kubernetes using Telepresence.io"
date = "2019-10-03T14:41:04Z"
draft = false
+++

<!--kg-card-begin: markdown--><p>Hello folks,</p>
<p>Today we're going to talk about using <a href="https://www.telepresence.io">telepresence.io</a> to debug PHP code running in Kubernetes using Telepresence. I'll refer you to the <a href="https://www.telepresence.io/discussion/overview">Telepresence Introduction</a> page for an overview of what Telepresence can do for you, but if you're reading this you probably are already aware and just want the example code. So, let's get to it!</p>
<p><mark>if you want to skip all the discussion and get right to hacking, just scroll past the break for 'gimme the code, man' section</mark></p>
<p>Once you've read the Introduction, then the <a href="https://www.telepresence.io/reference/install">installation guide</a> is your next stop. The specific version of Telepresence that introduced the ability to use xdebug for remote debugging is <em>0.102 (October 2, 2019)</em>  <a href="https://www.telepresence.io/reference/changelog">you can read the changelog here</a> if you're interested in the details.</p>
<p>Alright, so lets set some assumptions here:</p>
<p>1: you are comfortable with PHP and using xdebug</p>
<ul>
<li>
<p>There are plenty of guides to getting xdebug working on the internet, I used the <a href="https://www.jetbrains.com/help/phpstorm/configuring-xdebug.html">phpstorm guide</a></p>
</li>
<li>
<p>Note: I am also using the <a href="jetbrains.com/help/phpstorm/browser-debugging-extensions.html">browser debugger extension</a> for chrome</p>
</li>
</ul>
<p>2: I am using phpstorm for this example, feel free to follow along with your favorite editor</p>
<p>3: I am doing this from a Mac, but you could just as easily use Linux, all of the tools I use also work there. Windows, I honestly have no idea as I don't use Windows for any development work.</p>
<p>4: I am using both Kubernetes on my Docker for Desktop on Mac and EKS in AWS.</p>
<h4 id="setupyourenvironment">Setup your environment</h4>
<p>For this example, I'm just going to do a very simple 'hello world' PHP page that will also expose <code>phpinfo()</code> so you can see the environment variables.</p>
<h6 id="step1">Step 1:</h6>
<p>Create yourself a new project in your <code>$editor_of_choice</code> and create your index.php with 'hello world' and/or <code>phpinfo()</code> in it.</p>
<p><mark>Note, if you're not using a Unix compliant shell, then don't use the cat &gt; <code>file</code> &lt;&lt; EOF line, more info on heredoc <a href="https://en.wikipedia.org/wiki/Here_document#Unix_shells">here</a></mark></p>
<pre><code>mkdir -p ~/code/telepresenceDemo &amp;&amp; cd ~/code/telepresenceDemo

cat &gt; index.php &lt;&lt; EOF
&lt;html&gt;
 &lt;head&gt;
  &lt;title&gt;PHP Test&lt;/title&gt;
 &lt;/head&gt;
 &lt;body&gt;
 &lt;?php echo '&lt;p&gt;Hello World!&lt;/p&gt;'; ?&gt;
 &lt;?php phpinfo(); ?&gt;
 &lt;/body&gt;
&lt;/html&gt;

EOF
</code></pre>
<h6 id="step2">Step 2:</h6>
<p>Create a Dockerfile to test with. I'm using the <a href="https://hub.docker.com/_/php">official PHP</a>  apache docker build (apache for single container goodness. PHP-FPM + Nginx are usable as well and I may cover them in a future post)</p>
<p>This installs and enables xdebug and sets some custom xdebug options in the php.ini file. We also copy the index.php we created to <code>/var/www/html/index.php</code></p>
<pre><code>cat &gt; Dockerfile &lt;&lt; EOF
FROM php:7.2-apache
RUN pecl install xdebug-2.6.0
RUN docker-php-ext-enable xdebug
RUN echo &quot;xdebug.remote_enable=1&quot; &gt;&gt; /usr/local/etc/php/php.ini &amp;&amp; \
    echo &quot;xdebug.remote_host=localhost&quot; &gt;&gt; /usr/local/etc/php/php.ini &amp;&amp; \
    echo &quot;xdebug.remote_port=9000&quot; &gt;&gt; /usr/local/etc/php/php.ini &amp;&amp; \ 
    echo &quot;xdebug.remote_log=/var/log/xdebug.log&quot; &gt;&gt; /usr/local/etc/php/php.ini 
    

COPY ./index.php /var/www/html
WORKDIR /var/www/html

EOF
</code></pre>
<h6 id="step3">Step 3:</h6>
<p>build our example container</p>
<pre><code>docker build -t mytelepresencetest:01 .
</code></pre>
<p>This container pulls from <a href="https://hub.docker.com/_/php">upstream php</a> and we add our xdebug specific settings to it in the above Dockerfile.</p>
<h6 id="step4">Step 4:</h6>
<p>Finally, assuming you already have <code>KUBECONFIG</code> set we can fire up Telepresence. Telepresence will use whatever Kubernetes config file you have in your env, or in <code>~/.kube/config</code>.</p>
<ul>
<li><a href="https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/">more info on Kubernetes config file management here</a></li>
</ul>
<pre><code>telepresence --container-to-host 9000 --verbose --new-deployment tele-test --docker-run -p 8080:80 -v $(pwd):/var/www/html mytelepresencetest:01
</code></pre>
<p>In this example, I'm mounting the local (pwd) directory to <code>/var/www/html</code> which allows me to edit the index.php in my editor and have it automatically reflect inside the container we're running. You could also specify the explicit path to your code folder if you don't launch Telepresence from the code folder.</p>
<p>If you created the folder as noted above, this would look like:</p>
<pre><code>telepresence --container-to-host 9000 --verbose --new-deployment tele-test --docker-run -p 8080:80 -v ~/code/telepresenceDemo:/var/www/html mytelepresencetest:01
</code></pre>
<p>Here is how this command looks as it executes on my machine (on October 3rd 2019)</p>
<pre><code>telepresence --container-to-host 9000 --verbose --new-deployment tele-test --docker-run -p 8080:80 -v $(pwd):/var/www/html mytelepresencetest:01
T: How Telepresence uses sudo: https://www.telepresence.io/reference/install#dependencies
T: Invoking sudo. Please enter your sudo password.
Password:
T: Volumes are rooted at $TELEPRESENCE_ROOT. See https://telepresence.io/howto/volumes.html for details.
T: Starting network proxy to cluster using new Deployment tele-test

T: No traffic is being forwarded from the remote Deployment to your local machine. You can use the --expose option to specify which ports you want to forward.

T: Forwarding container port 9000 to host port 9000.
T: Setup complete. Launching your container.
AH00558: apache2: Could not reliably determine the server's fully qualified domain name, using 172.17.0.2. Set the 'ServerName' directive globally to suppress this message
AH00558: apache2: Could not reliably determine the server's fully qualified domain name, using 172.17.0.2. Set the 'ServerName' directive globally to suppress this message
[Thu Oct 03 17:04:35.421678 2019] [mpm_prefork:notice] [pid 7] AH00163: Apache/2.4.38 (Debian) PHP/7.2.23 configured -- resuming normal operations
[Thu Oct 03 17:04:35.422032 2019] [core:notice] [pid 7] AH00094: Command line: 'apache2 -D FOREGROUND'
</code></pre>
<p>Awesome, we see that apache has launched, and we can see the apache logs in our terminal window.</p>
<h6 id="step5">Step 5:</h6>
<p>Open a browser to <a href="http://localhost:8080">http://localhost:8080</a> we should see our &quot;Hello, World&quot; statement followed by <code>phpinfo()</code> output. Here is what you should see in your Telepresence output:</p>
<pre><code>(this line included for continuity from above example block) 

[Thu Oct 03 17:04:35.422032 2019] [core:notice] [pid 7] AH00094: Command line: 'apache2 -D FOREGROUND'

172.17.0.1 - - [03/Oct/2019:17:11:08 +0000] &quot;GET / HTTP/1.1&quot; 200 25347 &quot;-&quot; &quot;Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36&quot;
172.17.0.1 - - [03/Oct/2019:17:11:13 +0000] &quot;GET /favicon.ico HTTP/1.1&quot; 404 502 &quot;http://localhost:8080/&quot; &quot;Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36&quot;
</code></pre>
<p>The key line here is <code>--container-to-host 9000</code> - this creates a connection from the container back to your computer at <code>localhost:9000</code> so your xdebug listener can receive data from the code executing in that container.</p>
<p>Now that you have your Telepresence process running swap over to your Editor - again, I'm using PHPStorm + Chrome + the PHPStorm xdebug exension - and turn on your xdebug listener. Also turn on your xdebug extension in your browser. (Configuration instruction links are included for both of these in the top of this blog post under assumption #1)</p>
<p>Once those are running you should be able to refresh your page and see a breakpoint hit in PHPStorm! (The first time you should get a pop up asking for you to map the code to match what you have in your local path vs remote path)</p>
<p>In your editor, go modify your <code>index.php</code> to be &quot;Hello, Telepresence&quot; instead of &quot;Hello, World&quot; and refresh your browser to see the changes reflected in the container.</p>
<p>Now if this were an app that needed access to resources hosted in your Kubernetes cluster, you'd be able to hit those resources from your code that is technically running 'locally' on your box, giving you the ability to hit breakpoints and step through code without having to host all of those resources locally. Nice. Huge shoutout to awesome folks at Datawire who wrote this tool!</p>
<p>The way this all works is Telepresence spins up 2 proxy containers - one in Docker locally on your box, the other in your Kubernetes cluster. Then it routes all traffic from your local Docker container you built and ran through the 'local' Docker proxy container, to the remote Kubernetes proxy container with this chunk of the command:<br>
<code>--docker-run -p 8080:80 -v $(pwd):/var/www/html mytelepresencetest:01</code><br>
through the Kubernetes proxy side, giving you access to any resources your Kubernetes cluster has available.</p>
<p>If this doesn't work for you - make sure you've correctly configured your editor as noted in Assumption #1 at the top of this post. If you're still having issues, swing by twitter and ask <a href="https://twitter.com/badgerops">@badgerops</a> or check the <a href="https://github.com/telepresenceio/telepresence">github issues</a> to see if someone else is having a similar issue.</p>
<p>If you think Telepresence is awesome and want to contribute, <a href="https://github.com/telepresenceio/telepresence">head over to their github</a> and get your sweet <a href="https://hacktoberfest.digitalocean.com/">Hacktoberfest</a> PR's in. (Assuming you're reading this in October!)</p>
<hr>
<h2 id="justthestepsakagimmethecodeman">Just the steps aka, 'gimme the code, man'</h2>
<h6 id="step1">Step 1:</h6>
<p>Create yourself a new project in your <code>$editor_of_choice</code> and create your index.php with 'hello world' and/or <code>phpinfo()</code> in it.</p>
<h6 id="orifyouwantmanualsteps">Or, if you want manual steps:</h6>
<p><mark>Note, if you're not using a Unix compliant shell, then don't use the cat &gt; <code>file</code> &lt;&lt; EOF line, more info on heredoc <a href="https://en.wikipedia.org/wiki/Here_document#Unix_shells">here</a></mark></p>
<p>Create your code folder</p>
<pre><code>mkdir -p ~/code/telepresenceDemo &amp;&amp; cd ~/code/telepresenceDemo
</code></pre>
<p>Create your index.php file</p>
<pre><code>cat &gt; index.php &lt;&lt; EOF
&lt;html&gt;
 &lt;head&gt;
  &lt;title&gt;PHP Test&lt;/title&gt;
 &lt;/head&gt;
 &lt;body&gt;
 &lt;?php echo '&lt;p&gt;Hello World!&lt;/p&gt;'; ?&gt;
 &lt;?php phpinfo(); ?&gt;
 &lt;/body&gt;
&lt;/html&gt;

EOF
</code></pre>
<h6 id="step2">Step 2:</h6>
<p>Create a Dockerfile to test with. I'm using the <a href="https://hub.docker.com/_/php">official PHP</a>  apache docker build (apache for single container goodness. PHP-FPM + Nginx are usable as well)</p>
<pre><code>cat &gt; Dockerfile &lt;&lt; EOF
FROM php:7.2-apache
RUN pecl install xdebug-2.6.0
RUN docker-php-ext-enable xdebug
RUN echo &quot;xdebug.remote_enable=1&quot; &gt;&gt; /usr/local/etc/php/php.ini &amp;&amp; \
    echo &quot;xdebug.remote_host=localhost&quot; &gt;&gt; /usr/local/etc/php/php.ini &amp;&amp; \
    echo &quot;xdebug.remote_port=9000&quot; &gt;&gt; /usr/local/etc/php/php.ini &amp;&amp; \ 
    echo &quot;xdebug.remote_log=/var/log/xdebug.log&quot; &gt;&gt; /usr/local/etc/php/php.ini 
    

COPY ./index.php /var/www/html
WORKDIR /var/www/html

EOF
</code></pre>
<h6 id="step3">Step 3:</h6>
<p>Build our example container</p>
<pre><code>docker build -t mytelepresencetest:01 .
</code></pre>
<h6 id="step4">Step 4:</h6>
<p><s>Profit</s> Run the thing (Assuming pwd is your code repo):</p>
<pre><code>telepresence --container-to-host 9000 --verbose --new-deployment tele-test --docker-run -p 8080:80 -v $(pwd):/var/www/html mytelepresencetest:01
</code></pre>
<h6 id="step5">Step 5:</h6>
<p>Start up xdebug listener in your editor, open your browser to <a href="http://localhost:8080">http://localhost:8080</a> and start stepping through code! The key line here is <code>--container-to-host 9000</code> - this creates a connection from the container back to your computer at <code>localhost:9000</code> so your xdebug listener can receive data from the code executing in that container.</p>
<p>If this doesn't work for you - make sure you've correctly configured your editor as noted in Assumption #1 at the top of this post. If you're still having issues, swing by twitter and ask <a href="https://twitter.com/badgerops">@badgerops</a> or check the <a href="https://github.com/telepresenceio/telepresence">github issues</a> to see if someone else is having a similar issue.</p>
<p>If you think Telepresence is awesome and want to contribute, <a href="https://github.com/telepresenceio/telepresence">head over to their github</a> and get your sweet <a href="https://hacktoberfest.digitalocean.com/">Hacktoberfest</a> PR's in. (Assuming you're reading this in October!)</p>
<p>Hope this helps you out, Cheers!</p>
<p>-BadgerOps</p>
<p>twitter: <a href="https://twitter.com/badgerops">@badgerops</a></p>
<!--kg-card-end: markdown-->