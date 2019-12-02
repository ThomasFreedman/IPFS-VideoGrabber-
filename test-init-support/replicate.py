#!/usr/bin/python3
#
# Program to replicate an IPFS server populated with
# the Video Grabber progran (ytdl-ipfs????.py) which
# creates a SQLite database with hashes for each  of
# the files added to IPFS.
#
# This requires the SQLite3 database from the servers
# being replicated. It uses "ipfs cp <hash> /<grupe>/file"
# for every hash in the database to transfer the file,
# then an "ipfs pin add <hash>" to insure it will not
# be garbage collected on the local IPFS server
#
from __future__ import unicode_literals
from datetime import *
import sqlite3
import sys
import os

HOME = os.path.dirname(os.path.realpath(__file__)) + '/'

# GLOBALS
global OpCounter     # Count of IPFS operations done

def usage():
    cmd = sys.argv[0]
    str = "\nReplicate files on a remote IPFS server on local IPFS server.\n"
    str += "Requires Sqlite3 database file that specifies the files.\n\n"
    str += "Usage: " + cmd + " [-h] | <-d file> [-s <int>] [-p]\n"
    str += "where -d=SQLite DB file, -s=skip DB rows, -p=show pin progress\n\n"
    str += "ipfs must be in $PATH, and argument order is important.\n"
    str += "To create a log file DON'T use the -p flag, use:\n\n"
    str += cmd  + " <args> | tee -a <log file name>\n"
    print(str)
    exit(0)


# Prints IPFS operations done and day / time marker on console
def printMarker(newLine=False):
    global OpCounter

    now = datetime.now()
    str = "%s IPFS Operations Completed: %d"
    if newLine: str += "\n"
    mark = str % (now.strftime("%a %H:%M:%S"), OpCounter)
    print(mark, flush=True)
    OpCounter += 1


# Copy video & meta files from remote node into local virtual folder & pin them.
# Print progress as IPFS operations counter with day and time. The prog variable
# determines whether the  pinning operation reports incremental progress,  which
# makes for very long log files if tee is used on the output to create the log.
def copyPinFiles(row, prog):
    grupe = row[0]
    vhash = row[1]
    mhash = row[2]
    video = os.path.basename(row[3])
    meta  = video.split(".")[0] + ".info.json"
    if prog: progress = "-progress"
    else: progress = ''

    printMarker(True)
    copyCmd = "ipfs files cp /ipfs/" + vhash + " /" + grupe + "/" + video
    os.system("echo " + copyCmd)
    os.system(copyCmd)

    printMarker()
    pinCmd = "ipfs pin add --recursive=true %s /ipfs/%s" % (progress, vhash)
    os.system("echo " + pinCmd + "\n")
    os.system(pinCmd + "\n")

    printMarker(True)
    copyCmd = "ipfs files cp /ipfs/" + mhash + " /" + grupe + "/" + meta
    os.system("echo " + copyCmd)
    os.system(copyCmd)

    printMarker()
    pinCmd = "ipfs pin add --recursive=true %s /ipfs/%s" % (progress, mhash)
    os.system("echo " + pinCmd + "\n")
    os.system(pinCmd + "\n")




#############################################################################
#                                                                           #
# The main loop                                                             #
#                                                                           #
#############################################################################
skip = 0
OpCounter = 0
argc = len(sys.argv)
conn = errors = sql = grupe = progress = False

try:
    # Parse command line
    if argc > 1:
        if sys.argv[1] == "-h":
            usage()

        # Required parameter is SQLite database file
        if argc > 2 and sys.argv[1] == "-d":
            dbFile = sys.argv[2]
            conn = sqlite3.connect(dbFile) # Failure to open is exception
        else: usage()

        # Option to skip a number of rows in the SQLite database
        if argc > 4 and sys.argv[3] == "-s":
            OpCounter = int(sys.argv[4]) * 4  # 4 IPFS operations per DB row

        # Only use --progress on IPFS pinning if this option is used
        lastArg = sys.argv[-1]
        if lastArg == "-p":
            progress = True

    else: usage()

    conn.row_factory = sqlite3.Row   # Set query results to dictionary format
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM IPFS_HASH_INDEX")
    rowCount = int(cursor.fetchone()[0])
    print("Database currently has %d rows\n" % rowCount)

    # Primary loop to obtain the files we'll replicate locally
    sql = "SELECT grupe,mhash,vhash,_filename FROM IPFS_HASH_INDEX order by grupe"
    for row in cursor.execute(sql):
        skip += 4                            # 4 IPFS operations per DB row,
        if skip - 4 < OpCounter: continue    # but first row is 0 so minus 4

        if row[0] != grupe:
            grupe = row[0]
            os.system("echo 'ipfs files mkdir /" + grupe + "'")
            os.system("ipfs files mkdir /" + grupe)

        # Process this row into IPFS
        copyPinFiles(row, progress)


except sqlite3.Error as e:
    print("Database error during query: %s\nSQL=%s\n\n" % (e, sql))

except Exception as e:
    print("Exception in query: %s\nSQL=%s\n\n" % (e, sql))

except sqlite3.OperationalError:
    print("ERROR!: Query Failure")

exit(0)
