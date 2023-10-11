+++
title = "Creating a Raspberry Pi based, Resin.io powered speed test app"
date = "2017-05-03T22:46:17Z"
draft = false
+++

I first wrote [this app](https://github.com/BadgerOps/rpi-speedtest) back in February of 2016 when I first stumbled across [resin.io](https://resin.io). It worked ok, and I left it running for a couple of months before repurposing the Pi for other uses.

Then I saw the announcement for [ResinOS](https://resin.io/blog/introducing-resinos/) and the release of the 2.0 version. This got me interested in doing some of my 'todo' items on the project, including adding support for the buttons on the [Adafruit LCD Plate](https://www.adafruit.com/product/1109) that I used for the original project.

###### The code part:

First off, I'm not a 'trained' developer. While I had some excellent mentoring with Python in a previous job, I'm pretty much self-taught/hacker in the 'that code is really hacky' sense. (I'd love feedback on ways to improve this code!)

With that in mind, I started refactoring the original code, but then decided I wanted a fresh start without some of the assumptions (and hacky shortcuts) I made initially.

The worst part of my initial program was the while loop:
```
def main(self):
        self.setup()
        while True:
            try:
                self.checkspeed()
            except Exception as e:
                print "could not check speed: %s" %(e)
            try:
                self.printspeed()
            except Exception as e:
                print "could not display speed: %s" %(e)
            time.sleep(3600) 
```
It was quick, dirty, and ugly. Blocking for 3600 seconds in a loop? Bad badger! 

I wanted to have support for the buttons on the LCD Plate, as well as better handling of the tasks, specifically running the speedtest at a specified interval.

With this in mind, I fired up a [new repo](https://github.com/BadgerOps/resin-speedtest) and got to work.

I knew that I wanted to thread the LCD + Buttons away from the main thread so the buttons would be more responsive. I also wanted to add some support for adding more functions to the buttons in a easily extended manner, so I decided to use a dispatch dictionary, which essentially allows me to run a function based on a key, and optionally pass in data for that function. I'll probably rewrite this to align with [PEP443](https://www.python.org/dev/peps/pep-0443/) - but for now its working so I'm not going to get too much deeper there for now. Working is better than perfect, right? (I decided to stop rewriting code and blog about it instead)

I also [passed the Main thread](https://github.com/BadgerOps/resin-speedtest/blob/master/libs/LcdPlate.py#L15) into the LCD Plate thread to give some cross thread communication - for example, hitting 'select' on the plate [triggers a force re-run](https://github.com/BadgerOps/resin-speedtest/blob/master/libs/LcdPlate.py#L21) of [the speedcheck](https://github.com/BadgerOps/resin-speedtest/blob/master/SpeedTestCheck.py#L37).

Migrating the LCD Plate to its own thread and tighting up the while loop gave a very noticeable improvement to button performance. My initial attempt had me trying to press the buttons 2-4 times to get a response, now its first click response as expected, woot! 

Beyond these things I mentioned, the code is pretty straightforward, feel free to comment if there's something that doesn't make sense, and I'll do my best to clarify.

---
###### The Resin ([.io!](resin.io)) part:
 
  *Note: If you're wanting to follow along, then fork [my repo](https://github.com/BadgerOps/resin-speedtest) and clone it locally before doing the following.*

If you haven't played with Resin, and you have a spare Pi, Beagleboard, Chip, or [one of the many](https://docs.resin.io/hardware/devices/) other supported boards, then take 10 minutes, goto https://resin.io/ and click the friendly blue 'Get started now' button. Deploying a simple 'hello world' app is surprisingly simple and rewarding.

You'll see in the [repo](https://github.com/BadgerOps/resin-speedtest), that I've got a [Dockerfile.template](https://github.com/BadgerOps/resin-speedtest/blob/master/Dockerfile.template) which allows the project to seamlessly support multiple Arches, [documentation here](https://docs.resin.io/deployment/docker-templates/). Now, with this said, this particular project will only work on a Raspberry Pi at this point, but it could conceivably be ported to other devices, and why not support that in the Dockerfile?

Getting the app committed and built by Resin is incredibly simple. If you created an account already, all you have to do is make sure you're on the [applications](https://dashboard.resin.io/apps) page, and you should see a 'create new app' tile. Enter the name and architecture of your device, in this case I called it "Speedtest App" and the device is a Rpi 3. Once you click the 'create new application' button, you'll be presented with a ResinOS download. Using Etcher, or your flashing utility of choice, write that to your SD card and boot your Pi. 

While we're waiting for the Pi to boot, look in the upper right hand corner of the page, and you'll see a string `git remote add resin username@git.resin.io:username/speedtest.git`. Copy that, and make sure you're in the repo you cloned earlier. Once thats done, you should be able to simply run `git push resin` and it will build and upload the application. 

Once that is done, head back over to the application you created before and watch it download and run. The initial install takes a while because there's a lot of code that gets compiled for the i2c support for the LCD Plate.

---
###### The final tidbits part:

While this is a much better implementation than my first pass, there's a lot more I'd like to do:

* Build a better menu structure vs having a single button mapped to each item
* Add ability to select speedtest polling time from menu
* Scrolling text and ability to show full URL tested
* Custom speedtest endpoints

Right now, the buttons are as follows:

* Select: re-run the speedtest on demand
* Up: Show local IP Address
* Down: Show speedtest.net server ID that current speedtest was ran against
* Right: Show current speedtest
* Left: Show previous speedtest

I pay for 40mb down, 20mb up, so I set it to turn the LCD red if the speed is below 35mb or green if the speed is above 35. This can easily be adjusted by editing the `self.netspeed` dictionary in the SpeedTestCheck.py __init__.py function:
```
    def __init__(self):
        self.netspeed = {'up': 20, 'down': 40 }
```
Feel free to comment below, or open a issue in the git repo with questions or comments. Thanks for reading!

-BadgerOps