#!/usr/bin/python3

#
# Defines constants for ytdlVideoGrabber.py, a program to scrape videos.
#
EMAIL_SERVR     = ["yourSMTPserverAddress", portNumber]
EMAIL_LOGIN     = ["smtpAccount", "smtpPassword"]
EMAIL_LIST      = "comma separted list of recipients"
EMAIL_URLS      = EMAIL_LIST
STATIC_DB_HASH  = ""
DOWNLOAD_IP     = "111.222.333.444"  # The server IP address to use for downloads
IP_ADR_LIST     = ["111.111.111.111", "222.222.222.222", "333.333.333.333", "444.444.444.444"]
IP_ADR_INDX     = 0
EMAIL_SUB1      = 'email subject line'
EMAIL_SUB2      = 'email subject for (separate) URL email'
EMAIL_FROM      = "the address you want in from line of email"
SEND_EMAIL      = True   # Send results to email recipients or not
SEPARATOR       = "~^~"  # Separates elements of the downloaded file pathname
EXT_LIST        = ("webm", "mp4", "mkv", "m4v") # Video file extensions


