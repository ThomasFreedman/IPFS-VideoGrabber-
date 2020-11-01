#!/usr/bin/python3
#
# ytdlVideoGrabber.py - Program to scrape videos and add them to IPFS.
#
# A SQLite3 database is used to  store  IPFS  hashes and detailed metadata for
# each  video.  This  lightweight  SQL engine is filesystem based (no server).
#
# This script requires a JSON formatted config file containing  schema  column
# names and other info, like filter settings for video length and upload date.
#
# Youtube is known to change the metadata keys, making it difficult to rely on
# youtube metadata for the schema. After sampling 1000s of videos a common set
# of metadata columns was arrived at and is now found in the JSON config file.
#
# The metadata provided by youtube-dl extractors is not totally normalized. To
# insure a database record is saved for every file added to IPFS, an alternate
# metadata dictionary is used which always sets these 8 essential columns:
#
#      sqlts, pky, g_idx, grupe, vhash, season_number, url and _filename
#
# and any others from the downloaded metadata whose  field  names  are found in
# the Metadata list of the config file.  The  substitute metadata dictionary is
# used when a SQL error occurs while adding a new row. If the 2nd attempt fails
# it is logged along with the IPFS hash, so a record can be added manually at a
# later time. Usually the substitution is required b/c there are missing fields
# in the metadata provided by the youtube-dl extractor used for a video source.
#
from __future__ import unicode_literals
from email.message import EmailMessage
from ytdlServerDefinitions import *        # Server specific CONSTANTS
from youtube_dl import utils
from datetime import *
import youtube_dl
import subprocess
import threading
import smtplib
import sqlite3
import time
import json
import sys
import os

#
# Global Variables
#
SQLrows2Add     = []    # Lists populated by download callback threads
ErrorList       = []

# Loaded from config file specified on command line (JSON file format).
# This variable will remain empty until the config file is read.
Config = {}

"""  Config file template, JSON format. Use single quotes only, null not None:
Config {
     "Comment": [ "Unreferenced - for comments inside config file",
        "It is difficult sometimes to find the video link for Brightcove videos.",
        "This is the method that I use with Firefox. You will need 2 things:",
        "a) AccountID",
        "b) VideoID",
        "Get these by right-clicking on the video and select Player Information.",
        "Use ctrl-C to copy the info, and plug them into this template:",
        "http://players.brightcove.net/<AccountID>/default_default/index.html?videoId=<VideoID>",
        "Works with Firefox 68.8, 75.0 and probably others as of May 12, 2020"
    ],

    "DLbase":    "dir",      Folder for all downloaded files organized by grupe
    "DLeLog":    "file",     File for exceptions / errors during downloads
    "DLarch":    "file",     This tracks downloads to skip those already done

    "DLOpts": {              Name / value pairs for youtube-dl options
        "optName1": "value1", NOT always the same as cmd line opts
        ...
    },

    "Grupes": {    # Dictionary of grupes to download, with its own criteria
        "gName1": {          Group name containing video selection criteria
            "Active": true,  Enable or disable downloads for this grupe
            "Duration":  0,  Min size of video in seconds; for no limits use 0
            "Quota":  null,  Limits size of grupe's DL folder to N files
            "Start":  null,  Earliest upload date string or (YYYYMMDD) or null
            "End":    null,  Latest upload date or null. 1, 2 or neither OK
            "Stop":   null,  Stop downloading from playlist after this many DLs
                "url1",
                "url2",
                ...
            ]
        },
        ...                  Additional grupes
    },

    "MetaColumns": [   Contains the list of database fields for metadata for
        ...            the video downloaded along with it in JSON format.
    ]
}
"""

def usage():
    cmd =  sys.argv[0]
    str =  "\nUses youtube-dl to download videos and add them to IPFS and track\n"
    str += "the results in a SQLite database.\n\n"
    str += "Usage:  " + cmd + " [-h] | <-c config> <-d sqlite>\n"
    str += "-h or no args print this help message.\n\n"
    str += "-c is a JSON formated config file that specifies the target groups,\n"
    str += "their URL(s),  the list of metadata columns, downloader options and\n"
    str += "the base or top level folder for the groups of files downloaded.\n"
    str += "-d is the SQLite filename (it is created if it doesn't exist).\n\n"
    print(str)
    exit(0)


