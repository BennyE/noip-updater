noip-updater
============

Lightweight no-ip.com IP Address Updater

Today many consumer-grade routers offer some kind of facility to update a DynDNS service with your current IP address. This way you can always reach your home network via VPN (or your web server) while on the go.

Unfortunately my router is quite old and only offers "DynDNS" connections to providers for that you have to pay today and I didn't feel like that. I switched to www.no-ip.com which is, as of today, free of charge for simple FQDN -> IP services.

I run a Raspberry Pi and could likely have used the tools made available by that provider, but wanted to talk to the API myself.

The script doesn't run as a daemon, so you'll have to use a cronjob to start it e.g. every 10 minutes. Between that time the values will be stored in a file called "noip-settings.txt" and only updated once you hit an API error or a new IP address was detected.

Here is a example for an IP address getting updated:
(IP is getting updated, as the stored IP differs from IP reported by online site)

Aug 14 12:40:02 raspberrypi noip.py: Read: {'oldip': 'x.x.x.x', 'error': '', 'errmsg': '', 'time': 1407813610.181159}
Aug 14 12:40:02 raspberrypi noip.py: Contacting www.portchecktool.com for current IP!
Aug 14 12:40:10 raspberrypi noip.py: Successfully updated IP Address on server!
Aug 14 12:40:10 raspberrypi noip.py: IP is now: y.y.y.y
Aug 14 12:40:10 raspberrypi noip.py: Attempting to write noip-settings.txt
Aug 14 12:40:10 raspberrypi noip.py: Wrote: {'oldip': 'y.y.y.y', 'error': '', 'errmsg': '', 'time': 1408012810.621651}
Aug 14 12:40:10 raspberrypi noip.py: Successfully written status file to disk!

Here is a example how it will look most of the time:
(IP not getting updated, as it is still the same)

Aug 14 13:10:01 raspberrypi /USR/SBIN/CRON[2651]: (pi) CMD (/home/pi/noip.py)
Aug 14 13:10:03 raspberrypi noip.py: no-ip.com IP Address Updater starting ...
Aug 14 13:10:03 raspberrypi noip.py: Attempting to open noip-settings.txt
Aug 14 13:10:03 raspberrypi noip.py: Read: {'oldip': 'y.y.y.y', 'time': 1408012810.621651, 'errmsg': '', 'error': ''}
Aug 14 13:10:03 raspberrypi noip.py: Contacting www.portchecktool.com for current IP!
Aug 14 13:10:06 raspberrypi noip.py: IP address still the same! Exiting ...

The API guide of no-ip.com asks you to only contact their update-service when you have a change to report. I implemented a little verification that the stored IP address actually differs from the IP that is being reported by www.portchecktool.com and only then update the IP address at your no-ip.com account. There are a couple of other requirements, like reading the error code responses by the site.

If you plan to let this run for a long time, it is good practice on a Raspberry Pi to have the /var/log in memory instead of the SD card. The IP address etc on SD (noip-settings.txt) is only updated once per day or whenever your IP address changes - this shouldn't be too much of a burden for any SD.

Before your first start, you'll need to add your "Username", "Password" and "hostname" to the script.
