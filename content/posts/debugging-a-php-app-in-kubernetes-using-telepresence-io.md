+++
title = "Debugging a PHP app in Kubernetes using Telepresence.io"
date = "2019-10-03T14:41:04Z"
draft = false
+++

Hello folks,


Today we're going to talk about using [telepresence.io](https://www.telepresence.io) to debug PHP code running in Kubernetes using Telepresence. I'll refer you to the [Telepresence Introduction](https://www.telepresence.io/discussion/overview) page for an overview of what Telepresence can do for you, but if you're reading this you probably are already aware and just want the example code. So, let's get to it!

==if you want to skip all the discussion and get right to hacking, just scroll past the break for 'gimme the code, man' section==

Once you've read the Introduction, then the [installation guide](https://www.telepresence.io/reference/install) is your next stop. The specific version of Telepresence that introduced the ability to use xdebug for remote debugging is *0.102 (October 2, 2019)*  [you can read the changelog here](https://www.telepresence.io/reference/changelog) if you're interested in the details.

Alright, so lets set some assumptions here:

1: you are comfortable with PHP and using xdebug

* There are plenty of guides to getting xdebug working on the internet, I used the [phpstorm guide](https://www.jetbrains.com/help/phpstorm/configuring-xdebug.html)

* Note: I am also using the [browser debugger extension](jetbrains.com/help/phpstorm/browser-debugging-extensions.html) for chrome

2: I am using phpstorm for this example, feel free to follow along with your favorite editor

3: I am doing this from a Mac, but you could just as easily use Linux, all of the tools I use also work there. Windows, I honestly have no idea as I don't use Windows for any development work.

4: I am using both Kubernetes on my Docker for Desktop on Mac and EKS in AWS.

####Setup your environment

For this example, I'm just going to do a very simple 'hello world' PHP page that will also expose `phpinfo()` so you can see the environment variables.

######Step 1: 
Create yourself a new project in your `$editor_of_choice` and create your index.php with 'hello world' and/or `phpinfo()` in it.

==Note, if you're not using a Unix compliant shell, then don't use the cat > `file` << EOF line, more info on heredoc [here](https://en.wikipedia.org/wiki/Here_document#Unix_shells)==
```
mkdir -p ~/code/telepresenceDemo && cd ~/code/telepresenceDemo

cat > index.php << EOF
<html>
 <head>
  <title>PHP Test</title>
 </head>
 <body>
 <?php echo '<p>Hello World!</p>'; ?>
 <?php phpinfo(); ?>
 </body>
</html>

EOF
```
######Step 2: 
Create a Dockerfile to test with. I'm using the [official PHP](https://hub.docker.com/_/php)  apache docker build (apache for single container goodness. PHP-FPM + Nginx are usable as well and I may cover them in a future post)

This installs and enables xdebug and sets some custom xdebug options in the php.ini file. We also copy the index.php we created to `/var/www/html/index.php`
```
cat > Dockerfile << EOF
FROM php:7.2-apache
RUN pecl install xdebug-2.6.0
RUN docker-php-ext-enable xdebug
RUN echo "xdebug.remote_enable=1" >> /usr/local/etc/php/php.ini && \
    echo "xdebug.remote_host=localhost" >> /usr/local/etc/php/php.ini && \
    echo "xdebug.remote_port=9000" >> /usr/local/etc/php/php.ini && \ 
    echo "xdebug.remote_log=/var/log/xdebug.log" >> /usr/local/etc/php/php.ini 
    

COPY ./index.php /var/www/html
WORKDIR /var/www/html

EOF
```
######Step 3: 
build our example container
```
docker build -t mytelepresencetest:01 .
``` 

This container pulls from [upstream php](https://hub.docker.com/_/php) and we add our xdebug specific settings to it in the above Dockerfile.

######Step 4: 
Finally, assuming you already have `KUBECONFIG` set we can fire up Telepresence. Telepresence will use whatever Kubernetes config file you have in your env, or in `~/.kube/config`.

*  [more info on Kubernetes config file management here](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/)

```
telepresence --container-to-host 9000 --verbose --new-deployment tele-test --docker-run -p 8080:80 -v $(pwd):/var/www/html mytelepresencetest:01
```
In this example, I'm mounting the local (pwd) directory to `/var/www/html` which allows me to edit the index.php in my editor and have it automatically reflect inside the container we're running. You could also specify the explicit path to your code folder if you don't launch Telepresence from the code folder. 

If you created the folder as noted above, this would look like: 
```
telepresence --container-to-host 9000 --verbose --new-deployment tele-test --docker-run -p 8080:80 -v ~/code/telepresenceDemo:/var/www/html mytelepresencetest:01
```
Here is how this command looks as it executes on my machine (on October 3rd 2019)
```
telepresence --container-to-host 9000 --verbose --new-deployment tele-test --docker-run -p 8080:80 -v $(pwd):/var/www/html mytelepresencetest:01
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
```
Awesome, we see that apache has launched, and we can see the apache logs in our terminal window.

######Step 5:
 Open a browser to http://localhost:8080 we should see our "Hello, World" statement followed by `phpinfo()` output. Here is what you should see in your Telepresence output:

```
(this line included for continuity from above example block) 

[Thu Oct 03 17:04:35.422032 2019] [core:notice] [pid 7] AH00094: Command line: 'apache2 -D FOREGROUND'

172.17.0.1 - - [03/Oct/2019:17:11:08 +0000] "GET / HTTP/1.1" 200 25347 "-" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36"
172.17.0.1 - - [03/Oct/2019:17:11:13 +0000] "GET /favicon.ico HTTP/1.1" 404 502 "http://localhost:8080/" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36"
```
The key line here is `--container-to-host 9000` - this creates a connection from the container back to your computer at `localhost:9000` so your xdebug listener can receive data from the code executing in that container.

Now that you have your Telepresence process running swap over to your Editor - again, I'm using PHPStorm + Chrome + the PHPStorm xdebug exension - and turn on your xdebug listener. Also turn on your xdebug extension in your browser. (Configuration instruction links are included for both of these in the top of this blog post under assumption #1)

Once those are running you should be able to refresh your page and see a breakpoint hit in PHPStorm! (The first time you should get a pop up asking for you to map the code to match what you have in your local path vs remote path)

In your editor, go modify your `index.php` to be "Hello, Telepresence" instead of "Hello, World" and refresh your browser to see the changes reflected in the container.

Now if this were an app that needed access to resources hosted in your Kubernetes cluster, you'd be able to hit those resources from your code that is technically running 'locally' on your box, giving you the ability to hit breakpoints and step through code without having to host all of those resources locally. Nice. Huge shoutout to awesome folks at Datawire who wrote this tool!

The way this all works is Telepresence spins up 2 proxy containers - one in Docker locally on your box, the other in your Kubernetes cluster. Then it routes all traffic from your local Docker container you built and ran through the 'local' Docker proxy container, to the remote Kubernetes proxy container with this chunk of the command:
`--docker-run -p 8080:80 -v $(pwd):/var/www/html mytelepresencetest:01`
through the Kubernetes proxy side, giving you access to any resources your Kubernetes cluster has available.


If this doesn't work for you - make sure you've correctly configured your editor as noted in Assumption #1 at the top of this post. If you're still having issues, swing by twitter and ask [@badgerops](https://twitter.com/badgerops) or check the [github issues](https://github.com/telepresenceio/telepresence) to see if someone else is having a similar issue.

If you think Telepresence is awesome and want to contribute, [head over to their github](https://github.com/telepresenceio/telepresence) and get your sweet [Hacktoberfest](https://hacktoberfest.digitalocean.com/) PR's in. (Assuming you're reading this in October!)

--------

##Just the steps aka, 'gimme the code, man'


######Step 1: 
Create yourself a new project in your `$editor_of_choice` and create your index.php with 'hello world' and/or `phpinfo()` in it.

######Or, if you want manual steps:

==Note, if you're not using a Unix compliant shell, then don't use the cat > `file` << EOF line, more info on heredoc [here](https://en.wikipedia.org/wiki/Here_document#Unix_shells)==

Create your code folder
```
mkdir -p ~/code/telepresenceDemo && cd ~/code/telepresenceDemo
```
Create your index.php file
```
cat > index.php << EOF
<html>
 <head>
  <title>PHP Test</title>
 </head>
 <body>
 <?php echo '<p>Hello World!</p>'; ?>
 <?php phpinfo(); ?>
 </body>
</html>

EOF
```
######Step 2: 
Create a Dockerfile to test with. I'm using the [official PHP](https://hub.docker.com/_/php)  apache docker build (apache for single container goodness. PHP-FPM + Nginx are usable as well)
```
cat > Dockerfile << EOF
FROM php:7.2-apache
RUN pecl install xdebug-2.6.0
RUN docker-php-ext-enable xdebug
RUN echo "xdebug.remote_enable=1" >> /usr/local/etc/php/php.ini && \
    echo "xdebug.remote_host=localhost" >> /usr/local/etc/php/php.ini && \
    echo "xdebug.remote_port=9000" >> /usr/local/etc/php/php.ini && \ 
    echo "xdebug.remote_log=/var/log/xdebug.log" >> /usr/local/etc/php/php.ini 
    

COPY ./index.php /var/www/html
WORKDIR /var/www/html

EOF
```
######Step 3: 
Build our example container
```
docker build -t mytelepresencetest:01 .
``` 

######Step 4: 
~~Profit~~ Run the thing (Assuming pwd is your code repo):
```
telepresence --container-to-host 9000 --verbose --new-deployment tele-test --docker-run -p 8080:80 -v $(pwd):/var/www/html mytelepresencetest:01
```
######Step 5:
Start up xdebug listener in your editor, open your browser to http://localhost:8080 and start stepping through code! The key line here is `--container-to-host 9000` - this creates a connection from the container back to your computer at `localhost:9000` so your xdebug listener can receive data from the code executing in that container.

If this doesn't work for you - make sure you've correctly configured your editor as noted in Assumption #1 at the top of this post. If you're still having issues, swing by twitter and ask [@badgerops](https://twitter.com/badgerops) or check the [github issues](https://github.com/telepresenceio/telepresence) to see if someone else is having a similar issue.

If you think Telepresence is awesome and want to contribute, [head over to their github](https://github.com/telepresenceio/telepresence) and get your sweet [Hacktoberfest](https://hacktoberfest.digitalocean.com/) PR's in. (Assuming you're reading this in October!)

Hope this helps you out, Cheers!

-BadgerOps

twitter: [@badgerops](https://twitter.com/badgerops)