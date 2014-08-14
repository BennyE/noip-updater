#!/usr/bin/env python

"""
Lightweight no-ip.com IP Address Updater
Benny Eggerstedt in 2014
"""

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

#
# Imports
#

import pickle
import re
import sys
import syslog
import time
try:
    import requests
except ImportError:
    sys.exit("Failed to import python-requests!")

#
# Account related settings
#

# Username - This should be your mail address or username registered
#            with no-ip.com
username = ""

# Password - Your password, it may not contain special characters
#            according to no-ip.com
password = ""

# Hostname - Your hostname that is registered with no-ip.com
hostname = ""

if username == "":
    syslog.syslog("Username cannot be empty!")
    sys.exit("Username cannot be empty!")
if len(username) > 50:
    syslog.exit("Username cannot be longer than 50 characters " +
                "according to no-ip.com!")
    sys.exit("Username cannot be longer than 50 characters according " +
             "to no-ip.com!")
if password == "":
    syslog.exit("Password cannot be empty!")
    sys.exit("Password cannot be empty!")

#
# It should not be necessary to modify anything below this line
#

#
# www.no-ip.com Update URL
#
# You should NEVER send login credentials through an unencrypted connection!
# I warned you! Please only use the httpsurl!
# httpurl = "http://dynupdate.no-ip.com/nic/update"
httpsurl = "https://dynupdate.no-ip.com/nic/update"

#
# www.portchecktool.com
# Service page by noip.com to get our current IP address
# Unfortunately this service uses an invalid SSL certificate, reverting to HTTP
getipurl = "http://www.portchecktool.com"


def readstatusdict():
    """
    Opens our status file and reads variables
    """
    try:
        syslog.syslog("Attempting to open noip-settings.txt")
        fh = open("noip-settings.txt", "r")
    except IOError as ioerr:
        syslog.syslog("%s" % ioerr)
        return False
    else:
        settingsdict = pickle.load(fh)
        syslog.syslog("Read: %s" % settingsdict)
        return settingsdict


def writestatusdict(status):
    """
    Writes our status file to disk
    """
    try:
        syslog.syslog("Attempting to write noip-settings.txt")
        fh = open("noip-settings.txt", "w")
    except IOError as ioerr:
        syslog.syslog("%s" % ioerr)
        return False
    else:
        pickle.dump(status, fh)
        fh.close()
        syslog.syslog("Wrote: %s" % status)
        return True


def getip(conn):
    """
    getip()
    """
    try:
        syslog.syslog("Contacting www.portchecktool.com for current IP!")
        page = conn.get(getipurl)
        # syslog.syslog("WARNING: no-ip.com is unfortunately using an " +
        #              "invalid ssl certificate for www.portchecktool.com!")
        # syslog.syslog("This is why we use an unencrypted connection.")
    except requests.exceptions.ConnectionError as ce:
        syslog.syslog(ce)
    regex = re.search("<center><p><strong>Your Current Public IP " +
                      "Address is: (.*)</strong></p></center>", page.content)
    if regex is None:
        return "ip not found"
    currentip = regex.group(1)
    return currentip


def updateserver(conn):
    """
    This function updates the no-ip.com server
    """
    try:
        page = conn.get(httpsurl + "?hostname=" + hostname,
                        auth=requests.auth.HTTPBasicAuth(username, password))
    except requests.exceptions.ConnectionError as ce:
        syslog.syslog(ce)
        return False
    else:
        return page.content


def evaluateresponse(page, status):
    """
    Works on the page response and sets statusdict accordingly
    """
    if "good" in page:
        # Save our new IP address to the dictionary
        status["oldip"] = page.split()[1]
        status["time"] = time.time()
        status["error"] = ""
        status["errmsg"] = ""
        syslog.syslog("Successfully updated IP Address on server!")
        syslog.syslog("IP is now: %s" % status["oldip"])

    elif "nochg" in page:
        # Likely our first start if we get here!
        status["oldip"] = page.split()[1]
        status["time"] = time.time()
        status["error"] = ""
        status["errmsg"] = ""
        syslog.syslog("IP Address was still the same!")

    elif "nohost" in page:
        status["oldip"] = ""
        status["time"] = time.time()
        status["error"] = "nohost"
        status["errmsg"] = "Hostname supplied does not exist under " + \
            "specified account, client has to exit and requires " + \
            "you to modify login credentials before performing " + \
            " an additional request."
        # Note that I got this response code even for offline=YES
        # It is possible that there is a mistake in the server-side API
        syslog.syslog(status["errmsg"])

    elif "badauth" in page:
        status["oldip"] = ""
        status["time"] = time.time()
        status["error"] = "badauth"
        status["errmsg"] = "Invalid username password combination"
        syslog.syslog(status["errmsg"])

    elif "badagent" in page:
        status["oldip"] = ""
        status["time"] = time.time()
        status["error"] = "badagent"
        status["errmsg"] = "Client disabled. Client should exit and will " + \
            "not perform any more updates without user intervention."
        syslog.syslog(status["errmsg"])

    elif "!donator" in page:
        status["oldip"] = ""
        status["time"] = time.time()
        status["error"] = "!donator"
        status["errmsg"] = "An update request was sent including a " + \
            "feature that is not available to that particular user " + \
            "such as offline options."
        syslog.syslog(status["errmsg"])

    elif "abuse" in page:
        status["oldip"] = ""
        status["time"] = time.time()
        status["error"] = "abuse"
        status["errmsg"] = "Username is blocked due to abuse."
        syslog.syslog(status["errmsg"])

    elif "911" in page:
        status["oldip"] = ""
        status["time"] = time.time()
        status["error"] = "911"
        status["errmsg"] = "A fatal error occured on no-ip.com side. " + \
            "Retry not before 30 minutes passed"
        syslog.syslog(status["errmsg"])

    # Status now contains a dictionary of response values
    return status


