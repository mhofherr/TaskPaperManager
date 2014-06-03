#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
# TaskPaperManager
originally based on a small script for printing a task summary from K. Marchand
now completely re-written and modified for my own requirements

License: GPL v3 (for details see LICENSE file)

## Data structure

**prio**: priority of the task - high, medium or low; mapped to 1, 2 or 3
**startdate**: when will the task be visible - format: yyyy-mm-dd
**project**: with which project is the task associated
**taskline**: the actual task line
**done**: is it done?; based on @done tag; boolean
**repeat**: only for tasks in the project "repeat"; boolean
**repeatinterval**: the repeat inteval is given by a number followed by an interval type; e.g.
    2w = 2 weeks
    3d = 3 days
    1m = 1 month
**duedate**: same format as startdate
**duesoon**: boolean; true if today is duedate minus DUEDELTA in DUEINTERVAL (constants) or less
**overdue**: boolean; true if today is after duedate
**maybe**: boolean; true if task should be moved to maybe list
"""


from __future__ import (absolute_import, division, print_function, unicode_literals)

import dateutil.relativedelta
import email.mime.text
import dateutil.parser
import datetime
import jinja2
import markdown
import logging
import getopt
import shutil
import sys
import re
import urllib
import smtplib
import gnupg
import sqlite3
import cStringIO
import weasyprint

from six.moves import configparser
from six.moves import http_client

TODAY = datetime.datetime.date(datetime.datetime.now())
DAYBEFORE = TODAY - datetime.timedelta(days=1)


def initDB():
    """create a new sqlite in-memory db instance and create the table structure

    :returns: connection object for the database"""

    try:
        conn = sqlite3.connect(':memory:', isolation_level="DEFERRED")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('''CREATE TABLE tasks(
            taskid INTEGER PRIMARY KEY,
            prio INTEGER,
            startdate TEXT,
            project TEXT,
            taskline TEXT,
            done INTEGER,
            repeat INTEGER,
            repeatinterval text,
            duedate TEXT,
            duesoon INTEGER,
            overdue INTEGER,
            maybe INTEGER
            )''')
        cur.execute('''CREATE TABLE notes(
            noteid INTEGER PRIMARY KEY,
            taskid INTEGER,
            noteline text,
            FOREIGN KEY(taskid) REFERENCES tasks(taskid)
            )''')
        conn.commit()
    except sqlite3.Error as e:
        sys.exit("initDB - An error occurred: {0}".format(e.args[0]))
    return conn


def usage():
    """Prints usage information."""

    print('tpm.py -i <inputfile> -c <configfile> -m <mode:daily|review>')


def parseArgs(argv):
    """parse and verify the commandline args

    :param argv: list of commandline arguments, minus the first
    :returns: path to taskpaper file, path to the config file and the mode (daily|review) of operation
    """

    inputfile = ''
    configfile = ''
    modus = ''
    try:
        opts, args = getopt.getopt(argv, "hi:c:m:", ["help", "infile=", "conffile=", "modus="])
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        elif opt in ("-i", "--infile"):
            inputfile = arg
        elif opt in ("-c", "--conffile"):
            configfile = arg
        elif opt in ("-m", "--modus"):
            modus = arg
    if inputfile == '' or configfile == '' or modus == '':
        usage()
        sys.exit()
    if modus != 'daily' and modus != "review":
        usage()
        sys.exit()
    return (inputfile, configfile, modus)


def removeTaskParts(instring, removelist):
    """"remove elements from a taskpaper string

    :param instring: a string to be parsed
    :param removelist: the tags to be removed from the string
    :returns: the new strings minus the removed tags
    """

    outstring = ''
    cut_string = instring.split(' ')
    cut_removelist = removelist.split(' ')
    for i in range(0, len(cut_string)):
        for j in range(0, len(cut_removelist)):
            if cut_removelist[j] in cut_string[i]:
                break
        else:
            outstring = '{0}{1} '.format(outstring, cut_string[i])
    return outstring


class settings:
    """ contains the settings for TPM, parsed from the config file """

    def __init__(self, configfile):
        Config = configparser.ConfigParser()
        Config.read(configfile)
        self.debug = Config.getboolean('tpm', 'debug')
        self.sendmail = Config.getboolean('mail', 'sendmail')
        self.sendmailhome = Config.getboolean('mail', 'sendmailhome')
        self.sendmailwork = Config.getboolean('mail', 'sendmailwork')
        self.smtpserver = ConfigSectionMap(Config, 'mail')['smtpserver']
        self.smtpport = Config.getint('mail', 'smtpport')
        self.smtpuser = ConfigSectionMap(Config, 'mail')['smtpuser']
        self.smtppassword = ConfigSectionMap(Config, 'mail')['smtppassword']
        self.pushover = Config.getboolean('pushover', 'pushover')
        self.duedelta = ConfigSectionMap(Config, 'tpm')['duedelta']
        self.dueinterval = Config.getint('tpm', 'dueinterval')
        self.encryptmail = Config.getboolean('mail', 'encryptmail')
        self.gnupghome = ConfigSectionMap(Config, 'mail')['gnupghome']
        self.pushovertoken = ConfigSectionMap(Config, 'pushover')['pushovertoken']
        self.pushoveruser = ConfigSectionMap(Config, 'pushover')['pushoveruser']
        self.targetfingerprint = ConfigSectionMap(Config, 'mail')['targetfingerprint']
        self.sourceemail = ConfigSectionMap(Config, 'mail')['sourceemail']
        self.desthomeemail = ConfigSectionMap(Config, 'mail')['desthomeemail']
        self.destworkemail = ConfigSectionMap(Config, 'mail')['destworkemail']
        self.reviewpath = ConfigSectionMap(Config, 'review')['reviewpath']
        self.reviewagenda = Config.getboolean('review', 'reviewagenda')
        self.reviewprojects = Config.getboolean('review', 'reviewprojects')
        self.reviewcustomers = Config.getboolean('review', 'reviewcustomers')
        self.reviewwaiting = Config.getboolean('review', 'reviewwaiting')
        self.reviewmaybe = Config.getboolean('review', 'reviewmaybe')
        self.reviewoutputpdf = Config.getboolean('review', 'outputpdf')
        self.reviewoutputhtml = Config.getboolean('review', 'outputhtml')
        self.reviewoutputmd = Config.getboolean('review', 'outputmd')
        self.reviewhome = Config.getboolean('review', 'reviewhome')
        self.reviewwork = Config.getboolean('review', 'reviewwork')
        self.pushoverhome = Config.getboolean('pushover', 'pushoverhome')
        self.pushoverwork = Config.getboolean('pushover', 'pushoverwork')


def ConfigSectionMap(Config, section):
    """"helper function for parsing the config file

    :param Config: the name of the configuration file
    :param section: what value from the config file is required
    :returns: the relevant value in the config file
    """

    dict1 = {}
    options = Config.options(section)
    for option in options:
        try:
            dict1[option] = Config.get(section, option)
            if dict1[option] == -1:
                print('skip: {0}'.format(option))
        except:
            print('exception on {0}!'.format(option))
            dict1[option] = None
    return dict1


def printDebugOutput(con, prepend):
    """standardized debug output generator - prints tasks to stdout

    :param con: the database connection
    :param prepend: a string to be prepended to the debug output
    """

    try:
        cursel = con.cursor()
        cursel.execute("SELECT prio, startdate, project, taskline, done, repeat,\
            repeatinterval, duedate, duesoon, overdue, maybe FROM tasks")
        for row in cursel:
            print("{0}: {1} | {2} | {3} | {4} | {5} | {6} | {7} | {8} | {9} | {10} | {11}".format(
                prepend, row[0], row[1], row[2], row[3],
                row[4], row[5], row[6], row[7], row[8], row[9], row[10]))
        con.commit()
    except sqlite3.Error as e:
        sys.exit("printDebugOutput - An error occurred: {0}".format(e.args[0]))


def parseInputTask(line, myproject, con, configfile):
    """adds a new task to the database

    :param line: the content of the task
    :param project: the project section of the task
    :param con: the datbase connection
    :param configfile: the tpm config file
    :returns: taskid of the new task in the database
    """

    cur = con.cursor()
    sett = settings(configfile)
    project = myproject
    done = False
    repeat = False
    repeatinterval = '-'
    duedate = '2999-12-31'
    duesoon = False
    overdue = False
    maybe = False

    if '@done' in line:
        done = True
    if '@maybe' in line:
        maybe = True
    if '@repeat' in line:
        repeat = True
        repeatinterval = re.search(r'\@repeat\((.*?)\)', line).group(1)
    if '@due' in line:
        duedate = re.search(r'\@due\((.*?)\)', line).group(1)
        duealert = datetime.datetime.date(dateutil.parser.parse(duedate)) \
            - datetime.timedelta(**{sett.duedelta: sett.dueinterval})
        if duealert <= TODAY \
                <= datetime.datetime.date(dateutil.parser.parse(duedate)):
            duesoon = True
        if datetime.datetime.date(dateutil.parser.parse(duedate)) < TODAY:
            overdue = True

    if '@prio' not in line or '@start' not in line:
        project = 'Error'
    if '@prio' in line:
        priotag = re.search(r'\@prio\((.*?)\)', line).group(1)
        if priotag == 'high':
            priotag = 1
        elif priotag == 'medium':
            priotag = 2
        elif priotag == 'low':
            priotag = 3
    else:
        priotag = None
    if '@start' in line:
        starttag = re.search(r'\@start\((.*?)\)', line).group(1)
    else:
        starttag = None
    if '@repeat' in line:
        if '@prio' not in line or '@start' not in line or '@repeat' not in line or not\
                    (('@work' not in line and '@home' in line) or (('@work' in line and
                    '@home' not in line))):
            project = 'Error'
    # remove muiple spaces, not the leading tabs
    #line = ' '.join(line.split('\s'))
    line = re.sub(' +', ' ', line)
    try:
        cur.execute("insert into tasks (prio, startdate, project, taskline, done,\
            repeat, repeatinterval, duedate, duesoon, overdue, maybe) values\
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (priotag, starttag, project, line.strip('\n'), done, repeat,
            repeatinterval, duedate, duesoon, overdue, maybe))
    except sqlite3.Error as e:
        sys.exit("parseInputTask - An error occurred: {0}".format(e.args[0]))
    con.commit()
    return cur.lastrowid


def parseInputNote(line, taskid, con):
    """adds a new note to the database; this note requires a valid parent (task)

    :param line: the note field
    :param taskid: the primary key of the parent task
    :param con: the database connections
    """
    # ! todo: entfernen des CRLF am Ende der zeile

    cur = con.cursor()
    try:
        cur.execute("insert into notes (taskid, noteline) values\
            (?, ?)", (taskid, line.strip('\n')))
        con.commit()
    except sqlite3.Error as e:
        sys.exit("parseInputNote - An error occurred: {0}".format(e.args[0]))


def parseInput(tpfile, con, configfile):
    """parses the taskpaper file and populates the database with the content

    :param tpfile: the path to the taskpaper file
    :param con: the database connection
    :param configfile: the config file for tpm
    """

    try:
        with open(tpfile, 'rb') as f:
            tplines = f.readlines()
        project = ''
        taskid = ''

        for line in tplines:
            line = line.decode("utf-8")
            if not line.strip():
                continue
            if line.strip() == '-':
                continue
            if ':\n' in line:
                # Project
                project = line.strip()[:-1]
                continue
            elif re.match("\t*-.*", line):
                # is Task
                taskid = parseInputTask(line, project, con, configfile)
            else:
                # is Note
                if taskid == '':
                    # we currently only support notes which are associated to tasks
                    continue
                parseInputNote(line, taskid, con)
        f.close()
    except Exception as exc:
        sys.exit("parsing input file to db failed; {0}".format(exc))


def removeTags(con):
    """remove overdue and duesoon tags

    :param con: the database connection
    """

    try:
        cursel = con.cursor()
        curup = con.cursor()
        cursel.execute("SELECT taskid, taskline FROM tasks where overdue = 1 or duesoon = 1")
        for row in cursel:
                taskstring = removeTaskParts(row[1], '@overdue @duesoon')
                curup.execute("UPDATE tasks SET taskline=? WHERE taskid=?",
                             (taskstring, row[0]))
        con.commit()
    except sqlite3.Error as e:
        sys.exit("removeTags - An error occurred: {0}".format(e.args[0]))


def setTags(con):
    """set overdue and duesoon tags

    :param con: the database connection
    """

    try:
        cursel = con.cursor()
        curup = con.cursor()
        cursel.execute("SELECT taskid, taskline FROM tasks where overdue = 1")
        for row in cursel:
            curup.execute("UPDATE tasks SET taskline=? WHERE taskid=?",
                         ('{0} @overdue'.format(row[1]), row[0]))
        cursel.execute("SELECT taskid, taskline FROM tasks where duesoon = 1")
        for row in cursel:
            curup.execute("UPDATE tasks SET taskline=? WHERE taskid=?",
                         ('{0} @duesoon'.format(row[1]), row[0]))
        con.commit()
    except sqlite3.Error as e:
        sys.exit("setTags - An error occurred: {0}".format(e.args[0]))


def archiveDone(con):
    """check @done and mark for later move to archive

    :param con: the database connection
    """

    try:
        cursel = con.cursor()
        curup = con.cursor()
        cursel.execute("SELECT taskid, taskline, project FROM tasks where done = 1")
        for row in cursel:
            taskstring = removeTaskParts(row[1], '@done')
            newtask = '{0} @project({1}) @done({2})'.format(taskstring, row[2], DAYBEFORE)
            curup.execute("UPDATE tasks SET taskline=?, project=? WHERE taskid=?",
                         (newtask, 'Archive', row[0]))
        con.commit()
    except sqlite3.Error as e:
        sys.exit("archiveDone - An error occurred: {0}".format(e.args[0]))


def archiveMaybe(con):
    """check @maybe and mark for later move to maybe file

    :param con: the database connection"""

    try:
        cursel = con.cursor()
        curup = con.cursor()
        cursel.execute("SELECT taskid, taskline, project FROM tasks where maybe = 1")
        for row in cursel:
            taskstring = removeTaskParts(row[1], '@maybe @start @due @prio @project')
            newtask = '{0} @project({1})'.format(taskstring, row[2])
            curup.execute("UPDATE tasks SET taskline=?, project=? WHERE taskid=?",
                         (newtask, 'Maybe', row[0]))
        con.commit()
    except sqlite3.Error as e:
        sys.exit("archiveMaybe - An error occurred: {0}".format(e.args[0]))


def setNoteTag(con):
    """set a note tag if task has one or more notes associated

    :param con: the database connection"""

    try:
        cursel = con.cursor()
        cursel2 = con.cursor()
        curup = con.cursor()
        cursel.execute("SELECT taskid, taskline FROM tasks")
        for row in cursel:
            cursel2.execute("SELECT count(*) FROM notes where taskid=?", (row[0],))
            mycount = cursel2.fetchone()[0]
            if mycount != 0:
                if '@note' not in row[1]:
                    taskstring = '{0} {1}'.format(row[1], '@note')
                    curup.execute("UPDATE tasks SET taskline=? WHERE taskid=?",
                                 (taskstring, row[0]))
        con.commit()
    except sqlite3.Error as e:
        sys.exit("setNoteTag - An error occurred: {0}".format(e.args[0]))


def setRepeat(con):
    """check repeat statements; instantiate new tasks if startdate + repeat interval = today

    :param con: the database connection"""

    try:
        cursel = con.cursor()
        curin = con.cursor()
        curup = con.cursor()
        cursel.execute("SELECT repeatinterval, startdate, taskline,\
            prio, duedate, taskid FROM tasks where repeat = 1")
        for row in cursel:
            delta = ''
            intervalnumber = re.search(r'(\d+)[dwm]', row[0]).group(1)
            typeofinterval = re.search(r'\d+([dwm])', row[0]).group(1)
            intnum = int(intervalnumber)
            if 'd' in typeofinterval:
                delta = 'days'
            if 'w' in typeofinterval:
                delta = 'weeks'
            if 'm' in typeofinterval:
                delta = 'month'
            if delta == 'days' or delta == 'weeks':
                newstartdate = \
                    datetime.datetime.date(dateutil.parser.parse(row[1])) \
                    + datetime.timedelta(**{delta: intnum})
            if delta == 'month':
                newstartdate = \
                    datetime.datetime.date(dateutil.parser.parse(row[1])) \
                    + dateutil.relativedelta.relativedelta(months=intnum)

            # instantiate anything which is older or equal than today
            if newstartdate <= TODAY:
                if '@home' in row[2]:
                    projecttag = 'home'
                if '@work' in row[2]:
                    projecttag = 'work'

                # get the relevant information from the task description
                taskstring = removeTaskParts(row[2], '@repeat @home @work @start')
                taskstring = '{0} @start({1})'.format(taskstring, newstartdate)

                # ! create new instance of repeat task
                try:
                    # ! todo: repeatinterval should be NULL, not '-'
                    curin.execute("insert into tasks (prio, startdate, project, taskline, done,\
                        repeat, repeatinterval, duedate, duesoon, overdue, maybe) values\
                        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (row[3], str(newstartdate), projecttag, taskstring, 0, 0,
                        '-', row[4], 0, 0, 0))
                except sqlite3.Error as e:
                    sys.exit("setRepeat - An error occurred: {0}".format(e.args[0]))

                # remove old start-date in taskstring; add newstartdate as start date instead
                taskstring = removeTaskParts(row[2], '@start')
                taskstring = '{0} @start({1})'.format(taskstring, newstartdate)

                try:
                    # prepare modified entry for repeat-task
                    curup.execute("UPDATE tasks SET taskline=? WHERE taskid=?",
                                 (taskstring, row[5]))
                except sqlite3.Error as e:
                    sys.exit("setRepeat - An error occurred: {0}".format(e.args[0]))
        con.commit()
    except sqlite3.Error as e:
        sys.exit("setRepeat - An error occurred: {0}".format(e.args[0]))


def printGroup(con, destination):
    """helper function for printDebug - does the actual debug printing

    :param con: the database communication
    :param destination: what project ('home', 'work' ...) to print
    :returns: result as text string
    """

    mytxt = ''
    cursel = con.cursor()
    cursel2 = con.cursor()
    try:
        cursel.execute("SELECT taskline, project, prio, startdate, taskid FROM tasks\
            where project = ? ORDER BY prio asc, startdate desc", (destination,))
        for row in cursel:
            mytxt = '{0}{1}\n'.format(mytxt, row[0])
            cursel2.execute("SELECT noteline FROM notes where taskid=?", (row[4],))
            for rownote in cursel2:
                mytxt = '{0}{1}\n'.format(mytxt, rownote[0])
    except sqlite3.Error as e:
        sys.exit("printDebugGroup - An error occurred: {0}".format(e.args[0]))
    return mytxt


def printDebug(con):
    """writes tasks and notes to stdout; used if debug=True instead of actually writing to output file

    :param con: the database connection
    """

    mytxt = 'work:\n'
    mytxt = '{0}{1}'.format(mytxt, printGroup(con, 'work'))
    mytxt = '{0}\nhome:\n'.format(mytxt)
    mytxt = '{0}{1}'.format(mytxt, printGroup(con, 'home'))
    mytxt = '{0}\nRepeat:\n'.format(mytxt)
    mytxt = '{0}{1}'.format(mytxt, printGroup(con, 'Repeat'))
    mytxt = '{0}\nINBOX:\n'.format(mytxt)
    mytxt = '{0}{1}'.format(mytxt, printGroup(con, 'INBOX'))
    mytxt = '{0}\nArchive:\n'.format(mytxt)
    mytxt = '{0}{1}'.format(mytxt, printGroup(con, 'Archive'))
    mytxt = '{0}\nError:\n'.format(mytxt)
    mytxt = '{0}{1}'.format(mytxt, printGroup(con, 'Error'))
    mytxt = '{0}\nMaybe:\n'.format(mytxt)
    mytxt = '{0}{1}'.format(mytxt, printGroup(con, 'Maybe'))
    mytxt = mytxt.encode("utf-8")
    print(mytxt)

def createOutFile(con):
    """prepare the text for the different output files

    :param con: the database connection
    :returns: the text for the new taskpaper file, archive file and maybe file
    """

    mytxt = 'work:\n'
    mytxt = '{0}{1}'.format(mytxt, printGroup(con, 'work'))
    mytxt = '{0}\nhome:\n'.format(mytxt)
    mytxt = '{0}{1}'.format(mytxt, printGroup(con, 'home'))
    mytxt = '{0}\nRepeat:\n'.format(mytxt)
    mytxt = '{0}{1}'.format(mytxt, printGroup(con, 'Repeat'))
    mytxt = '{0}\nError:\n'.format(mytxt)
    mytxt = '{0}{1}'.format(mytxt, printGroup(con, 'Error'))
    mytxt = '{0}\nINBOX:\n'.format(mytxt)
    mytxt = '{0}{1}'.format(mytxt, printGroup(con, 'INBOX'))

    mytxtdone = printGroup(con, 'Archive')
    mytxtmaybe = printGroup(con, 'Maybe')

    return (mytxt, mytxtdone, mytxtmaybe)


def createTaskListMaybe(filename):
    """parses maybe file and generates content as text string

    :param filename: the filename of the maybe file
    :param destination: run for 'work' or 'home' tasks?
    :returns: two text string with content of maybe file (home/work)
    """

    with open(filename, 'rb') as f:
        lines = f.readlines()
    mytxthome = ''
    mytxtwork = ''
    for line in lines:
        line = line.decode("utf-8")
        if '@project(home)' in line:
            taskstring = removeTaskParts(line.strip('\n'), '@start @prio @project @customer @waiting')
            mytxthome = '{0}\n{1}'.format(mytxthome, taskstring)
        elif 'project(work)' in line:
            taskstring = removeTaskParts(line.strip('\n'), '@start @prio @project @customer @waiting')
            mytxtwork = '{0}\n{1}'.format(mytxtwork, taskstring)
    f.close()
    if mytxthome != '':
        mytxthome = '{0}\n\n{1}\n'.format('## Maybe list:', mytxthome)
    else:
        mytxthome = ''
    if mytxtwork != '':
        mytxtwork = '{0}\n\n{1}\n'.format('## Maybe list:', mytxtwork)
    else:
        mytxtwork = ''

    return (mytxthome, mytxtwork)


def createTaskListHigh(con, destination):
    """prepares a list of tasks with @prio(high)

    :param con: the database connection
    :param destination: run for 'work' or 'home' tasks?
    :returns: the result tasks as text string
    """

    try:
        mytxt = ''
        cursel = con.cursor()
        cursel.execute("SELECT taskline, project, prio, startdate FROM tasks\
            where project = ? and prio = 1 and \
            startdate <= date( julianday(date('now'))) and done = 0 ORDER BY prio asc,\
            startdate desc ", (destination,))
        for row in cursel:
            taskstring = removeTaskParts(row[0], '@start @prio')
            mytxt = '{0}{1}\n'.format(mytxt, taskstring)
        if mytxt == '':
            return mytxt
        else:
            return '{0}{1}'.format('## Open tasks with prio high:\n', mytxt)
    except sqlite3.Error as e:
        sys.exit("createTaskListHigh - An error occurred: {0}".format(e.args[0]))


def createTaskListOverdue(con, destination):
    """prepares a list of tasks with @overdue

    :param con: the database connection
    :param destination: run for 'work' or 'home' tasks?
    :returns: the result tasks as text string
    """

    try:
        mytxt = ''
        cursel = con.cursor()
        cursel.execute("SELECT taskline, project, prio, startdate FROM tasks\
            where project = ? and overdue = 1 and \
            done = 0 ORDER BY prio asc, startdate desc ", (destination,))
        for row in cursel:
            taskstring = removeTaskParts(row[0], '@start @prio')
            mytxt = '{0}{1}\n'.format(mytxt, taskstring)
        if mytxt == '':
            return mytxt
        else:
            return '{0}{1}'.format('## Open tasks - overdue:\n', mytxt)
    except sqlite3.Error as e:
        sys.exit("createTaskListOverdue - An error occurred: {0}".format(e.args[0]))


def markdown2html(mytext):
    """convert markdown text to html output

    :param text: input text
    :returns: the html output
    """

    TEMPLATE = """<!DOCTYPE html>
    <html>
    <head>
        <link href="http://netdna.bootstrapcdn.com/twitter-bootstrap/2.3.0/css/bootstrap-combined.min.css" rel="stylesheet">
        <style>
            body {
                font-family: sans-serif;
            }
            code, pre {
                font-family: monospace;
            }
            h1 code,
            h2 code,
            h3 code,
            h4 code,
            h5 code,
            h6 code {
                font-size: inherit;
            }
        </style>
    </head>
    <body>
    <div class="container">
    {{content}}
    </div>
    </body>
    </html>
    """

    extensions = ['extra', 'smartypants']
    html = markdown.markdown(mytext, extensions=extensions, output_format='html5')
    doc = jinja2.Template(TEMPLATE).render(content=html)
    return doc


def html2pdf(html, outfile):
    """convert html input to pdf output

    :param html: the html input
    :param outfile: the output pdf file
    """

    logger = logging.getLogger('weasyprint')
    logger.handlers = []
    logger.addHandler(logging.FileHandler('/tmp/weasyprint.log'))
    mydoc = weasyprint.HTML(string=html)
    mydoc.write_pdf(target=outfile)


def sendPushover(content, configfile):
    """send text to pushover service via http-request

    :param content: the text for the poushover message
    :param configfile: the tpm config file
    """

    sett = settings(configfile)
    content = content.encode("utf-8")
    try:
        #conn = httplib.HTTPSConnection("api.pushover.net:443")
        conn = http_client.HTTPSConnection("api.pushover.net:443")
        conn.request("POST", "/1/messages.json",
            urllib.urlencode({
                "token": sett.pushovertoken,
                "user": sett.pushoveruser,
                "message": content,
            }), {"Content-type": "application/x-www-form-urlencoded"})
        conn.getresponse()
    except Exception as exc:
        sys.exit("sending pushover message failed; {0}".format(exc))


def sendMail(content, subject, sender, receiver, text_subtype, encrypted, configfile):
    """sends email directly via starttls connection to smtp server

    :param content: the text messages for the mail
    :param subject: the subject of the mail
    :param sender: the sender email address
    :param receiver: the receiver email address
    :param text_subtype: the MIME type for the email
    :param encrypted: boolean - encrypt the mail with gpg?
    :param configfile: the tpm config file
    """

    sett = settings(configfile)
    content = content.encode("utf-8")
    try:
        if encrypted is False:
            msg = email.mime.text.MIMEText(content, text_subtype)
        elif encrypted is True:
            if sett.encryptmail:
                gpg = gnupg.GPG(gnupghome=sett.gnupghome)
                gpg.encoding = 'utf-8'
                contentenc = gpg.encrypt(content, sett.targetfingerprint, always_trust=True)
                msg = email.mime.text.MIMEText(str(contentenc), text_subtype)
            else:
                raise "encryption required, but not set in config file"
        msg['Subject'] = subject
        msg['From'] = sender

        conn = smtplib.SMTP(sett.smtpserver, sett.smtpport)
        conn.starttls()
        if sett.debug:
            conn.set_debuglevel(True)
        else:
            conn.set_debuglevel(False)
        conn.login(sett.smtpuser, sett.smtppassword)
        try:
            conn.sendmail(sender, receiver, msg.as_string())
        finally:
            conn.close()

    except Exception as exc:
        sys.exit("sending email failed; {0}".format(exc))


def createMail(con, destination, configfile):
    """create text for email output

    :param con: the database connection
    :param destination: either 'home' or 'work'
    :param configfile: the tpm config file
    """

    sett = settings(configfile)
    if sett.sendmail:
        try:
            cursel = con.cursor()

            mytxtasc = '# Tasks for Today\n'
            mytxtasc = '{0}\n## Overdue tasks\n'.format(mytxtasc)

            # Overdue
            cursel.execute("SELECT taskline, project, prio, startdate, duedate FROM tasks\
                where project = ? and overdue = 1 and done = 0 ORDER BY prio asc,\
                startdate desc ", (destination,))
            for row in cursel:
                taskstring = removeTaskParts(row[0], '@')
                taskstring = '{0} @due({1})'.format(taskstring, row[4])
                mytxtasc = '{0}{1}\n'.format(mytxtasc, taskstring.strip())
            mytxtasc = '{0}\n## Due soon tasks\n'.format(mytxtasc)

            # Due soon
            cursel.execute("SELECT taskline, project, prio, startdate, duedate FROM tasks\
                where project = ? and duesoon = 1 and done = 0 ORDER BY prio asc,\
                startdate desc ", (destination,))
            for row in cursel:
                taskstring = removeTaskParts(row[0], '@')
                taskstring = '{0} @due({1})'.format(taskstring, row[4])
                mytxtasc = '{0}{1}\n'.format(mytxtasc, taskstring.strip())

            mytxtasc = '{0}\n## High priority tasks ##\n'.format(mytxtasc)

            # All other high prio tasks
            cursel.execute("SELECT taskline, project, prio, startdate, duedate FROM tasks\
                where project = ? and prio = 1 and duesoon = 0 and overdue = 0 and \
                startdate <= date( julianday(date('now'))) and done = 0 ORDER BY prio asc,\
                startdate desc ", (destination,))
            for row in cursel:
                taskstring = removeTaskParts(row[0], '@start @prio')
                if row[4] != '2999-12-31':
                    taskstring = '{0} @due({1})'.format(taskstring, row[4])
                mytxtasc = '{0}{1}\n'.format(mytxtasc, taskstring.strip())

        except Exception as exc:
            sys.exit("creating email failed; {0}".format(exc))
        return mytxtasc


def createUniqueList(con, element, group):
    """creates a unique list of tag contents for a given group
     e.g. a unique list of all customers (derived from @customer)

     :param con: the database connection
     :param element: the tag to parse the unique list from
     :param group: search in which group ('work' or 'home')
     :returns: a list of unique names from `element´
     """

    mylist = []
    try:
        cursel = con.cursor()
        cursel.execute("SELECT taskline, project FROM tasks\
            where project = ? ORDER BY prio asc, startdate desc ", (group,))
        for row in cursel:
            if '@{0}'.format(element) in row[0]:
                mycontent = re.search(r'\@' + element + '\((.*?)\)', row[0]).group(1)
                if mycontent not in mylist:
                    mylist.append(mycontent)
    except sqlite3.Error as e:
        sys.exit("createUniqueList - An error occurred: {0}".format(e.args[0]))
    return mylist


def createTaskList(con, element, headline, mylist, group):
    """create a list of tasks for specified content

    :param con: the database connection
    :param element: the tag to use
    :param headline: the headline to use for the output
    :param mylist: a list of unique names
    :param group: search in which group ('work' or 'home')
    :returns: text string with task list
    """

    mytasks = '\n\n## {0}\n'.format(headline)
    for listelement in mylist:
        mytasks = '{0}\n\n### {1}\n'.format(mytasks, listelement)
        try:
            cursel = con.cursor()
            cursel.execute("SELECT taskline, project FROM tasks\
                where project = ? ORDER BY prio asc, startdate desc ", (group,))
            for row in cursel:
                if '@{0}'.format(element) in row[0]:
                    if re.search(r'\@' + element + '\((.*?)\)', row[0]).group(1) == listelement:
                        taskstring = removeTaskParts(row[0], '@start @prio @project @customer @waiting')
                        mytasks = '{0}\n{1}'.format(mytasks, taskstring)
        except sqlite3.Error as e:
            sys.exit("createTaskList - An error occurred: {0}".format(e.args[0]))
    return mytasks


def myFile(mytext, filename, mode):
    """helper function for file operations; append and write

    :param mytext: text for file write
    :param filename: the target filename
    :param mode: 'w' for write new and 'a' for append existing
    """

    try:
        mytext = mytext.encode("utf-8")
        outfile = open(filename, mode)
        outfile.write(mytext)
        outfile.close()
    except Exception as exc:
        sys.exit("file operation failed; {0}".format(exc))


def main():
    (inputfile, configfile, modus) = parseArgs(sys.argv[1:])
    mycon = initDB()
    sett = settings(configfile)
    parseInput(inputfile, mycon, configfile)

    if modus == "daily":
        removeTags(mycon)
        setTags(mycon)
        archiveDone(mycon)
        archiveMaybe(mycon)
        setNoteTag(mycon)
        setRepeat(mycon)
        if sett.debug:
            printDebug(mycon)
        else:
            (mytxt, mytxtdone, mytxtmaybe) = createOutFile(mycon)
            shutil.move(inputfile, '{0}backup/todo_{1}.txt'.format(inputfile[:-8], TODAY))
            myFile(mytxt, inputfile, 'w')
            myFile(mytxtdone, '{0}archive.txt'.format(inputfile[:-8]), 'a')
            myFile(mytxtmaybe, '{0}maybe.txt'.format(inputfile[:-8]), 'a')
        if sett.sendmail:
            source = sett.sourceemail
            desthome = sett.desthomeemail
            destwork = sett.destworkemail
            if sett.sendmailhome:
                mytxtasc = createMail(mycon, 'home', configfile)
                myhtml = markdown2html(mytxtasc)
                # ! todo: add to config for user to choose if 'work' or 'home' shall be encrypted
                sendMail(myhtml, 'Taskpaper daily overview', source,
                         desthome, 'html', False, configfile)
            if sett.sendmailwork:
                mytxtasc = createMail(mycon, 'work', configfile)
                sendMail(mytxtasc, 'Taskpaper daily overview', source,
                         destwork, 'text', True, configfile)
        if sett.pushover:
            if sett.pushoverhome:
                pushovertxt = createTaskListHigh(mycon, 'home')
                pushovertxt = '{0}\n{1}'.format(pushovertxt, createTaskListOverdue(mycon, 'home'))
                # pushover limits messages sizes to 512 characters
                if len(pushovertxt) > 512:
                        pushovertxt = pushovertxt[:512]
                sendPushover(pushovertxt, configfile)
            if sett.pushoverwork:
                pushovertxt = createTaskListHigh(mycon, 'work')
                pushovertxt = '{0}\n{1}'.format(pushovertxt, createTaskListOverdue(mycon, 'work'))
                # pushover limits messages sizes to 512 characters
                if len(pushovertxt) > 512:
                        pushovertxt = pushovertxt[:512]
                sendPushover(pushovertxt, configfile)
    elif modus == "review":
        reviewgroup = []
        if sett.reviewhome:
            reviewgroup.append('home')
        if sett.reviewwork:
            reviewgroup.append('work')
        for group in reviewgroup:
            reviewfile = '{0}/Review_{1}_{2}'.format(sett.reviewpath, group, TODAY)
            reviewtext = '# Review\n\n'
            reviewtext = '{0}\n{1}'.format(reviewtext, createTaskListHigh(mycon, group))
            reviewtext = '{0}\n{1}'.format(reviewtext, createTaskListOverdue(mycon, group))
            if sett.reviewagenda:
                agendalist = createUniqueList(mycon, 'agenda', group)
                if len(agendalist) > 0:
                    agendatasks = createTaskList(mycon, 'agenda', 'Agenda', agendalist, group)
                    reviewtext = '{0}\n{1}'.format(reviewtext, agendatasks)
            if sett.reviewwaiting:
                waitinglist = createUniqueList(mycon, 'waiting', group)
                if len(waitinglist) > 0:
                    waitingtasks = createTaskList(mycon, 'waiting',
                                              'Waiting For', waitinglist, group)
                    reviewtext = '{0}\n{1}'.format(reviewtext, waitingtasks)
            if sett.reviewcustomers:
                customerlist = createUniqueList(mycon, 'customer', group)
                if len(customerlist) > 0:
                    customertasks = createTaskList(mycon, 'customer',
                                               'Customers', customerlist, group)
                    reviewtext = '{0}\n{1}'.format(reviewtext, customertasks)
            if sett.reviewprojects:
                projectlist = createUniqueList(mycon, 'project', group)
                if len(projectlist) > 0:
                    projecttasks = createTaskList(mycon, 'project', 'Projects', projectlist, group)
                    reviewtext = '{0}\n{1}'.format(reviewtext, projecttasks)
            if sett.reviewmaybe:
                maybetxt = ''
                (maybehometxt, maybeworktxt) = createTaskListMaybe('{0}maybe.txt'.format(inputfile[:-8]))
                if group == 'home':
                    maybetxt = maybehometxt
                elif group == 'work':
                    maybetxt = maybeworktxt
                reviewtext = '{0}\n{1}'.format(reviewtext, maybetxt)

            html = markdown2html(reviewtext)

            if sett.reviewoutputmd:
                myFile(reviewtext, '{0}.md'.format(reviewfile), 'wb')
            if sett.reviewoutputhtml:
                myFile(html, '{0}.html'.format(reviewfile), 'wb')
            if sett.reviewoutputpdf:
                html2pdf(html, '{0}.pdf'.format(reviewfile))
    else:
        print("modus error")
        sys.exit()


if __name__ == '__main__':
    sys.exit(main())