# Flattens a nested JSON object and returns a python dictionary
def flatten_json(nested_json):
    out = {}

    def flatten(x, name=''):
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + '_')
        elif type(x) is list:
            i = 0
            for a in x:
                flatten(a, name + str(i) + '_')
                i += 1
        else:
            out[name[:-1]] = x

    flatten(nested_json)
    return out


# Create the SQLite database file if it doesn't  exist,  using the
# MetaColumns from Config. If it already exists, open a connection
# to it. Always returns a connection object to the dbFile.
def openSQLiteDB(columns, dbFile):
    newDatabase = not os.path.exists(dbFile)
    conn = sqlite3.connect(dbFile)
    if newDatabase:
        sql = '''create table if not exists IPFS_HASH_INDEX (
        "sqlts" TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime')),
        "pky"   INTEGER PRIMARY KEY AUTOINCREMENT,
        "g_idx" TEXT,
        "grupe" TEXT,
        "vhash" TEXT,
        "mhash" TEXT'''

        for c in columns:
            sql += ',\n\t"' + c + '" TEXT'
        sql += ')'
        conn.execute(sql)
    return conn


# Add a file to IPFS and return the hash for it. Needs some error detection
def add2IPFS(file):
    lst = []
    cmd = ["ipfs", "add", file]
    out = subprocess.run(cmd, stderr=subprocess.DEVNULL,
                              stdout=subprocess.PIPE).stdout.decode('utf-8')
    return(out.split("\n")[0][6:52])    # Only take the 46 character hash


# Create a grupe index file containg a list of all video and metadata IPFS
# hashes for the group. Add it to IPFS & return the hash and count of rows
# updated.
def updateGrupeIndex(conn: object, grupe: object) -> object:
    cursor    = conn.cursor()

    idxFile = "/tmp/%s_idx.txt" % grupe
    idx = open(idxFile, "w")
    sql =  'SELECT "v=" || vhash || " " || "m=" || mhash'
    sql += '  FROM IPFS_HASH_INDEX'
    sql += ' WHERE grupe = "%s"' % grupe
    for row in cursor.execute(sql): # Loop through all rows this grupe
        idx.write(row[0] + "\n")
    idx.close()
    hash = add2IPFS(idxFile)
    if len(hash) > 0:
        sql = "UPDATE IPFS_HASH_INDEX set g_idx=? WHERE grupe=?"
        cursor.execute(sql, (hash, grupe))
        conn.commit()
        os.remove(idxFile)
    return (cursor.rowcount, hash)


#    This block of code will create group index files for every group in DB,
#    then add that file to IPFS. Update every row in the group with that hash,
#    and do that for every grupe, so every row in IPFS_HASH_INDEX table gets
#    updated. See "updateGrupeIndex" above for details. This just wraps that.
def regenerateAllGrupeIndexes(conn):
    cursor = conn.cursor()
    sql = "sSELECT DISTINCT grupe FROM IPFS_HASH_INDEX"
    for row in cursor.execute(sql):
        (count, hash) = updateGrupeIndex(conn, row[0])
        print("Updated %d rows for grupe %s with grupe index hash %s" %
               (count, row[0], hash))


# Add a row to SQLite database. Most of the column data is from the JSON
# metadata (gvmjList) downloaded with the video. Note that SQLite is not
# thread safe, so only the main thread updates the DB.
def addRow2db(conn, cols, gvmjList):
    (grupe, vhash, mhash, jsn) = gvmjList
    cursor = conn.cursor()
    jsn["episode_number"] = mhash # Mark row as pinned by adding the hashes
    jsn["season_number"] = vhash  #  to these fields
    values = [grupe, vhash, mhash] # 1st 3 values: video group and IPFS hashes
    sql    = 'INSERT INTO IPFS_HASH_INDEX ("grupe", "vhash", "mhash"'

    for col in cols:
        sql += ',\n\t"' + col + '"'

    sql += ") VALUES (?,?,?"       # Now add metadata
    for col in cols:
        sql += ",?"
        values.append(jsn[col])
    sql += "); "

    cursor.execute(sql, values)
    conn.commit()

    return cursor.lastrowid