def main():
    """
    In main(), the entry point to this script, we'll verify that we're
    actually in need to contact the noip.com servers for an update.
    To do so, we'll look at a file on disk that holds our last known IP
    and compare it with the one we find online. If the IPs differ, we'll
    update the noip.com server with the new IP address.
    """

    # Let the syslog know that we're running
    syslog.syslog("no-ip.com IP Address Updater starting ...")

    # Our python-requests session
    conn = requests.Session()

    # Setting a User-Agent, as requested by no-ip.com API documentation
    conn.headers["User-Agent"] = "Lightweight no-ip.com IP-Address Updater/" + \
        "v0.2 benjamin.eggerstedt@gmail.com"

    # Read our last status, returns False if file doesn't exist
    status = readstatusdict()
    if status is False:
        # If there is no statusdict, we run for first time
        status = {}
        # page contains the no-ip.com response code
        page = updateserver(conn)
        # We need to evaluate what will need to happen depending on response
        status = evaluateresponse(page, status)
        rc = writestatusdict(status)
        if rc is True:
            syslog.syslog("Successfully written status file to disk!")
        else:
            syslog.syslog("Something went wrong writing status file!")
    else:
        # Found status file
        if status["error"] == "":
            # status doesn't hold an error message
            currentip = getip(conn)
            if status["oldip"] == currentip:
                syslog.syslog("IP address still the same! Exiting ...")
                sys.exit(0)
            elif currentip == "ip not found":
                syslog.syslog("Couldn't find current IP online!")
                sys.exit("Couldn't find current IP online!")
            else:
                page = updateserver(conn)
                status = evaluateresponse(page, status)
                rc = writestatusdict(status)
                if rc is True:
                    syslog.syslog("Successfully written status file to disk!")
                    sys.exit(0)
                else:
                    syslog.syslog("Something went wrong writing status file!")
        elif status["error"] == "911":
            # 911 error means we can try again after 30 minutes passed
            syslog.syslog("Trying to recover from 911 error!")
            if (time.time() - status["time"]) >= 1800:
                syslog.syslog("30 minutes passed! Trying ...")
                page = updateserver(conn)
                status = evaluateresponse(page, status)
                rc = writestatusdict(status)
                if rc is True:
                    syslog.syslog("Successfully written status file to disk!")
                    sys.exit(0)
                else:
                    syslog.syslog("Something went wrong writing status file!")
            else:
                syslog.syslog("30 minutes did NOT pass, keep waiting!")
                sys.exit(0)

        elif status["error"] == "nohost":
                syslog.syslog("Host not found! Or: You'll have to pay for " +
                              "additional features!")
                syslog.syslog("Correct settings and delete noipsettings.txt")
                sys.exit("Host not found! Or: You need to pay for " +
                         "this service!")

        elif status["error"] == "badauth":
                syslog.syslog("Bad login credentials!")
                syslog.syslog("Correct settings and delete noipsettings.txt")
                sys.exit("Bad login credentials! Correct them! " +
                         "Delete noipsettings.txt afterwards!")

        elif status["error"] == "badagent":
                syslog.syslog("Bad agent! no-ip no longer likes us!")
                sys.exit("Bad agent! no-ip no longer likes us!")

        elif status["error"] == "!donator":
                syslog.syslog("You'll have to pay for " +
                              "additional features!")
                sys.exit("You need to pay for " +
                         "this service!")

        elif status["error"] == "abuse":
                syslog.syslog("Your account has been blocked! Contact " +
                              "no-ip.com support!")
                sys.exit("Your account has been blocked! Contact " +
                         "no-ip.com support!")

if __name__ == "__main__":
    main()
