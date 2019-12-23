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
OP_COUNT = 0     # Count of IPFS operations done
DO_IPFS  = True  # Run IPFS commands AND echo them to STDOUT

def usage():
    cmd = sys.argv[0]
    str = "\nReplicate the files on a remote IPFS server locally.\n"
    str += "Requires Sqlite3 database created by the ytdl-xxxx program.\n\n"
    str += "Usage: " + cmd + " [-h] | <-d file> [-s <int> | -g <grupe>] [-p] [-n]\n"
    str += "where -d=database, -s=start rowID, -g=grupe only, -p=pin progress, -n=No IPFS"
    str += "\n\nipfs must be in $PATH (unless -n), with -s and -g being mutually exclusive.\n"
    str += "To create a log file DON'T use the -p flag, instead use:\n\n"
    str += cmd  + " <args> | tee -a <log file name>\n"
    print(str)
    exit(0)


# Prints IPFS operations done and day / time marker on console
def printMarker():
    global OP_COUNT

    OP_COUNT += 1
    now = datetime.now()
    m = "%s IPFS Operations Completed: %d"
    mark = m % (now.strftime("%a %H:%M:%S"), OP_COUNT)
    print(mark, flush=True)


# Copy video & meta files from remote node to local virtual folder & pin them.
# Show progress as IPFS ops completed with day and time. The prog variable (if
# set) determines whether the  pinning operation  reports incremental progress
# (makes for very long log files if tee is used on the output). To restart the
# replication process use the -s flag with the rowID.  A few errors are likely
# if some of the IPFS operations for that row were completed; the program will
# not stop, but errors will appear for such cases.
def copyPinFiles(row, prog):
    pky   = row[0]   # Row's primary key, can change if merge.py is used
    grupe = row[1]   # Name for this collection of videos
    vhash = row[2]   # IPFS hash for video file
    mhash = row[3]   # IPFS hash for json metadata for this video
    vFile = os.path.basename(row[4])         # Remove the path, leave filename
    mFile  = vFile.split(".")[0] + ".info.json"
    if prog: progress = "--progress"
    else: progress = ''

    print("\nRow ID = %d" % pky)
    copyCmd = "ipfs files cp /ipfs/" + vhash + " /" + grupe + "/" + vFile
    print(copyCmd, flush=True)
    if DO_IPFS: os.system(copyCmd + "; sleep .1")
    printMarker()

    pinCmd = "ipfs pin add --recursive=true %s /ipfs/%s" % (progress, vhash)
    print(pinCmd, flush=True)
    if DO_IPFS: os.system(pinCmd + "; sleep .1\n")
    printMarker()

    copyCmd = "ipfs files cp /ipfs/" + mhash + " /" + grupe + "/" + mFile
    print("\n" + copyCmd, flush=True)
    if DO_IPFS: os.system(copyCmd + "; sleep .1")
    printMarker()

    pinCmd = "ipfs pin add --recursive=true %s /ipfs/%s" % (progress, mhash)
    print(pinCmd, flush=True)
    if DO_IPFS: os.system(pinCmd + "; sleep .1")
    printMarker()



##############################################################################
#                                                                            #
# The main loop                                                              #
#                                                                            #
##############################################################################
conn  = errors = sql = grp = grupe = progress = False
start = rowCounter = 0
argc  = len(sys.argv)

try:
    # Parse command line
    if argc > 1:
        if sys.argv[1] == "-h":
            usage()

        # Required parameter: the SQLite database file
        if argc > 2 and sys.argv[1] == "-d":
            dbFile = sys.argv[2]
            conn = sqlite3.connect(dbFile) # Failure to open is exception
        else: usage()

        # Option to start with a specific pky value (row ID) in the database
        if argc > 4 and sys.argv[3] == "-s":
            start = int(sys.argv[4])        # 4 IPFS operations per DB row

        # Option to limit replication to a single grupe
        if argc > 4 and sys.argv[3] == "-g":
            grp = sys.argv[4]               # The grupe to replicate

        # Option to use --progress on IPFS pinning
        if sys.argv[-1] == "-p" or sys.argv[-2] == "-p":
            progress = True

        # Option to just echo IPFS commands to STDOUT (debug mode)
        if sys.argv[-1] == "-n":
            DO_IPFS = False

    else: usage()

    conn.row_factory = sqlite3.Row   # Set query results to dictionary format
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM IPFS_HASH_INDEX")
    totalRows = int(cursor.fetchone()[0])
    tim = datetime.now().strftime("%a %H:%M:%S")

    # Select the files we'll replicate and print starting header
    sql =  "SELECT pky,grupe,mhash,vhash,_filename FROM IPFS_HASH_INDEX"
    sql += " WHERE season_number is not null "   # Only verified hashes
    header = "%s DB Rows: %d. Starting replication with " % (tim, totalRows)
    if start:
        sql += "and pky >= %d " % start          # Start at a specific row
        header += "rowID(pky)=" + str(start)
    elif grp:
        sql += "and grupe = '%s' " % grp         # Replicate grupe only
        header += "grupe=" + grp
    else: header += "row 1"
    print(header)
    sql += "order by grupe"

    # Primary loop which pulls file info from the DB for IPFS replication
    for row in cursor.execute(sql):
        rowCounter += 1
        if grp and row[1] != grp: continue

        # Temporary filters
        if row[1] == 'morse': continue            # We already have these
        if row[1] == 'freeRoss': continue         # We already have this
        if row[1] == 'larkenRose': continue       # Sadly these are probably lost
        if row[1] == 'jordanPeterson': continue   # ...as are these

        if row[1] != grupe:
            grupe = row[1]
            print("ipfs files mkdir /" + grupe, flush=True)
            if DO_IPFS:
                os.system("ipfs files mkdir /" + grupe)

        # Replicate this row's files into the local IPFS server
        copyPinFiles(row, progress)


except Exception as e:
    print("Exception: %s\n" % e)

except sqlite3.Error as e:
    print("Database error during query: %s\nSQL=%s\n" % (e, sql))

except sqlite3.OperationalError:
    print("ERROR!: Query Failure")

exit(0)