# This wrapper function detects failures in the addRow2db  function above and
# makes a 2nd attempt to insert the row with alternate metadata dictonary. If
# the failure occurs on the second attempt the failure is indicated by a None
# return value and raising the SQLite3 exception. A new dictionary is created
# and all valid metadata values in download are copied to it.  Missing values
# are set to "unknown-value".
#
# The ytdl  extractors vary as to the the format of the metadata they produce,
# youtube-dl doesn't totally normalize it.  If a video file was downloaded and
# an IPFS hash was produced a row will be added with sqlts, pky, g_idx, grupe,
# vhash, season_number and _filename columns that have known valid data.
def addRow(conn, cols, gvmjList):
    try:
        row = addRow2db(conn, cols, gvmjList)   # Attempt number one...

    # On failure create a new metadata dictionary for this video. For any
    # missing keys, create a key whose value is "unknown-value". This will get
    # around issues related to the JSON metadata
    except Exception as e:
        newDictionary = {}
        for col in cols:
            if col in gvmjList[3].keys():
                newDictionary[col] = gvmjList[3][col]
            else: newDictionary[col] = "unknown-value"

        # Try again. Any exception this time will propagate upstream
        (grp, vhash, mhash, jsn) = gvmjList
        row = addRow2db(conn, cols, (grp, vhash, mhash, newDictionary))

    return row


# Add a row to the SQLite database for every video downloaded for this grupe,
# print the downloads and failures and log the failures to the error log file.
def processGrupeResults(conn, cols, urls, grupe, eLog):
    global ErrorList, SQLrows2Add
    downloads = len(SQLrows2Add)
    rowz = 0

    if downloads > 0:
        for dat in SQLrows2Add:  # dat = (grp, vhash, mhash, json)
            try:
                row = addRow(conn, cols, dat)
                rowz += rowz + 1 # Sucessfully added to SQLite
                mark = datetime.now().strftime("%a %H:%M:%S")
                refs = "video=%s, metadata=%s" % (dat[1], dat[2])
                print("%s row=%d, %s" % (mark, row, refs))

            # Failed to add the row to SQLite, but it's saved in IPFS
            except Exception as expn:
                args = (dat[0], dat[1], dat[2], dat[3], expn)
                er = "SQL Error! Grupe=%s vHash=%s mHash=%s JSON=%s\n%s" % args
                print(er)
                er += "\nMetadata key/values used:\n"
                for col in dat[3]:
                    er += "%32s = %s\n" % (col, dat3[col])
                ErrorList.append(er)

        print("%d downloads, %d DB rows added" % (downloads, rowz))
        args = (rowz, updateGrupeIndex(conn, grupe))
        print("Updated %d rows with grupe index hash %s\n" % args)

    # Print and log the list of download failures
    failures = len(ErrorList)
    if len(ErrorList) > 0:
        eLog.write("PROCESSING ERRORS FOR GRUPE=%s:\n" % grupe)
        for error in ErrorList:
            eLog.write(error + '\n')
        eLog.write("END OF ERRORS FOR %s\n\n" % grupe)

    args = (urls, downloads, failures)
    print("URLs Processed=%d (Downloaded=%d, Failed=%d)" % args)
    return rowz


# Used to determine if folder size limit has been exceeded. NOT recursive
def getSize(path):
    totalSize = 0
    for f in os.listdir(path):
        fp = os.path.join(path, f)
        totalSize += os.path.getsize(fp)
    return totalSize


# Check if the download folder for this grupe is over the quota (if any)  and
# remove the oldest file if it is.  The quota  is the maximum number of files
# or the maximum amount of space to limit the folder to. Quota is a string of
# integers followed by whitespace & unit string value. If no unit designation
# is specified the quota is the amount of space used in bytes. When the limit
# is exceeded the oldest files are removed to make room. .json and .wav files
# aren't counted in a file count quota, but they are for folder space quotas.
# Removals always remove all files of the same name  regardless of extension,
# HOWEVER, wildcard replacement occurs after the 1st . on the left. Also note
# that pruning will never remove the last remaining audio file.
def pruneDir(quota, dir):
    global ErrorList
    max = count = 0
    fList = []

    if quota:                               # Do nothing if no quota specified
        q = quota.split(' ')                # Quota amount and units, if any
        if q[0].isdecimal():                # Check if string is a valid number
            max = int(q[0])                 # This is the quota limit
        if max < 2:                         # Invalid quota value, zero removed
            err = "Invalid quota: " + dir
            ErrorList.append(err)           # Log the error
            return False

        for f in os.listdir(dir):           # Create a list of candidate files
            if f.endswith(EXT_LIST):        # Only include primary audio files
                fList.append(dir + '/' + f) # Prefix the file with path
                count += 1                  # Count how many in the list
        if count < 2: return False          # We're done if none or only 1

        old = min(fList, key=os.path.getctime)   # Get oldest audio file

        if len(q) > 1: size = 0             # Quota limits number of files
        else: size = getSize(dir)           # Quota limits space used
        if count > max or size > max:       # Over the quota?
            rm = old.rsplit('.')[0] + ".*"  # Replace extension with a wildcard
            os.system("rm -rf %s" % rm)     # Easy way to do all related files
            return True                     # Oldest file removed
        else: return False


