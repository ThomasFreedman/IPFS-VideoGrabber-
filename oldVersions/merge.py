#!/usr/bin/python3

import re, sys, sqlite3

class sqlMerge(object):
    # Python script to merge data of 2 SQL tables in different SQLite
    # databases. The 2 tables must be IDENTICAL! The constraints of
    # the merged table will exactly match the 1st table. This means
    # if the schemas are identical, columns with the AUTOINCREMENT
    # constraint are not copied. The result will be a 1 - n range
    # for such columns where n is the number of rows in the merged
    # table.
    #
    # NOTE: This class includes a copy method for adding specific rows
    #       and columns between 2 tables that differ, but the caller
    #       is responsible for compatability of the column mapping.
    #
    def __init__(self, parent=None):
        super(sqlMerge, self).__init__()


    # Parse the schema (table definition) and extract the list of columns.
    # Returns a quoted, comma separated list of columns. ALL autoincrement
    # columns omitted. Problems with some private key contraints may occur.
    def getColumnNames(self, schema):
        columns = ""
        for line in schema.split('\n'): # Parse each line and build the list
            col = re.sub(r'\s+(\"[^\"]+\").*', r'\1', line)
            if re.search(r'create', col, flags=re.IGNORECASE): continue
            if re.search(r'autoincrement', line, flags=re.IGNORECASE):
                skip = re.sub(r'\s+(\"[^\"]+\".*)', r'\1', line)
                print("Omitting %s" % skip)
                continue
            columns += col + ","

        return columns[:-1] # Remove the last comma


    # Copies specific columns and rows from source to destination.
    # Tables don't have to be in the same sqlite database, and
    # columns don't have to match either. It's up to the caller
    # to make sure the columns of both tables are compatible.
    #
    # sConn,  dConn  -- opened conn obj for source & destination databases
    # sTable, dTable -- source & destination table names
    # sWhere, dWhere -- sql where clause for source & destination
    # sList,  dList  -- list of columns to copy. List order correlates mapping
    #
    def copy(self, sConn, sTable, sWhere, sList, dConn, dTable, dWhere, dList):
        sCursor = sConn.cursor()
        dCursor = dConn.cursor()
        sWhere = " " + sWhere
        dWhere = " " + dWhere
        errors = False

        try:
            sSql = "SELECT " + sList + " FROM " + sTable + sWhere
            for row in sCursor.execute(sSql):
                dSql = "INSERT INTO " + dTable + " (" + dList + ") VALUES ("
                values = []
                for col in range(len(row)):
                    dSql += "?,"
                    values.append(row[col])    # Values from source table
                dSql = dSql[:-1] + ") " + dWhere
                dCursor.execute(dSql, values)  # Insert row into destination
                dConn.commit()

        except sqlite3.Error as e:
            print("Database error during copy: %s\nSQL=%s\n\n" % (e, sql))
            errors = True

        except Exception as e:
            print("Exception in query: %s\nSQL=%s\n\n" % (e, sql))
            errors = True

        except sqlite3.OperationalError:
            print("ERROR!: Copy Failed")
            cursor.execute("DROP TABLE IF EXISTS " + dTable)
            errors = True

        return errors


    # Add the rows of mergeTable2 to a table in same  database as
    # mergeTable1. The merged results will replace mergeTable1 if
    # the rename flag is set (destroying mergeTable1),  otherwise
    # they will be in mergedTable. The tables must have IDENTICAL
    # schemas.
    def merge(self):
        cursor_a = self.resultsDB.cursor()
        cursor_b = self.mergeDB.cursor()
        mergedTable = self.mergedTable
        source_name = self.mergeTable1
        merge_name = self.mergeTable2

        # Get schemas for each table of merge
        getSchema = "SELECT sql FROM sqlite_master WHERE type='table' "
        getSchema += "AND name='" + source_name + "'"
        cursor_a.execute(getSchema)
        aSql = str(cursor_a.fetchone()[0])
        cursor_b.execute(getSchema)
        bSql = str(cursor_b.fetchone()[0])

        # Remove all quotes and then compare
        a = re.sub(r'\"', r'', aSql, flags=re.MULTILINE)
        b = re.sub(r'\"', r'', bSql, flags=re.MULTILINE)
        if a != b:
            print("Schemas aren't the same!, Aborting merge" % (a,b))
            exit(0)

        print("\nSchemas match, good.")
        print("Merging will begin in the " + mergedTable + " table")
        cursor_a.execute("DROP TABLE IF EXISTS " + mergedTable)
        self.resultsDB.commit()
        opts = re.MULTILINE | re.IGNORECASE
        dSql = re.sub(source_name, mergedTable, aSql, flags=opts)
        cursor_a.execute(dSql)

        print("\nMerging rows in %s and %s" % (source_name, merge_name))

        # Copying contents of source_name to mergedTable,
        # PRESERVING ALL CONSTRAINTS from source_name table.
        columns = self.getColumnNames(aSql)
        sql =  "INSERT INTO " + mergedTable + " (" + columns + ")"
        sql += "SELECT " + columns + " FROM " + source_name
        cursor_a.execute(sql)
        cursor_a.execute("SELECT count(*) FROM " + mergedTable)
        count = int(cursor_a.fetchone()[0])
        print("\nInitial copy of %d rows complete" % count)
        self.resultsDB.commit()

        # Add rows from merge_table in mergeDB to mergedTable in resultsDB
        cursor_b.execute("SELECT count(*) FROM " + merge_name)
        count = int(cursor_b.fetchone()[0])
        print("%s rows to merge from %s" % (count, merge_name))
        print("This will take some time to do...")
        errors = self.copy(self.mergeDB, merge_name, "",
			   columns, self.resultsDB, mergedTable, "", columns)
        if not errors:
            print("\nMerge Successful!\n")
            cursor_a.execute("SELECT count(*) FROM " + mergedTable)
            count = int(cursor_a.fetchone()[0])
            print("%s rows in %s" % (count, mergedTable))
            if self.rename:
                ps = "\nAre you sure you want to replace %s,"
                print(ps % source_name)
                ps = "destroying original table " + source_name + "? (y/n) :"
                inp = input(ps)
                if inp == "y":
                    cursor_a.execute("DROP TABLE IF EXISTS " + source_name)
                    self.resultsDB.commit()
                    tmp = "ALTER TABLE "+mergedTable+" RENAME TO "+source_name
                    cursor_a.execute(tmp)
                    self.resultsDB.commit()

        else: print("\nMerge Failed!\n")

        self.resultsDB.close()
        self.mergeDB.close()
        return


    # The UI: get database file and table names from the user and open
    # (create connection objects) the databases.
    def getMergeParameters(self):
        self.mergeTable1 = None
        self.mergeTable2 = None
        self.mergedTable = None
        self.resultsDB = None
        self.mergeDB = None
        self.rename = False

        print("\nPlease enter db file containing the 1st table to merge,")
        dbFile1 = input("(and for merged result table): ")
        self.resultsDB = sqlite3.connect(dbFile1)
        self.resultsDB.row_factory = lambda cursor, row: row[0] # List format
        cursor_1 = self.resultsDB.cursor()
        cursor_1.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor_1.fetchall()

        print("\nTables Available in 1st DB:")
        print("===================================================\n")
        for t in range(len(tables)):
            print("%d-> %s" % (t, tables[t]))
        print("\n===================================================")

        inp = int(input("Enter the table number: "))
        self.mergeTable1 = tables[inp]

        dbFile2 = input("\nPlease enter db file with the 2nd table to merge: ")
        self.mergeDB = sqlite3.connect(dbFile2)
        self.mergeDB.row_factory = lambda cursor, row: row[0] # List format

        cursor_2 = self.mergeDB.cursor()
        cursor_2.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tabelz = cursor_2.fetchall()

        print("\nTables Available in 2nd DB:")
        print("===================================================\n")
        for t in range(len(tabelz)):
            print("%d-> %s" % (t, tabelz[t]))
        print("\n===================================================")

        inp = int(input("Enter the table number: "))
        self.mergeTable2 = tabelz[inp]

        print("\nEnter the name of merge result table")
        inp = input("(or press Enter for options): ")
        if not inp:
            print("\nReplace %s with merge results (y/n)?" % self.mergeTable1)
            inp = input("CAUTION, destroys original table: ")
            if inp == "y": self.rename = True
            self.mergedTable = self.mergeTable1 + "_merged"
        else: self.mergedTable = inp

        # Now set the row format for use with python dictionaries
        self.resultsDB.close()
        self.resultsDB = sqlite3.connect(dbFile1)
        self.resultsDB.row_factory = sqlite3.Row  # column name / values format

        self.mergeDB.close()
        self.mergeDB = sqlite3.connect(dbFile2)
        self.mergeDB.row_factory = sqlite3.Row  # column name / values format

#        print("%s %s %s %s %s %s" %
#              (self.mergeTable1, self.mergeTable2, self.mergedTable,
#               self.resultsDB, self.mergeDB, self.rename) )
#        exit(0)

    def main(self):
        self.getMergeParameters()
        self.merge()

        return

if __name__ == '__main__':
    app = sqlMerge()
    app.main()
