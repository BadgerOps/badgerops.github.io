+++
title = "Creating a Raspberry Pi based, Resin.io powered speed test app"
date = "2017-05-03T22:46:17Z"
draft = false
+++

<!--kg-card-begin: markdown--><p>I first wrote <a href="https://github.com/BadgerOps/rpi-speedtest">this app</a> back in February of 2016 when I first stumbled across <a href="https://resin.io">resin.io</a>. It worked ok, and I left it running for a couple of months before repurposing the Pi for other uses.</p>
<p>Then I saw the announcement for <a href="https://resin.io/blog/introducing-resinos/">ResinOS</a> and the release of the 2.0 version. This got me interested in doing some of my 'todo' items on the project, including adding support for the buttons on the <a href="https://www.adafruit.com/product/1109">Adafruit LCD Plate</a> that I used for the original project.</p>
<h6 id="thecodepart">The code part:</h6>
<p>First off, I'm not a 'trained' developer. While I had some excellent mentoring with Python in a previous job, I'm pretty much self-taught/hacker in the 'that code is really hacky' sense. (I'd love feedback on ways to improve this code!)</p>
<p>With that in mind, I started refactoring the original code, but then decided I wanted a fresh start without some of the assumptions (and hacky shortcuts) I made initially.</p>
<p>The worst part of my initial program was the while loop:</p>
<pre><code>def main(self):
        self.setup()
        while True:
            try:
                self.checkspeed()
            except Exception as e:
                print &quot;could not check speed: %s&quot; %(e)
            try:
                self.printspeed()
            except Exception as e:
                print &quot;could not display speed: %s&quot; %(e)
            time.sleep(3600) 
</code></pre>
<p>It was quick, dirty, and ugly. Blocking for 3600 seconds in a loop? Bad badger!</p>
<p>I wanted to have support for the buttons on the LCD Plate, as well as better handling of the tasks, specifically running the speedtest at a specified interval.</p>
<p>With this in mind, I fired up a <a href="https://github.com/BadgerOps/resin-speedtest">new repo</a> and got to work.</p>
<p>I knew that I wanted to thread the LCD + Buttons away from the main thread so the buttons would be more responsive. I also wanted to add some support for adding more functions to the buttons in a easily extended manner, so I decided to use a dispatch dictionary, which essentially allows me to run a function based on a key, and optionally pass in data for that function. I'll probably rewrite this to align with <a href="https://www.python.org/dev/peps/pep-0443/">PEP443</a> - but for now its working so I'm not going to get too much deeper there for now. Working is better than perfect, right? (I decided to stop rewriting code and blog about it instead)</p>
<p>I also <a href="https://github.com/BadgerOps/resin-speedtest/blob/master/libs/LcdPlate.py#L15">passed the Main thread</a> into the LCD Plate thread to give some cross thread communication - for example, hitting 'select' on the plate <a href="https://github.com/BadgerOps/resin-speedtest/blob/master/libs/LcdPlate.py#L21">triggers a force re-run</a> of <a href="https://github.com/BadgerOps/resin-speedtest/blob/master/SpeedTestCheck.py#L37">the speedcheck</a>.</p>
<p>Migrating the LCD Plate to its own thread and tighting up the while loop gave a very noticeable improvement to button performance. My initial attempt had me trying to press the buttons 2-4 times to get a response, now its first click response as expected, woot!</p>
<p>Beyond these things I mentioned, the code is pretty straightforward, feel free to comment if there's something that doesn't make sense, and I'll do my best to clarify.</p>
<hr>
<h6 id="theresiniopart">The Resin (<a href="resin.io">.io!</a>) part:</h6>
<p><em>Note: If you're wanting to follow along, then fork <a href="https://github.com/BadgerOps/resin-speedtest">my repo</a> and clone it locally before doing the following.</em></p>
<p>If you haven't played with Resin, and you have a spare Pi, Beagleboard, Chip, or <a href="https://docs.resin.io/hardware/devices/">one of the many</a> other supported boards, then take 10 minutes, goto <a href="https://resin.io/">https://resin.io/</a> and click the friendly blue 'Get started now' button. Deploying a simple 'hello world' app is surprisingly simple and rewarding.</p>
<p>You'll see in the <a href="https://github.com/BadgerOps/resin-speedtest">repo</a>, that I've got a <a href="https://github.com/BadgerOps/resin-speedtest/blob/master/Dockerfile.template">Dockerfile.template</a> which allows the project to seamlessly support multiple Arches, <a href="https://docs.resin.io/deployment/docker-templates/">documentation here</a>. Now, with this said, this particular project will only work on a Raspberry Pi at this point, but it could conceivably be ported to other devices, and why not support that in the Dockerfile?</p>
<p>Getting the app committed and built by Resin is incredibly simple. If you created an account already, all you have to do is make sure you're on the <a href="https://dashboard.resin.io/apps">applications</a> page, and you should see a 'create new app' tile. Enter the name and architecture of your device, in this case I called it &quot;Speedtest App&quot; and the device is a Rpi 3. Once you click the 'create new application' button, you'll be presented with a ResinOS download. Using Etcher, or your flashing utility of choice, write that to your SD card and boot your Pi.</p>
<p>While we're waiting for the Pi to boot, look in the upper right hand corner of the page, and you'll see a string <code>git remote add resin username@git.resin.io:username/speedtest.git</code>. Copy that, and make sure you're in the repo you cloned earlier. Once thats done, you should be able to simply run <code>git push resin</code> and it will build and upload the application.</p>
<p>Once that is done, head back over to the application you created before and watch it download and run. The initial install takes a while because there's a lot of code that gets compiled for the i2c support for the LCD Plate.</p>
<hr>
<h6 id="thefinaltidbitspart">The final tidbits part:</h6>
<p>While this is a much better implementation than my first pass, there's a lot more I'd like to do:</p>
<ul>
<li>Build a better menu structure vs having a single button mapped to each item</li>
<li>Add ability to select speedtest polling time from menu</li>
<li>Scrolling text and ability to show full URL tested</li>
<li>Custom speedtest endpoints</li>
</ul>
<p>Right now, the buttons are as follows:</p>
<ul>
<li>Select: re-run the speedtest on demand</li>
<li>Up: Show local IP Address</li>
<li>Down: Show speedtest.net server ID that current speedtest was ran against</li>
<li>Right: Show current speedtest</li>
<li>Left: Show previous speedtest</li>
</ul>
<p>I pay for 40mb down, 20mb up, so I set it to turn the LCD red if the speed is below 35mb or green if the speed is above 35. This can easily be adjusted by editing the <code>self.netspeed</code> dictionary in the SpeedTestCheck.py <strong>init</strong>.py function:</p>
<pre><code>    def __init__(self):
        self.netspeed = {'up': 20, 'down': 40 }
</code></pre>
<p>Feel free to comment below, or open a issue in the git repo with questions or comments. Thanks for reading!</p>
<p>-BadgerOps</p>
<!--kg-card-end: markdown-->