# This function is a thread of execution started with each completed download.
# It is started as a daemon thread to add the video and its' metadata to IPFS,
# and creates lists for errors and the files downloaded (to update SQLite).
def processVideo(file):
    global Config, ErrorList, SQLrows2Add
    vHash = mHash = jFlat = None

    grp = file.rsplit('/', 2)[1]      # Extract grupe from file pathname
    pb = os.path.splitext(file)[0]    # Path + Basename in list index 0
    mFile = pb + ".info.json"         # json metadata file for this download
    vFile = file                      # Full pathname of downloaded video file
    dir, base = file.rsplit('/', 1)   # Separate grupe folder & downloaded file

    # The grupe quota limits the size of the download folder. It's a string
    # containing an integer with a space followed by an optional units word.
    quota = Config["Grupes"][grp]["Quota"] # i.e. "20 files" or "2500000000"
    pruned = False
    while pruneDir(quota, dir):       # Keep pruning until under quota
        time.sleep(0.01)
        pruned = True
    if pruned: ErrorList.append("WARNING: Folder limit reached and pruned!")

    # Log all errors, but add to SQLite if we got a valid video hash from IPFS
    try:
        vHash = add2IPFS(vFile)        # Add video file to IPFS
        mHash = add2IPFS(mFile)        # Add the metadata file to IPFS
        with open(mFile, 'r') as jsn:  # Read the entire JSON metadata file
            jDict = json.load(jsn)     # Create a python dictionary from it
        jFlat = flatten_json(jDict)    # Flatten the dictionary

    except Exception as e:             # Log any errors that may have occurred
        args = (grp, vHash, mHash, base, e)
        ErrorList.append("Grupe=%s vHash=%s mHash=%s vFile=%s\n%s" % args)

    # If vHash is valid create a SQLite entry for it, regardless of metadata
    finally:
        if len(vHash) == 46 and vHash[0] == 'Q':  # Valid vHash?  If so add it
            SQLrows2Add.append([grp, vHash, mHash, jFlat])  # to SQLite DB


# Starts a daemon thread to process the downloaded file. youtube-dl provides no
# way to obtain information about the ffmpeg post processor, and adding to IPFS
# can be time consuming.  Using  threads to handle files allows the main thread
# 2 download other files concurrently with IPFS additions. See the processVideo
# function above for specifics of how the downloaded file is processed.
def callback(d):
    if d['status'] == 'finished':
        path = d['filename']             # Callback provides full pathname
        th = threading.Thread(target=processVideo, args=([path]), daemon=True)
        th.start()                       # Start the thread and continue


