#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TaskPaperManager
originally based on a small script for printing a task summary from K. Marchand
now completely re-written and modified for my own requirements

License: GPL v3 (for details see LICENSE file)
"""

from __future__ import (absolute_import, division, print_function, unicode_literals)

from datetime import datetime, timedelta
from collections import namedtuple
from operator import itemgetter
from dateutil import parser
from dateutil.relativedelta import relativedelta
import markdown2
import xhtml2pdf.pisa as pisa
import cStringIO
import ConfigParser
import getopt
import shutil
import sys
import re
import sqlite3


"""Data structure
prio: priority of the task - high, medium or low; mapped to 1, 2 or 3
startdate: when will the task be visible - format: yyyy-mm-dd
project: with which project is the task associated
taskline: the actual task line
done: is it done?; based on @done tag; boolean
repeat: only for tasks in the project "repeat"; boolean
repeatinterval: the repeat inteval is given by a number followed by an interval type; e.g.
    2w = 2 weeks
    3d = 3 days
    1m = 1 month
duedate: same format as startdate
duesoon: boolean; true if today is duedate minus DUEDELTA in DUEINTERVAL (constants) or less
overdue: boolean; true if today is after duedate"""


# create in-memory db instance
conn = sqlite3.connect(':memory:')
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
cur.execute('''CREATE TABLE comments(
    commentid INTEGER PRIMARY KEY,
    taskid INTEGER,
    commentline text,
    FOREIGN KEY(taskid) REFERENCES tasks(taskid)
    )''')

Flagged = Flaggednew = Flaggedarchive = Flaggedmaybe = namedtuple('Flagged', [
    'prio',
    'startdate',
    'project',
    'taskline',
    'done',
    'repeat',
    'repeatinterval',
    'duedate',
    'duesoon',
    'overdue',
    'maybe',
])

TODAY = datetime.date(datetime.now())
DAYBEFORE = TODAY - timedelta(days=1)

# global vars
DEBUG = SENDMAIL = SMTPSERVER = SMTPPORT = SMTPUSER = SMTPPASSWORD\
    = PUSHOVER = DUEDELTA = DUEINTERVAL = ENCRYPTMAIL = GNUPGHOME\
    = PUSHOVERTOKEN = PUSHOVERUSER = TARGETFINGERPRINT = SOURCEEMAIL\
    = DESTHOMEEMAIL = DESTWORKEMAIL = REVIEWPATH\
    = REVIEWAGENDA = REVIEWPROJECTS = REVIEWCUSTOMERS\
    = REVIEWWAITING = REVIEWOUTPUTPDF = REVIEWOUTPUTHTML\
    = REVIEWOUTPUTMD = REVIEWHOME = REVIEWWORK\
    = SENDMAILHOME = SENDMAILWORK = PUSHOVERHOME = PUSHOVERWORK = ''


def usage():
    print('tpm.py -i <inputfile> -c <configfile> -m <mode:daily|review>')
    """
    Prints usage information.
    """


def parseArgs(argv):
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


# filter unnecessary spaces
def filterWhitespaces(flaglist):
    flaglistnew = []
    for task in flaglist:
        taskstring = ' '.join(task.taskline.split())
        flaglistnew.append(Flaggednew(
            task.prio,
            task.startdate,
            task.project,
            taskstring,
            task.done,
            task.repeat,
            task.repeatinterval,
            task.duedate,
            task.duesoon,
            task.overdue,
            task.maybe
        ))
    return flaglistnew


# remove elements from a taskpaper string
def removeTaskParts(instring, removelist):
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


def parseConfig(configfile):
    # sets the config parameters as global variables
    # tpm.cfg config file required - for details see README.md
    # set correct path if not in same directory as script
    Config = ConfigParser.ConfigParser()
    Config.read(configfile)

    global DEBUG
    global SENDMAIL
    global SENDMAILHOME
    global SENDMAILWORK
    global SMTPSERVER
    global SMTPPORT
    global SMTPUSER
    global SMTPPASSWORD
    global PUSHOVER
    global DUEDELTA
    global DUEINTERVAL
    global ENCRYPTMAIL
    global GNUPGHOME
    global PUSHOVERTOKEN
    global PUSHOVERUSER
    global TARGETFINGERPRINT
    global SOURCEEMAIL
    global DESTHOMEEMAIL
    global DESTWORKEMAIL
    global REVIEWPATH
    global REVIEWAGENDA
    global REVIEWPROJECTS
    global REVIEWCUSTOMERS
    global REVIEWWAITING
    global REVIEWOUTPUTPDF
    global REVIEWOUTPUTHTML
    global REVIEWOUTPUTMD
    global REVIEWHOME
    global REVIEWWORK
    global PUSHOVERHOME
    global PUSHOVERWORK

    DEBUG = Config.getboolean('tpm', 'debug')
    SENDMAIL = Config.getboolean('mail', 'sendmail')
    SENDMAILWORK = Config.getboolean('mail', 'sendmailwork')
    SENDMAILHOME = Config.getboolean('mail', 'sendmailhome')
    SMTPSERVER = ConfigSectionMap(Config, 'mail')['smtpserver']
    SMTPPORT = Config.getint('mail', 'smtpport')
    SMTPUSER = ConfigSectionMap(Config, 'mail')['smtpuser']
    SMTPPASSWORD = ConfigSectionMap(Config, 'mail')['smtppassword']
    PUSHOVER = Config.getboolean('pushover', 'pushover')
    PUSHOVERHOME = Config.getboolean('pushover', 'pushoverhome')
    PUSHOVERWORK = Config.getboolean('pushover', 'pushoverwork')
    DUEDELTA = ConfigSectionMap(Config, 'tpm')['duedelta']
    DUEINTERVAL = Config.getint('tpm', 'dueinterval')
    ENCRYPTMAIL = Config.getboolean('mail', 'encryptmail')
    GNUPGHOME = ConfigSectionMap(Config, 'mail')['gnupghome']
    PUSHOVERTOKEN = ConfigSectionMap(Config, 'pushover')['pushovertoken']
    PUSHOVERUSER = ConfigSectionMap(Config, 'pushover')['pushoveruser']
    TARGETFINGERPRINT = ConfigSectionMap(Config, 'mail')['targetfingerprint']
    SOURCEEMAIL = ConfigSectionMap(Config, 'mail')['sourceemail']
    DESTHOMEEMAIL = ConfigSectionMap(Config, 'mail')['desthomeemail']
    DESTWORKEMAIL = ConfigSectionMap(Config, 'mail')['destworkemail']
    REVIEWPATH = ConfigSectionMap(Config, 'review')['reviewpath']
    REVIEWAGENDA = Config.getboolean('review', 'reviewagenda')
    REVIEWPROJECTS = Config.getboolean('review', 'reviewprojects')
    REVIEWCUSTOMERS = Config.getboolean('review', 'reviewcustomers')
    REVIEWWAITING = Config.getboolean('review', 'reviewwaiting')
    REVIEWOUTPUTPDF = Config.getboolean('review', 'outputpdf')
    REVIEWOUTPUTHTML = Config.getboolean('review', 'outputhtml')
    REVIEWOUTPUTMD = Config.getboolean('review', 'outputmd')
    REVIEWHOME = Config.getboolean('review', 'reviewhome')
    REVIEWWORK = Config.getboolean('review', 'reviewwork')


def ConfigSectionMap(Config, section):
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


def printDebugOutput(flaglist, prepend):
    for task in flaglist:
        print("{0}: {1} | {2} | {3} |  {4} | {5} | {6} | {7} | {8} | {9} | {10}".format(
            prepend, task.prio, task.startdate, task.project, task.taskline,
            task.done, task.repeat, task.repeatinterval,
            task.duesoon, task.overdue, task.maybe))


def parseInputDB(tpfile):
    try:
        with open(tpfile, 'rb') as f:
            tplines = f.readlines()
        errlist = []
        project = ''

        for line in tplines:
            line = line.decode("utf-8")
            try:
                done = False
                repeat = False
                repeatinterval = '-'
                duedate = '2999-12-31'
                duesoon = False
                overdue = False
                maybe = False

                if not line.strip():
                    continue
                if line.strip() == '-':
                    continue
                if ':\n' in line:
                    project = line.strip()[:-1]
                    continue
                if '@done' in line:
                    done = True
                if '@maybe' in line:
                    maybe = True
                if '@repeat' in line:
                    repeat = True
                    repeatinterval = re.search(r'\@repeat\((.*?)\)', line).group(1)
                if '@due' in line:
                    duedate = re.search(r'\@due\((.*?)\)', line).group(1)
                    duealert = datetime.date(parser.parse(duedate)) \
                        - timedelta(**{DUEDELTA: DUEINTERVAL})
                    if duealert <= TODAY \
                            <= datetime.date(parser.parse(duedate)):
                        duesoon = True
                    if datetime.date(parser.parse(duedate)) < TODAY:
                        overdue = True
                if '@start' in line and '@prio' in line:
                    priotag = re.search(r'\@prio\((.*?)\)', line).group(1)
                    if priotag == 'high':
                        priotag = 1
                    elif priotag == 'medium':
                        priotag = 2
                    elif priotag == 'low':
                        priotag = 3
                    starttag = re.search(r'\@start\((.*?)\)', line).group(1)
                    try:
                        cur.execute("insert into tasks (prio, startdate, project, taskline, done,\
                            repeat, repeatinterval, duedate, duesoon, overdue, maybe) values\
                            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            ( priotag, starttag, project, line.strip(), done, repeat,\
                            repeatinterval, duedate, duesoon, overdue, maybe))
                    except sqlite3.Error as e:
                        sys.exit("An error occurred: {0}".format(e.args[0]))
                else:
                    try:
                        cur.execute("insert into tasks (prio, startdate, project, taskline, done,\
                            repeat, repeatinterval, duedate, duesoon, overdue, maybe) values\
                            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            ( NULL, NULL, project, line.strip(), done, repeat,\
                            repeatinterval, duedate, duesoon, overdue, maybe))
                    except sqlite3.Error as e:
                        sys.exit("An error occurred: {0}".format(e.args[0]))
            except Exception as e:
                errlist.append((line, e))
        f.close()
    except Exception as exc:
        sys.exit("parsing input file to db failed; {0}".format(exc))


def parseInput(tpfile):
    try:
        with open(tpfile, 'rb') as f:
            tplines = f.readlines()
        flaglist = []
        errlist = []
        project = ''

        for line in tplines:
            line = line.decode("utf-8")
            try:
                done = False
                repeat = False
                repeatinterval = '-'
                duedate = '2999-12-31'
                duesoon = False
                overdue = False
                maybe = False

                if not line.strip():
                    continue
                if line.strip() == '-':
                    continue
                if ':\n' in line:
                    project = line.strip()[:-1]
                    continue
                if '@done' in line:
                    done = True
                if '@maybe' in line:
                    maybe = True
                if '@repeat' in line:
                    repeat = True
                    repeatinterval = re.search(r'\@repeat\((.*?)\)', line).group(1)
                if '@due' in line:
                    duedate = re.search(r'\@due\((.*?)\)', line).group(1)
                    duealert = datetime.date(parser.parse(duedate)) \
                        - timedelta(**{DUEDELTA: DUEINTERVAL})
                    if duealert <= TODAY \
                            <= datetime.date(parser.parse(duedate)):
                        duesoon = True
                    if datetime.date(parser.parse(duedate)) < TODAY:
                        overdue = True
                if '@start' in line and '@prio' in line:
                    priotag = re.search(r'\@prio\((.*?)\)', line).group(1)
                    if priotag == 'high':
                        priotag = 1
                    elif priotag == 'medium':
                        priotag = 2
                    elif priotag == 'low':
                        priotag = 3
                    starttag = re.search(r'\@start\((.*?)\)', line).group(1)
                    flaglist.append(Flagged(
                        priotag,
                        starttag,
                        project,
                        line.strip(),
                        done,
                        repeat,
                        repeatinterval,
                        duedate,
                        duesoon,
                        overdue,
                        maybe
                    ))
                else:
                    flaglist.append(Flagged(
                        '-',
                        '-',
                        project,
                        line.strip(),
                        done,
                        repeat,
                        repeatinterval,
                        duedate,
                        duesoon,
                        overdue,
                        maybe
                    ))
            except Exception as e:
                errlist.append((line, e))
        f.close()
        return flaglist
    except Exception as exc:
        sys.exit("parsing input file failed; {0}".format(exc))


# remove overdue and duesoon tags
def removeTags(flaglist):
    try:
        flaglistnew = []
        for task in flaglist:
            if '@overdue' in task.taskline or '@duesoon' in task.taskline:
                taskstring = removeTaskParts(task.taskline, '@overdue @duesoon')
                flaglistnew.append(Flaggednew(
                    task.prio,
                    task.startdate,
                    task.project,
                    taskstring,
                    task.done,
                    task.repeat,
                    task.repeatinterval,
                    task.duedate,
                    task.duesoon,
                    task.overdue,
                    task.maybe
                ))
            else:
                flaglistnew.append(Flaggednew(
                    task.prio,
                    task.startdate,
                    task.project,
                    task.taskline,
                    task.done,
                    task.repeat,
                    task.repeatinterval,
                    task.duedate,
                    task.duesoon,
                    task.overdue,
                    task.maybe,
                ))
        return flaglistnew
    except Exception as exc:
        sys.exit("removing tags failed; {0}".format(exc))


# set overdue and duesoon tags
def setTags(flaglist):
    try:
        flaglistnew = []
        for task in flaglist:
            if task.overdue:
                flaglistnew.append(Flaggednew(
                    task.prio,
                    task.startdate,
                    task.project,
                    '{0} @overdue'.format(task.taskline),
                    task.done,
                    task.repeat,
                    task.repeatinterval,
                    task.duedate,
                    task.duesoon,
                    task.overdue,
                    task.maybe,
                ))
            elif task.duesoon:
                flaglistnew.append(Flaggednew(
                    task.prio,
                    task.startdate,
                    task.project,
                    '{0} @duesoon'.format(task.taskline),
                    task.done,
                    task.repeat,
                    task.repeatinterval,
                    task.duedate,
                    task.duesoon,
                    task.overdue,
                    task.maybe,
                ))
            else:
                flaglistnew.append(Flaggednew(
                    task.prio,
                    task.startdate,
                    task.project,
                    task.taskline,
                    task.done,
                    task.repeat,
                    task.repeatinterval,
                    task.duedate,
                    task.duesoon,
                    task.overdue,
                    task.maybe,
                ))
        return flaglistnew
    except Exception as exc:
        sys.exit("setting overdue or duesoon tags failed; {0}".format(exc))


# check @done and move to archive file
def archiveDone(flaglist):
    flaglistnew = []
    flaglistarchive = []
    try:
        for task in flaglist:
            if task.done:
                #if DEBUG:
                #    printDebugOutput(flaglist, 'BeforeDone')
                taskstring = removeTaskParts(task.taskline, '@done')
                newtask = '{0} @project({1}) @done({2})'.format(taskstring, task.project, DAYBEFORE)
                flaglistarchive.append(Flaggedarchive(
                    task.prio,
                    task.startdate,
                    'Archive',
                    newtask,
                    task.done,
                    task.repeat,
                    task.repeatinterval,
                    task.duedate,
                    task.duesoon,
                    task.overdue,
                    task.maybe,
                ))
            else:
                flaglistnew.append(Flaggednew(
                    task.prio,
                    task.startdate,
                    task.project,
                    task.taskline,
                    task.done,
                    task.repeat,
                    task.repeatinterval,
                    task.duedate,
                    task.duesoon,
                    task.overdue,
                    task.maybe,
                ))
        return (flaglistnew, flaglistarchive)
    except Exception as exc:
        sys.exit("archiving of @done failed; {0}".format(exc))


# check @done and move to archive file
def archiveDoneDB():
    flaglistnew = []
    flaglistarchive = []
    try:
        for row in conn.execute('SELECT * FROM tasks where done=1'):
            print('DB: {0}'.format(row))

        for task in flaglist:
            if task.done:
                #if DEBUG:
                #    printDebugOutput(flaglist, 'BeforeDone')
                taskstring = removeTaskParts(task.taskline, '@done')
                newtask = '{0} @project({1}) @done({2})'.format(taskstring, task.project, DAYBEFORE)
                flaglistarchive.append(Flaggedarchive(
                    task.prio,
                    task.startdate,
                    'Archive',
                    newtask,
                    task.done,
                    task.repeat,
                    task.repeatinterval,
                    task.duedate,
                    task.duesoon,
                    task.overdue,
                    task.maybe,
                ))
            else:
                flaglistnew.append(Flaggednew(
                    task.prio,
                    task.startdate,
                    task.project,
                    task.taskline,
                    task.done,
                    task.repeat,
                    task.repeatinterval,
                    task.duedate,
                    task.duesoon,
                    task.overdue,
                    task.maybe,
                ))
        return (flaglistnew, flaglistarchive)
    except Exception as exc:
        sys.exit("archiving of @done failed; {0}".format(exc))


# check @maybe and move to archive file (maybe)
def archiveMaybe(flaglist):
    flaglistnew = []
    flaglistmaybe = []

    for task in flaglist:
        if task.maybe:
            #if DEBUG:
            #    printDebugOutput(flaglist, 'Maybe')
            taskstring = removeTaskParts(task.taskline, '@maybe @start @due @prio @project')
            newtask = '{0} @project({1})'.format(taskstring, task.project)
            flaglistmaybe.append(Flaggedmaybe(
                task.prio,
                task.startdate,
                'Maybe',
                newtask,
                task.done,
                task.repeat,
                task.repeatinterval,
                task.duedate,
                task.duesoon,
                task.overdue,
                task.maybe,
            ))
        else:
            flaglistnew.append(Flaggednew(
                task.prio,
                task.startdate,
                task.project,
                task.taskline,
                task.done,
                task.repeat,
                task.repeatinterval,
                task.duedate,
                task.duesoon,
                task.overdue,
                task.maybe,
            ))
    return (flaglistnew, flaglistmaybe)


# check repeat statements; instantiate new tasks if startdate + repeat interval = today
def setRepeat(flaglist):
    flaglistnew = []

    for task in flaglist:
        if task.project == 'Repeat' and task.repeat:
            delta = ''
            intervalnumber = task.repeatinterval[0]
            typeofinterval = task.repeatinterval[1]
            intnum = int(intervalnumber)
            if 'd' in typeofinterval:
                delta = 'days'
            if 'w' in typeofinterval:
                delta = 'weeks'
            if 'm' in typeofinterval:
                delta = 'month'
            if delta == 'days' or delta == 'weeks':
                newstartdate = \
                    datetime.date(parser.parse(task.startdate)) \
                    + timedelta(**{delta: intnum})
            if delta == 'month':
                newstartdate = \
                    datetime.date(parser.parse(task.startdate)) \
                    + relativedelta(months=intnum)

            # instantiate anything which is older or equal than today
            if newstartdate <= TODAY:
                if '@home' in task.taskline:
                    projecttag = 'home'
                if '@work' in task.taskline:
                    projecttag = 'work'

                # get the relevant information from the task description
                taskstring = removeTaskParts(task.taskline, '@repeat @home @work @start')
                taskstring = '{0} @start({1})'.format(taskstring, newstartdate)
                done = False
                repeat = False
                repeatinterval = '-'

                # create new instance of repeat task

                flaglistnew.append(Flaggednew(
                    task.prio,
                    str(newstartdate),
                    projecttag,
                    taskstring,
                    done,
                    repeat,
                    repeatinterval,
                    task.duedate,
                    task.duesoon,
                    task.overdue,
                    task.maybe,
                ))

                # remove old start-date in taskstring; add newstartdate as start date instead
                taskstring = removeTaskParts(task.taskline, '@start')
                taskstring = '{0} @start({1})'.format(taskstring, newstartdate)

                # prepare modified entry for repeat-task

                flaglistnew.append(Flaggednew(
                    task.prio,
                    task.startdate,
                    task.project,
                    taskstring,
                    task.done,
                    task.repeat,
                    task.repeatinterval,
                    task.duedate,
                    task.duesoon,
                    task.overdue,
                    task.maybe,
                ))
            else:

                # write back repeat tasks with non-matching date
                flaglistnew.append(Flaggednew(
                    task.prio,
                    task.startdate,
                    task.project,
                    task.taskline,
                    task.done,
                    task.repeat,
                    task.repeatinterval,
                    task.duedate,
                    task.duesoon,
                    task.overdue,
                    task.maybe,
                ))
        else:
            flaglistnew.append(Flaggednew(
                task.prio,
                task.startdate,
                task.project,
                task.taskline,
                task.done,
                task.repeat,
                task.repeatinterval,
                task.duedate,
                task.duesoon,
                task.overdue,
                task.maybe,
            ))
    #if DEBUG:
    #    printDebugOutput(flaglist, 'AfterRepeat')
    return flaglistnew


def sortList(flaglist):
    try:
        # sort in following order: project (asc), prio (asc), date (desc)
        flaglist = sorted(flaglist, key=itemgetter(Flagged._fields.index
                ('startdate')), reverse=True)
        flaglist = sorted(flaglist, key=itemgetter(Flagged._fields.index
                ('project'),Flagged._fields.index('prio')))
        return flaglist
    except Exception as exc:
        sys.exit("sorting list failed; {0}".format(exc))


def printOutFileDebug(flaglist, flaglistarchive, flaglistmaybe, tpfile):
    print('work:')
    for task in flaglist:
        if task.project == 'work':
            print('\t{0}'.format(task.taskline))

    print('\nhome:')

    for task in flaglist:
        if task.project == 'home':
            print('\t{0}'.format(task.taskline))

    print('\nRepeat:')

    for task in flaglist:
        if task.project == 'Repeat':
            print('\t{0}'.format(task.taskline))

    print('\nArchive:')

    print('\nINBOX:')

    for task in flaglist:
        if task.project == 'INBOX':
            print('\t{0}'.format(task.taskline))

    print('\nArchive:')

    for task in flaglistarchive:
        if task.project == 'Archive':
            print('\t{0}'.format(task.taskline))
    print('\nMaybe:')

    for task in flaglistmaybe:
        if task.project == 'Maybe':
            print('\t{0}'.format(task.taskline))


def printOutFile(flaglist, flaglistarchive, flaglistmaybe, tpfile):
    try:
        shutil.move(tpfile, '{0}backup/todo_{1}.txt'.format(tpfile[:-8], TODAY))
        appendfilearchive = open('{0}archive.txt'.format(tpfile[:-8]), 'a')
        appendfilemaybe = open('{0}maybe.txt'.format(tpfile[:-8]), 'a')

        outfile = open(tpfile, 'w')

        print('work:', file=outfile)
        for task in flaglist:
            if task.project == 'work':
                print('\t{0}'.format(task.taskline), file=outfile)

        print('\nhome:', file=outfile)

        for task in flaglist:
            if task.project == 'home':
                print('\t{0}'.format(task.taskline), file=outfile)

        print('\nRepeat:', file=outfile)

        for task in flaglist:
            if task.project == 'Repeat':
                print('\t{0}'.format(task.taskline), file=outfile)

        print('\nArchive:', file=outfile)

        print('\nINBOX:', file=outfile)

        for task in flaglist:
            if task.project == 'INBOX':
                print('\t{0}'.format(task.taskline), file=outfile)

        print('\n', file=outfile)

        # append all done-files to archive-file
        for task in flaglistarchive:
            if task.project == 'Archive':
                print('\t{0}'.format(task.taskline), file=appendfilearchive)

        # append all maybe-files to maybe.txt
        for task in flaglistmaybe:
            if task.project == 'Maybe':
                print('\t{0}'.format(task.taskline), file=appendfilemaybe)

    except Exception as exc:
        sys.exit("creating output failed; {0}".format(exc))


def createTaskListHighOverdue(flaglist, destination):
    try:
        mytxt = '## Open tasks with prio high or overdue:\n'
        for task in flaglist:
            if task.project == destination and \
                (task.overdue or task.prio == 1) and task.startdate <= str(TODAY):
                    taskstring = removeTaskParts(task.taskline, '@start')
                    mytxt = '{0}{1}\n'.format(mytxt, taskstring.strip())
    except Exception as exc:
        sys.exit("creating task list for High and Overdue failed; {0}".format(exc))
    return mytxt


def markdown2html(text):
    text = text.encode("utf-8")
    return markdown2.markdown(text)


def html2pdf(html, outfile):
    html = html.encode("utf-8")
    pdf = pisa.CreatePDF(
        cStringIO.StringIO(html),
        file(outfile, "wb")
        )
    if pdf.err:
        print("*** {0} ERRORS OCCURED".format(pdf.err))
        sys.exit()


def sendPushover(content):
    import httplib
    import urllib
    content = content.encode("utf-8")
    try:
        conn = httplib.HTTPSConnection("api.pushover.net:443")
        conn.request("POST", "/1/messages.json",
            urllib.urlencode({
                "token": PUSHOVERTOKEN,
                "user": PUSHOVERUSER,
                "message": content,
            }), {"Content-type": "application/x-www-form-urlencoded"})
        print('pushover-funct')
        conn.getresponse()
    except Exception as exc:
        sys.exit("sending pushover message failed; {0}".format(exc))


def sendMail(content, subject, sender, receiver, text_subtype, encrypted):
    import smtplib
    from email.mime.text import MIMEText
    content = content.encode("utf-8")
    try:
        if encrypted is False:
            msg = MIMEText(content, text_subtype)
        elif encrypted is True:
            if ENCRYPTMAIL:
                import gnupg
                gpg = gnupg.GPG(gnupghome=GNUPGHOME)
                gpg.encoding = 'utf-8'
                contentenc = gpg.encrypt(content, TARGETFINGERPRINT, always_trust=True)
                msg = MIMEText(str(contentenc), text_subtype)
            else:
                raise "encryption required, but not set in config file"
        msg['Subject'] = subject
        msg['From'] = sender

        conn = smtplib.SMTP(SMTPSERVER, SMTPPORT)
        conn.starttls()
        if DEBUG:
            conn.set_debuglevel(True)
        else:
            conn.set_debuglevel(False)
        conn.login(SMTPUSER, SMTPPASSWORD)
        try:
            conn.sendmail(sender, receiver, msg.as_string())
        finally:
            conn.close()

    except Exception as exc:
        sys.exit("sending email failed; {0}".format(exc))


def createMail(flaglist, destination, encrypted):
    if SENDMAIL:
        try:
            source = SOURCEEMAIL
            desthome = DESTHOMEEMAIL
            destwork = DESTWORKEMAIL

            mytxt = '<html><head><title>Tasks for Today</title></head><body>'

            mytxt = '{0}<h1>Tasks for Today</h1><p>'.format(mytxt)
            mytxtasc = '# Tasks for Today\n'
            mytxt = '{0}<h2>Overdue tasks</h2><p>'.format(mytxt)
            mytxtasc = '{0}\n## Overdue tasks\n'.format(mytxtasc)
            # Overdue

            for task in flaglist:
                if task.overdue is True and task.project == destination:
                    taskstring = removeTaskParts(task.taskline, '@')
                    taskstring = '{0} @due({1})'.format(taskstring, task.duedate)
                    mytxt = '{0}<FONT COLOR="#ff0033">{1}</FONT><br/>'.format(mytxt,
                            taskstring.strip())
                    mytxtasc = '{0}{1}\n'.format(mytxtasc, taskstring.strip())

            mytxt = '{0}<h2>Due soon tasks</h2>'.format(mytxt)
            mytxtasc = '{0}\n## Due soon tasks\n'.format(mytxtasc)

            # Due soon

            for task in flaglist:
                if task.project == destination and task.duesoon is True and task.done is False:
                    taskstring = removeTaskParts(task.taskline, '@')
                    taskstring = '{0} @due({1})'.format(taskstring, task.duedate)
                    mytxt = '{0}{1}<br/>'.format(mytxt, taskstring.strip())
                    mytxtasc = '{0}{1}\n'.format(mytxtasc, taskstring.strip())

            mytxt = '{0}<h2>High priority tasks</h2><p>'.format(mytxt)
            mytxtasc = '{0}\n## High priority tasks ##\n'.format(mytxtasc)

            # All other high prio tasks
            for task in flaglist:
                if task.project == destination and task.prio == 1 \
                        and task.startdate <= str(TODAY) \
                        and (task.overdue is not True or task.duesoon is not True) \
                        and task.done is False:
                    taskstring = removeTaskParts(task.taskline, '@start @prio')
                    if task.duedate != '2999-12-31':
                        taskstring = '{0} @due({1})'.format(taskstring, task.duedate)
                    mytxt = '{0}<FONT COLOR="#ff0033">{1}</FONT><br/>'.format(mytxt,
                            taskstring.strip())
                    mytxtasc = '{0}{1}\n'.format(mytxtasc, taskstring.strip())
            mytxt = '{0}</table></body></html>'.format(mytxt)

            if destination == 'home':
                sendMail(mytxt, 'Taskpaper daily overview', source, desthome, 'html', False)
            elif destination == 'work':
                sendMail(mytxtasc, 'Taskpaper daily overview', source, destwork, 'text', True)
            else:
                raise "wrong destination"

        except Exception as exc:
            sys.exit("creating email failed; {0}".format(exc))


def createUniqueList(flaglist, element, group):
    mylist = []
    for task in flaglist:
        if '@{0}'.format(element) in task.taskline and task.project == group:
            mycontent = re.search(r'\@' + element + '\((.*?)\)', task.taskline).group(1)
            if mycontent not in mylist:
                mylist.append(mycontent)
    return mylist


def createTaskList(flaglist, element, headline, mylist, group):
    mytasks = '\n\n## {0}\n'.format(headline)
    for listelement in mylist:
        mytasks = '{0}\n\n### {1}\n'.format(mytasks, listelement)
        for task in flaglist:
            if '@{0}'.format(element) in task.taskline and task.project == group:
                if re.search(r'\@' + element + '\((.*?)\)', task.taskline).group(1) == listelement:
                    mytasks = '{0}\n{1}'.format(mytasks, task.taskline)
    return mytasks


def writeFile(mytext, filename):
    try:
        mytext = mytext.encode("utf-8")
        outfile = open(filename, 'w')
        outfile.write(b'{0}'.format(mytext))
        outfile.close()
    except Exception as exc:
        sys.exit("writing file failed; {0}".format(exc))


def main():
    (inputfile, configfile, modus) = parseArgs(sys.argv[1:])
    parseConfig(configfile)

    flaglist = parseInput(inputfile)
    parseInputDB(inputfile)
    #for row in conn.execute('SELECT * FROM tasks'):
    #    print('DB: {0}'.format(row))

    if modus == "daily":
        (flaglist, flaglistarchive) = archiveDone(flaglist)
        (flaglist, flaglistmaybe) = archiveMaybe(flaglist)
        flaglist = setRepeat(flaglist)
        flaglist = sortList(flaglist)
        flaglist = filterWhitespaces(flaglist)
        flaglistarchive = filterWhitespaces(flaglistarchive)
        flaglistmaybe = filterWhitespaces(flaglistmaybe)
        if DEBUG:
            printOutFileDebug(flaglist, flaglistarchive, flaglistmaybe, inputfile)
        else:
            printOutFile(flaglist, flaglistarchive, flaglistmaybe, inputfile)
        if SENDMAIL:
            if SENDMAILHOME:
                createMail(flaglist, 'home', False)
            if SENDMAILWORK:
                createMail(flaglist, 'work', True)
        if PUSHOVER:
            if PUSHOVERHOME:
                pushovertxt = createTaskListHighOverdue(flaglist, 'home')
                # pushover limits messages sizes to 512 characters
                if len(pushovertxt) > 512:
                        pushovertxt = pushovertxt[:512]
                sendPushover(pushovertxt)
            if PUSHOVERWORK:
                pushovertxt = createTaskListHighOverdue(flaglist, 'work')
                # pushover limits messages sizes to 512 characters
                if len(pushovertxt) > 512:
                        pushovertxt = pushovertxt[:512]
                sendPushover(pushovertxt)
    elif modus == "review":
        reviewgroup = []
        if REVIEWHOME:
            reviewgroup.append('home')
        if REVIEWWORK:
            reviewgroup.append('work')
        for group in reviewgroup:
            reviewfile = '{0}/Review_{1}_{2}'.format(REVIEWPATH, group, TODAY)
            reviewtext = '# Review\n\n'
            reviewtext = '{0}\n{1}'.format(reviewtext, createTaskListHighOverdue(flaglist, group))
            if REVIEWAGENDA:
                agendalist = createUniqueList(flaglist, 'agenda', group)
                agendatasks = createTaskList(flaglist, 'agenda', 'Agenda', agendalist, group)
                reviewtext = '{0}\n{1}'.format(reviewtext, agendatasks)
            if REVIEWWAITING:
                waitinglist = createUniqueList(flaglist, 'waiting', group)
                waitingtasks = createTaskList(flaglist, 'waiting',
                    'Waiting For', waitinglist, group)
                reviewtext = '{0}\n{1}'.format(reviewtext, waitingtasks)
            if REVIEWCUSTOMERS:
                customerlist = createUniqueList(flaglist, 'customer', group)
                customertasks = createTaskList(flaglist, 'customer',
                    'Customers', customerlist, group)
                reviewtext = '{0}\n{1}'.format(reviewtext, customertasks)
            if REVIEWPROJECTS:
                projectlist = createUniqueList(flaglist, 'project', group)
                projecttasks = createTaskList(flaglist, 'project', 'Projects', projectlist, group)
                reviewtext = '{0}\n{1}'.format(reviewtext, projecttasks)

            html = markdown2html(reviewtext)

            if REVIEWOUTPUTMD:
                writeFile(reviewtext, '{0}.md'.format(reviewfile))
            if REVIEWOUTPUTHTML:
                writeFile(html, '{0}.html'.format(reviewfile))
            if REVIEWOUTPUTPDF:
                html2pdf(html, '{0}.pdf'.format(reviewfile))
    else:
        print("modus error")
        sys.exit()


if __name__ == '__main__':
    sys.exit(main())
