#!/usr/bin/python3
import PySimpleGUI as sg
import sqlite3 as sql
import os

# GUI layouts and Event Processing for PBox Search

class pBoxQuery:
    def __init__(self):
        self.DBfiles = ['2021-02-24_tx.sqlite','2021-02-24_ny.sqlite']
        self.Pwd = os.path.dirname(os.path.realpath(__file__)) + '/'
        self.Conn = None
        self.Day6 = ''          # Need to persist date and time b/c can't read value of text field
        self.Tmv6 = ''
        self.Max7 = 1000000     # TODO - come up with a better way to handle widget defaults.
        self.LBox = []          # Each numeric field may require a different max value for example
        self.LBoxMode = sg.LISTBOX_SELECT_MODE_MULTIPLE
        self.Where = []
        self.Grupes = []
        self.Ext = []
        self.ExKey = []
        self.Format = []


        sg.set_global_icon(r'/home/owner/Code/tv-watcher/pirateFlag.png')

        # Define a custom theme for this app:
        sg.LOOK_AND_FEEL_TABLE['PirateTheme'] = {'BACKGROUND': '#000000', "TEXT": "gold",
                                                 "FONT": ("Helvetica", 11),
                                                 "INPUT": "#393a32", "TEXT_INPUT": "#E7C855",
                                                 "SCROLL": "#E7C855", "BORDER": 1,
                                                 "BUTTON": ("red", "gold"),
                                                 'PROGRESS': ('#D1826B', '#CC8019'), "SLIDER_DEPTH": 1,
                                                 "PROGRESS_DEPTH": 0, "ACCENT1": "#c15226",
                                                 "ACCENT2": "#7a4d5f", "ACCENT3": "#889743" }

        # Although there are many themes in the menu, they cannot be activated during a session. Theme
        # selection will become active on the next start of the app. The call below is thus temporary.
        sg.theme("PirateTheme")   # Activate the custom pirate theme colors and settings

        # Metadata fields in SQLite DB available to use as search criteria.
        # Each field (column in SQLite) is categorized under an input state.
        # These names define those states for each field to select the right
        # widget to obtain user input for that field.
        # These are the query builder states as the filter criteria is selected.
        self.Start     = 0      # Starting state where users select a field
        self.ListBox   = 1      # Select value(s) from a list (like Start state)
        self.TextBox   = 2      # any; if int > < =, starts with ends with contains, exact...
        self.ComboBox  = 3      # Choice from a list or can type in items not in list
        self.Radio     = 4      # Choose 1 of n
        self.CheckBox  = 5      # Choose any / all of n
        self.Calendar  = 6      # Date and optional time in SQLite3 format: 'YYYYMMDD HH:MM:SS'
        self.NumSlide  = 7      # Linear slider to select a numeric value or type one in
        self.Time      = 8      # Returns number of seconds. Displayed as HH:MM:SS

        #
        # CONSIDER LOADING THE FOLLOWING FROM A JSON CONFIG FILE
        #
        self.Metafields = {
            "grupe": self.ListBox, "id": self.TextBox, "pky": self.NumSlide, "vhash": self.TextBox,
            "mhash": self.TextBox, "width": self.NumSlide, "height": self.NumSlide, "title": self.TextBox,
            "license": self.TextBox, "fulltitle": self.TextBox, "description": self.TextBox, "_filename": self.TextBox,
            "view_count": self.NumSlide, "like_count": self.NumSlide, "dislike_count": self.NumSlide,
            "webpage_url": self.TextBox, "extractor_key": self.ListBox, "format_note": self.ListBox,
            "ext": self.ListBox, "sqlts": self.Calendar, "upload_date": self.Calendar, "release_date": self.Calendar,
            "average_rating": self.NumSlide, "duration": self.Time
            }

    # Perform a SQL query that selects only 1 column and return the results in a list
    def getListFromSql(self, sql):
        out = []
        for r in self.Conn.cursor().execute(sql).fetchall():
            out.append(r[0])
        return out

    # Open the SQLite database file for one of the preset servers based on the idx
    def openDatabase(self, window, name, idx):
        if self.Conn: self.Conn.close()
        self.Conn = sql.connect(self.Pwd + self.DBfiles[idx])
        self.Conn.row_factory = sql.Row     # Results as a python dictionary

        # Get selections for multi-select items (radio buttons, checkboxes, listboxes & comboboxes
        grpSql = "select distinct grupe from IPFS_HASH_INDEX;"
        self.Grupes = pBoxQuery.getListFromSql(self, grpSql)
        extSql = "select distinct ext from IPFS_HASH_INDEX where ext not like '%unknown%';"
        self.Ext = pBoxQuery.getListFromSql(self, extSql)
        exKSql = "select distinct extractor_key from IPFS_HASH_INDEX where extractor_key not like '%unknown%';"
        self.ExKey = pBoxQuery.getListFromSql(self, exKSql)
        fmtSql = "select distinct format_note from IPFS_HASH_INDEX where format_note not like '%unknown%';"
        self.Format = pBoxQuery.getListFromSql(self, fmtSql)

        # Not sure of best way to present multiselect elements whose selections come from the DB
        # For now, all fields of type ListBox will show grupe list
        self.LBox = self.Grupes

        count = self.Conn.cursor().execute("SELECT COUNT(*) FROM IPFS_HASH_INDEX;")

        # Show some stats about the DB in a popup
        sg.popup(f"{count.fetchone()[0]} items on the {name} node",
                 f"in {len(self.Grupes)} groups and ",
                 f"with {len(self.Ext)} media types from",
                 f"{len(self.ExKey)} sources", font=("Helvetica", 11, "bold"))

        window['-META-'].update(values=list(self.Metafields.keys()), disabled=False)

    # Run the search query using the
    def runQuery(self, window):
        result = []
        sql = "SELECT pky, upload_date, ext, CAST(duration as int), title from IPFS_HASH_INDEX WHERE "
        if len(self.Where) == 0:
            sql += " 1=1 limit 50"
        else:
            for clause in self.Where:
                sql += clause
        rows = self.Conn.cursor().execute(sql).fetchall()
        items = len(rows)
        if len(rows) > 0:
            result = ['  KEY UPLOAD DATE  TYPE  DURATION  TITLE']
            for r in rows:
                # Strip unicode characters Tcl doesn't like from title
                char_list = [r[4][j] for j in range(len(r[4])) if ord(r[4][j]) in range(65536)]
                title = ''
                for j in char_list:
                    title += j

                result.append("%5s %11s %5s %9s  %s" % (r[0], r[1], r[2], r[3], title))
        else: result.append("No results found based on your search criteria")
        window['-ROWS-'].update(f"{items} items")
        window['-RESULTS-'].update(values=result)

    def getHash(self, key):
        sql = f"SELECT vhash from IPFS_HASH_INDEX WHERE pky={key}"
        return self.Conn.cursor().execute(sql).fetchone()[0]

    def resetAll(self, window):
        state = pBoxQuery.resetToState0(self, window)
        pBoxQuery.resetWidgets(self, window, range(1, 9))
        self.Where = []
        if self.Conn: self.Conn.close()
        window['-META-'].update(values=[])
        window['-META-'].update(disabled=True)
        window['-TODO-'].update(values=[])
        window['-ROWS-'].update('')
        window['-RESULTS-'].update(values=[])
        window['-SEARCH-'].update(disabled=True)
        window['-CLEAR-'].update(disabled=True)
        return state

    # Split array lst into segments of size items in each segment
    def splitList(self, lst, size):
        for i in range(0, len(lst), size):
            yield lst[i:i + size]

    # Form a list of theme menus with unique keys (Note - keys aren't returned!)
    # Since the theme names are unique strings the only thing necessary is to
    # identify each value returned by these items is actually a theme.
    def createThemeMenus(self):
        t = int(0)
        themeMenuGroups = []
        tGroups = list(pBoxQuery.splitList(self, sg.theme_list(), 10))
        for g in range(0, len(tGroups)):
            themeMenuGroups.append("Group %d" % (g + 1))
            grpLst = []
            for thm in tGroups[g]:
                grpLst.append("%s::-THM%d-" % (thm, t))
                t += 1
            themeMenuGroups.append(grpLst)
        return themeMenuGroups

    def resetWidgets(self, window, widgetList):
        # For each state in the widgetList process the list of reset actions
        # returned from the reset method defined just above its' layout.
        for item in widgetList:
            m = globals()['pBoxQuery']()     # global namespace allows this to be called externally too
            elements = getattr(m, f"qbResetInput{item}")()   # Retrieve dictionary of elements to reset
            for element in elements.keys():
                for attr in elements[element]:
                     target = f"window['{element}'].update({attr[0:]})"
                     #print(target)
                     eval(target)

    # Clear search results and return to state 0 to select other criteria for a new search
    def resetToState0(self, window):
        window[f'-META-'].Widget.selection_clear(0, len(self.Metafields))
        for s in range(1, 9):
            window[f'-ST{s}-'].update(visible=False)
        window['-ST0-'].update(visible=True)
        window['-META-'].update(scroll_to_index=0)
        return 0

    # ----------- STATE 0: SPECIAL CASE   -   choose from a list element to build query  ----------- #
    def qbMetaInput0(self):     # Why is initial position of text different than subsequent ones?
        return [[               # Without newlines initial position is vertically centered
            sg.Text('\n\n\n\n\n<-- Select an item and set a value to filter results', key='-MSG0-',
                    justification="left", pad=((0,311), (0,0)))
            ]]

    # ----------- ELEMENT LAYOUTS used to gather search criteria inputs and their resets ----------- #
    # List input widget reset to defaults. Layout follows
    def qbResetInput1(self):
        return {'-LBOX-': [],
                '-MSG1-': ["''"],
                #'Ok1-': ['disabled=True']
                }
    def qbMetaInput1(self):
        tooltip = "Selection of multiple items is allowed here"
        return [
            [sg.Listbox(self.LBox, select_mode=self.LBoxMode, key='-LBOX1-', enable_events=True,
                        size=(20, 6), tooltip=tooltip, pad=((200, 0), (15, 15))),
             sg.Button('Ok', font=("Helvetica", 11, "bold"), key='Ok1-', disabled=True, pad=((10, 190), (10, 15)))],
            [sg.Text('', key='-MSG1-', size=(55, 1), pad=((25, 5), (0, 10))),
             sg.Button('Cancel', font=("Helvetica", 11, "bold"), pad=((5, 25), (0, 15)))]
            ]


    # Text input widget reset to defaults. Layout follows
    def qbResetInput2(self):
        return {'-MSG2-': ["''"],
                '-TXT2-': ["''"],
                '-HAS2-': ['value=True'],
                'Ok2-': ['disabled=True']
                }
    def qbMetaInput2(self):
        return [
            [sg.Text('', size=(70, 1))],  # Empty row for vertical spacing of content below
            [sg.Button('Ok', font=("Helvetica", 11, "bold"), key='Ok2-', disabled=True, pad=((10, 10), (10, 0))),
             sg.InputText(key='-TXT2-', enable_events=True, size=(62, 1), pad=((0, 10), (10, 0)),
                          text_color="black", background_color="gold")],
            [sg.Radio('Contains', "TXT", key='-HAS2-', default=True, pad=((125, 0), (7, 5))),
             sg.Radio('Starts with', "TXT", key='-STR2-', pad=((15, 0), (7, 5))),
             sg.Radio('Ends with', "TXT", key='-END2-', pad=((15, 0), (7, 5))),
             sg.Radio('Equals', "TXT", key='-EQU2-', pad=((15, 0), (7, 5)))],

            [sg.Text('', key='-MSG2-', pad=((25, 5), (20, 0)), size=(55, 1)),
             sg.Button('Cancel', font=("Helvetica", 11, "bold"), pad=((0, 25), (20, 0)))]
            ]


    # TODO: ComboBox input widget reset to defaults. Layout follows
    def qbResetInput3(self):
        return {'-MSG3-': ["''"],
                #'Ok3-': ['disabled=True']
                }
    def qbMetaInput3(self):
        return [[
            sg.Text('', key='-MSG3-', pad=((0, 14), (30, 0)), size=(82, 1)),
            sg.Button('Cancel', font=("Helvetica", 11, "bold"), pad=((0, 10), (90, 0)))
            ]]


    # TODO: Radio Buttons input widget reset to defaults. Layout follows
    def qbResetInput4(self):
        return {'-MSG4-': ["''"],
                #'Ok4-': ['disabled=True']
                }
    def qbMetaInput4(self):
        return [[
            sg.Text('', key='-MSG4-', pad=((0, 14), (30, 0)), size=(82, 1)),
            sg.Button('Cancel', font=("Helvetica", 11, "bold"), pad=((0, 10), (90, 0)))
            ]]


    # TODO: Checkbox input widget reset to defaults. Layout follows
    def qbResetInput5(self):
        return {'-MSG5-': ["''"],
                #'Ok5-': ['disabled=True']
                }
    def qbMetaInput5(self):
        return [[
            sg.Text('', key='-MSG5-', pad=((0, 14), (30, 0)), size=(82, 1)),
            sg.Button('Cancel', font=("Helvetica", 11, "bold"), pad=((0, 10), (90, 0)))
            ]]


    # Date and optional time of day input widget reset to defaults. Layout follows
    def qbResetInput6(self):
        return {'-DAT6-': ["''"],
                '-TMV6-': ['disabled=True', "''"],
                '-SLD6-': ['disabled=True', 'value=0'],
                '-EQU6-': ['value=True'],
                '-MSG6-': ["''"],
                'Ok6-': ['disabled=True']
                }    
    def qbMetaInput6(self):
        return [
            [sg.Button('Ok', font=("Helvetica", 11, "bold"), key='Ok6-', disabled=True, pad=((30, 0), (15, 5))),
             sg.Button('Calendar', font=("Helvetica", 11, "bold"), pad=((10, 30), (15, 5))),
             sg.Text('', key='-DAT6-', size=(17, 1), pad=((0, 0), (15, 5)))],
            [sg.Text('Add a time of day by sliding button below.. or enter it here-->', font=("Helvetica", 11),
                     size=(50, 1), pad=((30, 16), (14, 7))),
             sg.InputText(key='-TMV6-', enable_events=True, font=("Helvetica", 11), size=(7, 1),
                          text_color="black", disabled=True, background_color="gold",
                          default_text="")],
            [sg.Slider(key='-SLD6-', disabled=True, enable_events=True, size=(60, 15),
                       disable_number_display=True, orientation='h', range=(0, 86399),
                       tooltip="Slide button to pick a time. Click or hold to\nleft or right of button for fine adjustment.",
                       default_value=0, pad=((30, 0), (0, 0)))],
            [sg.Radio('Earlier than', "ERQ", key='-MAX6-',  pad=((150, 0), (7, 5))),
             sg.Radio('Later than', "ERQ", key='-MIN6-', pad=((15, 0), (7, 5))),
             sg.Radio('Equal to', "ERQ", key='-EQU6-', pad=((15, 0), (7, 5)))],

            [sg.Text('', key='-MSG6-', pad=((30, 5), (0, 0)), size=(56, 1)),
             sg.Button('Cancel', font=("Helvetica", 11, "bold"), pad=((0, 40), (3, 0)))]
            ]


    # Numeric input widget reset to defaults. Layout follows
    def qbResetInput7(self):
        return { '-NUM7-': ["'0'"],  # evable_events is not updateable.
                                     # Possibly disable=False on slider?
                '-SLD7-': ['range=(0, self.Max7)','value=0'],
                '-MSG7-': ["''"],
                '-EQU7-': ['value=True'],
                'Ok7-': ['disabled=True']
                }
    def qbMetaInput7(self):
        tooltip = "Slide button to pick a time. Click or hold to\nleft or right of button for fine adjustment."
        return [
            [sg.Text('', size=(70, 1))],  # Empty row for vertical spacing of content below
            [sg.Radio('Less or =', "LME", key='-MAX7-', pad=((220, 0), (0, 5))),
             sg.Radio('More or =', "LME", key='-MIN7-', pad=((15, 0), (0, 5))),
             sg.Radio('Equal to', "LME", key='-EQU7-', pad=((15, 0), (0, 5)))],
            [sg.Button('Ok', font=("Helvetica", 11, "bold"), key='Ok7-', disabled=True, pad=((5, 10), (15, 0))),
             sg.InputText(key='-NUM7-', enable_events=True, size=(7, 1), pad=((0, 0), (15, 0)),
                          default_text='0', text_color="black", background_color="gold"),
             sg.Slider(key='-SLD7-', enable_events=True, size=(49, 15), orientation='h',
                       disable_number_display=True, pad=((12, 0), (15, 0)),
                       tooltip=tooltip, range=(0, self.Max7), default_value='')],

            [sg.Text('', key='-MSG7-', pad=((35, 10), (7, 10)), size=(52, 1)),
             sg.Button('Cancel', font=("Helvetica", 11, "bold"), pad=((0, 0), (7, 10)))]
            ]


    # Duration in seconds input widget reset to defaults. Layout follows
    def qbResetInput8(self):
        return {'-MIN8-': ['value=True'],
                '-TIM8-': ["'00:00:00'"],
                '-SEC8-': ['value=""'],
                '-SLD8-': ['value=0', 'disabled=False', 'range=(0, 9000)'],
                '-MSG8-': ["''"],
                'Ok8-': ['disabled=True']
                }
    def qbMetaInput8(self):
        return [
            [sg.Radio('Minimum', "MNX", key='-MIN8-', pad=((275, 0), (10, 10))),
             sg.Radio('Maximum', "MNX", key='-MAX8-', pad=((0, 0), (10, 10)))],
            [sg.Text('Seconds', font=("Helvetica", 11), pad=((56, 140), (20, 0))),
             sg.Text('Time (hh:mm:ss)=', font=("Helvetica", 11), pad=((0, 0), (20, 0))),
             sg.Text('00:00:00', key='-TIM8-', font=("Helvetica", 11), pad=((0, 0), (20, 0)), size=(8, 1))],

            [sg.Button('Ok', font=("Helvetica", 11, "bold"), key='Ok8-', pad=((0,3),(0,0)),disabled=True),
             sg.InputText('', key='-SEC8-', enable_events=True, size=(7, 1),
                          text_color="black", background_color="gold"),
             sg.Slider(key='-SLD8-', enable_events=True, disabled=True, size=(49, 15),
                       disable_number_display=True, orientation='h',
                       tooltip="Slide button to pick a time. Click or hold to\nleft or right of button for fine adjustment.",
                       range=(0, 9000), default_value=0)],
            [sg.Text('', key='-MSG8-', pad=((35, 10), (7, 0)), size=(50, 1)),
             sg.Button('Cancel', font=("Helvetica", 11, "bold"), pad=((0, 0), (7, 0)))
             ]
        ]

    # Process input collected from user and create SQL where clause for it
    def addSQL2SearchCriteriaList(self, window, state, field, input):
        self.resetWidgets(window, [state])  # We have all inputs, reset the form
        window['-SEARCH-'].update(disabled=False)
        window['-CLEAR-'].update(disabled=False)

        if len(self.Where) > 0: clause = ' and '
        else: clause = ''

        # Process selections from a list
        if state == self.ListBox:
            choices = len(input['list'])
            if choices > 0:
                c = 0
                clause += f"{field} in ("
                for choice in input['list']:
                    clause += f"'{choice}'"
                    c += 1
                    if c < choices: clause += ','
                clause += ')'
                self.Where.append(clause)
                window['-TODO-'].update(values=self.Where)

        # Process text input
        elif state == self.TextBox:
            if input['equ']: val = f"{field} = {input['text']}"
            elif input['has']: val = f"{field} like '%" + input['text'] + "%'"
            elif input['str']: val = f"{field} like '" + input['text'] + "%'"
            elif input['end']: val = f"{field} like '%" + input['text'] + "'"
            clause += val
            self.Where.append(clause)
            window['-TODO-'].update(values=self.Where)
        elif state == self.ComboBox:
            pass
        elif state == self.Radio:
            pass
        elif state == self.CheckBox:
            pass

        # Process Date and optional time input
        elif state == self.Calendar:
            if input['max']: mnx = '<='
            elif input['min']: mnx = '>='
            else: mnx = '='
            dateTime = input['datetm']
            clause += f"{field} {mnx} '{dateTime}'"
            self.Where.append(clause)
            window['-TODO-'].update(values=self.Where)

        # Process numeric input
        elif state == self.NumSlide:
            if input['max']: mnx = '<='
            elif input['min']: mnx = '>='
            else: mnx = '='
            clause += f"CAST({field} as int) {mnx} {input['number']}"
            self.Where.append(clause)
            window['-TODO-'].update(values=self.Where)

        # Process time input
        elif state == self.Time:
            if input['min']: mnx = '>='
            else: mnx = '<='
            clause += f"CAST({field} as int) {mnx} {input['seconds']}"
            self.Where.append(clause)
            window['-TODO-'].update(values=self.Where)

    # ----------- Widget EVENT PROCESSING methods ----------- #
    # These methods process events generated from the layouts defined above. Ok button should only be active
    # for the state if input is validated and returned in dictionary form.  TODO: revisit default values and
    # widget specific persistent values now that the reset (default) element state is handled.
    def handleState1(self, window, event, values):
        lstInput = []
        if event == '-LBOX1-':
            lstInput.append('Get List Items')
            window['Ok1-'].update(disabled=False)
            if len(lstInput) > 0:
                return {'list': values['-LBOX1-']}

    def handleState2(self, window, event, values):
        txtInput = None
        if event in ('-TXT2-'):
            txtInput = str(values['-TXT2-'])
            window['Ok2-'].update(disabled=False)
        if txtInput is not None and len(txtInput) > 0:
            self.Txt2 = txtInput
            return {'text': self.Txt2, 'has': values['-HAS2-'], 'str': values['-STR2-'],
                    'end': values['-END2-'], 'equ': values['-EQU2-']}

    def handleState3(self, window, event, values):
        pass

    def handleState4(self, window, event, values):
        pass

    def handleState5(self, window, event, values):
        pass

    def handleState6(self, window, event, values):
        if event == 'Calendar':
            window['-DAT6-'].update("")
            window['-SLD6-'].update(disabled=True)
            d = sg.popup_get_date(no_titlebar=False)
            if d is not None:
                date = "%d-%02d-%02d " % (d[2], d[0], d[1])
                self.Day6 = date
                self.Tmv6 = ''    # Reset time when a new date is selected
                window['Ok6-'].update(disabled=False)
                window['-TMV6-'].update(disabled=False)
                window['-SLD6-'].update(disabled=False)

        elif event == '-SLD6-':
            slider = int(values['-SLD6-'])
            if slider > 0:
                minutes, s = divmod(slider, 60)
                h, m = divmod(minutes, 60)
                self.Tmv6 = "%02d:%02d:%02d" % (h, m, s)
            else:
                self.Tmv6 = ""
            window['-TMV6-'].update(self.Tmv6)
        elif event == '-TMV6-':
            t = values['-TMV6-'].split(':')
            if len(t) == 3 and t[0].isdecimal() and \
                    t[1].isdecimal() and t[2].isdecimal():
                h = int(t[0]) % 24
                m = int(t[1]) % 60
                s = int(t[2]) % 60
                self.Tmv6 = "%02d:%02d:%02d" % (h, m, s)
            else:
                self.Tmv6 = ""
        date = "%s %s" % (self.Day6, self.Tmv6)
        window['-DAT6-'].update(date)
        return {'datetm': date.rstrip(), 'min': values['-MIN6-'], 'max': values['-MAX6-'], 'equ': values['-EQU6-']}

    # Get a numeric value. If a number is entered into the input box,
    # update the slider with that value. Max value allowed is set in self.Max7
    def handleState7(self, window, event, values):
        numInput = None
        if event in ('-SLD7-', '-NUM7-'):
            if event == '-SLD7-':
                numInput = int(values['-SLD7-'])
                window['-NUM7-'].update(numInput)
            else:
                numInput = str(values['-NUM7-'])[0:7]
                if numInput.isdecimal():
                    numInput = int(numInput)
                    window['-SLD7-'].update(numInput)
                else:
                    numInput = 0
                    window['-NUM7-'].update(numInput)

            window['-NUM7-'].update(numInput)
            window['Ok7-'].update(disabled=False)
            return {'number': numInput, 'min': values['-MIN7-'], 'max': values['-MAX7-'], 'equ': values['-EQU7-']}

    # Update the text element with time as hrs, mins, secs string,
    # and slider input to value in seconds. If a number is entered
    # into the input box, update the slider with that value.
    # BUG: user must select max radio button before entering a value or it will be ignored
    def handleState8(self, window, event, values):
        secInput = None
        if event in ('-SLD8-', '-SEC8-'):
            if event == '-SLD8-':
                secInput = int(values['-SLD8-'])
                window['-SEC8-'].update(secInput)          # Update text input to match
            else:
                secInput = str(values['-SEC8-'])[0:5]
                if secInput.isdecimal():
                    secInput = int(secInput)
                    window['-SLD8-'].update(secInput)      # Update slider imput to match
                else:
                    secInput = 0
                    window['-SEC8-'].update(secInput)

            # Update the time text element based on slider or text input
            minutes, s = divmod(secInput, 60)
            h, m = divmod(minutes, 60)
            window['-TIM8-'].update("%02d:%02d:%02d" % (h, m, s))
            window['Ok8-'].update(disabled=False)
            return {'seconds': secInput, 'min': values['-MIN8-'], 'max': values['-MAX8-']}

    # ------ Top menu bar definition ------ #
    def topMenuBar(self):
        return [['File',   ['Save as',
                            'Pin', ['Pin Folder', 'Pin Hash Local', 'Pin Search Results'],
                            'Open IPFS Hash Address',
                            'Exit']],
                ['Config', ['IPFS Server', ['Texas', 'New York'],
                            'Programs',    ['Media Player', 'PDF Viewer', 'Text Viewer', 'Web Browser', 'File Manager'],
                            'Settings',    ['Theme', pBoxQuery.createThemeMenus(self),
                                            'Favorites', ['Highwire', 'Corbett Report', 'Truthstream Media'],
                                            'Results per page', ['10', '20', '30']]]],
                ['Help', 'About...']]

    # ------ Query builder - left column ------ #
    def queryBuilder(self):
        return [
            [sg.Frame('Search Criteria', [[  # Criteria Selection layouts
                sg.Listbox([], disabled=True, key='-META-', enable_events=True, size=(15, 10)),
                sg.Column(pBoxQuery.qbMetaInput0(self), visible=True, key='-ST0-'),
                sg.Column(pBoxQuery.qbMetaInput1(self), visible=False, key='-ST1-'),
                sg.Column(pBoxQuery.qbMetaInput2(self), visible=False, key='-ST2-'),
                sg.Column(pBoxQuery.qbMetaInput3(self), visible=False, key='-ST3-'),
                sg.Column(pBoxQuery.qbMetaInput4(self), visible=False, key='-ST4-'),
                sg.Column(pBoxQuery.qbMetaInput5(self), visible=False, key='-ST5-'),
                sg.Column(pBoxQuery.qbMetaInput6(self), visible=False, key='-ST6-'),
                sg.Column(pBoxQuery.qbMetaInput7(self), visible=False, key='-ST7-'),
                sg.Column(pBoxQuery.qbMetaInput8(self), visible=False, key='-ST8-')
            ]], size=(100, 18), key='-SRCH-')],

            [sg.Frame('Selected Search Criteria', [[
                sg.Listbox([], key='-TODO-', background_color="black", size=(88, 10))]])]
        ]

    # Right column listbox is used for search results
    def queryResults(self):
        return [
            [sg.Frame('Search Results', [[
                sg.Listbox('', key='-RESULTS-', background_color="black", size=(50, 23),
                           font=('Courier', 10, 'bold'), enable_events=True)
                                        ]])
                ]
            ]

        # ----------- This is the complete GUI layout ----------- #
    def pBoxSearchApp(self):
        return [
            [sg.Menu(pBoxQuery.topMenuBar(self), key='-MENU-', tearoff=True)],  # Top Menu bar
            [sg.Column(pBoxQuery.queryBuilder(self), visible=True),
             sg.Column(pBoxQuery.queryResults(self), visible=True)],

            [sg.Button('Search', key='-SEARCH-', disabled=True, font=("Helvetica", 11, "bold"),
                       pad=((15,0),(0,0))),
             sg.Button('Clear', key='-CLEAR-', disabled=True, font=("Helvetica", 11, "bold"),
                       pad=((15,0),(0,0))),
             sg.Button('Exit', font=("Helvetica", 11, "bold"), pad=((15, 580),(0,0))),
             sg.Button('Next', key='-NEXTP-', disabled=True, font=("Helvetica", 11, "bold"),
                     pad=((15, 0), (0, 0))),
             sg.Button('Previous', key='-PREVP-', disabled=True, font=("Helvetica", 11, "bold"),
                       pad=((15, 0), (0, 0))),
             sg.Text('Page 1', key='-PAGE-', font=("Helvetica", 11),
                     pad=((15, 30), (0, 0))),
             sg.Text('', key='-ROWS-', size=(12, 1), font=("Helvetica", 11))]
        ]