##############################################################################
#                                                                            #
# Primary program loop. The  youtube-dl library  takes care of downloading.  #
# The callback function above processes each download, adding files to IPFS  #
# and creating a list of rows to add to the SQLite DB by this function.      #
#                                                                            #
##############################################################################
def ytdlProcess(config, conn):
    global          ErrorList, SQLrows2Add
    sep             = SEPARATOR
    cols            = config['MetaColumns']
    dlBase          = config['DLbase']
    dlArch          = dlBase + config['DLarch']
    dlElog          = dlBase + config['DLeLog']
    dlOpts          = config['DLOpts']
    grupeList       = config['Grupes']
    completed       = 0
    # NOTE: items missing from extractor's metadata will be replaced with "NA"
    ytdlFileFormat  = "/%(id)s" + sep + "%(duration)s"+ sep + ".%(ext)s"

    # Add crucial download options. Some options MUST be added in the DL loop
    # dlOpts['force-ipv6'] = True                # May not be enabled on host
    dlOpts['source_address'] = DOWNLOAD_IP     # The IP  video platform sees
    dlOpts['writeinfojson'] = True
    dlOpts['progress_hooks'] = [callback]      # Called at least once / video
    dlOpts['download_archive'] = dlArch        # Facilitates updates w/o dupes
    dlOpts['restrictfilenames'] = True         # Required format for DLd files
    eLog = open(dlElog, mode='a+')             # Error log file for all grupes
    try:
        with youtube_dl.YoutubeDL(dlOpts) as ydl:
            for grupe in grupeList:
                if not grupeList[grupe]['Active']: continue # Skip this grupe
                SQLrows2Add = []               # Empty the list of downloads
                ErrorList = []                 # Empty the list of errors
                print("\nBEGIN " + grupe)      # Marks start of group in log

                if not os.path.isdir(dlBase + grupe):  # If it doesn't exist
                    os.mkdir(dlBase + grupe)           #  create folder 4 grupe

                # Add qualifier for minimum video duration (in seconds)
                dur = grupeList[grupe]['Duration']
                if dur != None and dur > 0:
                    dur = "duration > %d" % dur
                    ydl.params['match_filter'] = utils.match_filter_func(dur)
                elif 'match_filter' in ydl.params.keys():
                    del ydl.params['match_filter']  # No duration filter

                # Add release date range qualifier; either one or both are OK
                sd = grupeList[grupe]['Start']      # null or YYYYMMDD format
                ed = grupeList[grupe]['End']        # in JSON
                if sd != None or ed != None:
                    dr = utils.DateRange(sd, ed)    # Dates are inclusive
                    ydl.params['daterange'] = dr    # Always set a date range
                elif 'daterange' in ydl.params.keys():
                    del ydl.params['daterange']     # No date filter

                # This stops downloading from playlist after this many videos
                stop = grupeList[grupe]['Stop']
                if stop != None and stop > 0: ydl.params['playlistend'] = stop
                elif 'playlistend' in ydl.params.keys():
                    del ydl.params['playlistend']   # No playlist limit

                # This will change downloaded file folder for each grupe
                ydl.params['outtmpl'] = dlBase + grupe + ytdlFileFormat
                urls = grupeList[grupe]['urls']
                ydl.download(urls)              # BEGIN DOWNLOADING!!!
                print("YOUTUBE-DL PROCESSING COMPLETE for %s" % grupe)

                # Wait for all callback threads to finish
                for th in threading.enumerate():
                    if th.name != "MainThread":
                        th.join()

                # Log errors and print results of this DL grupe
                rowz = processGrupeResults(conn, cols, len(urls), grupe, eLog)
                completed += rowz

    except Exception as e:
        err = "ytdlProcess exception: Grupe=%s:\n%s" % (grupe, e)
        eLog.write(err + '\n')
        print(err)

    eLog.close()
    return completed

#
# Display a summary of this download session. Return them for emailing.
#
def displaySummary(conn):
    now = datetime.now().strftime("%a %b %d, %Y")
    #
    # Report the number of files in each grupe
    #
    sql = "SELECT DISTINCT g_idx, count(*) as videos, grupe"
    sql += " FROM IPFS_HASH_INDEX GROUP BY grupe ORDER BY grupe;"
    args = "Grupe index files for %s:     Hash  Videos     Grupe" % now
    mail = args
    print('\n' + args)
    for cols in conn.execute(sql):
        args = (cols['g_idx'], cols['videos'], cols['grupe'])
        mail += "%48s | %5d  |  %s\n" % args
        print("%48s | %5d  |  %s" % args)
    # Print the total number of files in all grupes
    cursor = conn.cursor().execute("SELECT COUNT(*) FROM IPFS_HASH_INDEX;")
    total  = "                                            Total: "
    total += "%5d\n" % cursor.fetchone()[0]
    print(total)
    mail += total
    #
    # Report the number of files added in the last 30 days
    #
    strt = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    sql = "SELECT DISTINCT SUBSTR(sqlts, 6, 5) as tme, grupe, count(*) as cnt "
    sql +=  "FROM IPFS_HASH_INDEX WHERE sqlts > '" + strt + "' "
    sql += "GROUP BY grupe ORDER BY sqlts desc;"
    args = " Date   Videos   Grupe (Videos Added in the Last 30 Days)"
    mail = args + "\n"
    print(args)
    for cols in conn.execute(sql):
        args = (cols['tme'], cols['cnt'], cols['grupe'])
        mail += "%5s | %6d | %s\n" % args
        print("%5s | %6d | %s" % args)
    # Print the total number of files downloaded in last 30 days
    sql = "SELECT COUNT(*) FROM IPFS_HASH_INDEX WHERE sqlts > "
    cursor = conn.cursor().execute(sql + "'" + strt + "';")
    total = " Total:  "
    total += "%5d" % cursor.fetchone()[0]
    print(total)
    mail += total
    #
    # Report the videos downloaded today as grupes, titles & IPFS URLs
    #
    urls = ""
    sql = "SELECT grupe, title, vhash "
    sql +=  "FROM IPFS_HASH_INDEX "
    sql += "WHERE DATE(sqlts) = DATE('now', 'localtime', 'start of day');"
    rows = (conn.cursor().execute(sql)).fetchall()
    if len(rows) > 0:
        args = "\nIPFS URLs for videos downloaded today:"
        urls = args + '\n'
        print(args)
        for col in rows:
            args = (col['grupe'], col['title'][:48], col['vhash'])
            text = "%12s | %48s | https://ipfs.io/ipfs/%s" % args
            urls += text + '\n'
            print(text)

    return [mail, urls]


# Send a plain text message via email to recipient(s)
def emailResults(server, account, subject, origin, to, text):
    msg = EmailMessage()         # Create a text/plain container
    msg.set_content(text)
    msg['Subject'] = subject
    msg['From'] = origin
    msg['To'] = to

    emailer = smtplib.SMTP_SSL(server[0], server[1])
    emailer.login(account[0], account[1])
    emailer.send_message(msg)
    emailer.quit()


##############################################################################
# Get command line arguments. Returns a tuple with config and DB connection. #
# Usage: thisFile [-h] | <-c config> <-d sqlite>                             #
#                                                                            #
# Parse command line and report config info. Prints usage and exists if args #
# are invalid or missing.                                                    #
##############################################################################
def getCmdLineArgs():
    if len(sys.argv) >= 5:
        sqlDBfile = config = conn = None
        grupes = urls = 0

        # Required parameter: -c config file
        if sys.argv[1] == "-c" and os.path.isfile(sys.argv[2]):
            with open(sys.argv[2], 'r') as jsn:
                config = json.load(jsn)
            metaSize = len(config['MetaColumns'])
            if metaSize > 0:  # config info loaded OK?
                for grupe in config['Grupes']:  # Count groups and urls in them
                    grupes += 1
                    urls += len( config['Grupes'][grupe]['urls'] )
                print("Database Metadata Columns=%d" % metaSize)
                print("Downloaded groups will be saved in %s" % config['DLbase'])
                print("%d groups, %d urls to process" % (grupes, urls))
            else: usage()
        else: usage()

        # Required parameter: -d SQLite database file
        if sys.argv[3] == "-d":
            sqlDBfile = sys.argv[4]
            conn = openSQLiteDB(config['MetaColumns'], sqlDBfile)
            conn.row_factory = sqlite3.Row       # Results as python dictionary
        if conn == None: usage()

        if not os.path.isdir(config['DLbase']):  # Create folder for results
            os.mkdir(config['DLbase'])           #  if necessary

        return (config, conn, sqlDBfile)         # Return essential information
    else: usage()

##############################################################################
# Primary starting point for script according to "pythonic" convention.      #
# Change this "main" the class name,  call  getCmdLine as constructor to use #
# in a proper OOP style.                                                     #
# ############################################################################
def main():
    global Config
    Config, conn, sqlFile = getCmdLineArgs()     # Read config file, open DB

    #regenerateAllGrupeIndexes(conn)             # Fix all grupe indexes
    #exit(0)

    # Command line and config file processed, time to get down to it
    completed = ytdlProcess(Config, conn)

    mail = displaySummary(conn)
    conn.close()

    # If any downloads were completed, update IPFS with new SQLite file
    if completed > 0:
        hash = add2IPFS(sqlFile)
        args = "\nHash of the updated SQLite database: %s" % hash
        mail[0] += args
        print(args + "\n")

    if SEND_EMAIL:
        emailResults(EMAIL_SERVR, EMAIL_LOGIN,
                     EMAIL_SUB1, EMAIL_FROM, EMAIL_LIST, mail[0])

        if len(EMAIL_URLS) > 0 and len(mail[1]) > 0:
            emailResults(EMAIL_SERVR, EMAIL_LOGIN,
                         EMAIL_SUB2, EMAIL_FROM, EMAIL_URLS, mail[1])


###############################################################################
# main is only called if this file is a script not an object class definition.#
# If this code is useful as a class it will be easy to make it one.           #
###############################################################################
if __name__ == "__main__":
    main()

exit(0)
