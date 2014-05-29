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
from dateutil import parser
from dateutil.relativedelta import relativedelta
from email.mime.text import MIMEText

import markdown2
import xhtml2pdf.pisa as pisa
import getopt
import shutil
import sys
import re
import httplib
import urllib
import smtplib
import gnupg
import sqlite3

from six.moves import configparser
from six.moves import cStringIO


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


TODAY = datetime.date(datetime.now())
DAYBEFORE = TODAY - timedelta(days=1)


# create in-memory db instance
def initDB():
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
        cur.execute('''CREATE TABLE comments(
            commentid INTEGER PRIMARY KEY,
            taskid INTEGER,
            commentline text,
            FOREIGN KEY(taskid) REFERENCES tasks(taskid)
            )''')
        conn.commit()
    except sqlite3.Error as e:
        sys.exit("An error occurred: {0}".format(e.args[0]))
    return conn


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
def sanitizer(con):
    try:
        cursel = con.cursor()
        curup = con.cursor()
        # check tasks in project work and home
        cursel.execute("SELECT taskid, taskline FROM tasks where project = 'work'\
            or project = 'home'")
        for row in cursel:
            if '@prio' not in row[1] or '@start' not in row[1]:
                curup.execute("UPDATE tasks SET project='Error' WHERE taskid=?", (row[0],))
            taskstring = ' '.join(row[1].split())
            curup.execute("UPDATE tasks SET taskline=? WHERE taskid=?",
                         (taskstring, row[0]))
        # check tasks in project repeat
        cursel.execute("SELECT taskid, taskline FROM tasks where project = 'Repeat'")
        for row in cursel:
            if '@prio' not in row[1] or '@start' not in row[1] or '@repeat' not in row[1] or not\
                    (('@work' not in row[1] and '@home' in row[1]) or (('@work' in row[1] and
                    '@home' not in row[1]))):
                curup.execute("UPDATE tasks SET project='Error' WHERE taskid=?", (row[0],))
            taskstring = ' '.join(row[1].split())
            curup.execute("UPDATE tasks SET taskline=? WHERE taskid=?",
                         (taskstring, row[0]))
        con.commit()
    except sqlite3.Error as e:
        sys.exit("An error occurred: {0}".format(e.args[0]))


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


class settings:
    """ contains the settings for TPN, parsed from the config file """

    def __init__(self, configfile):
        Config = configparser.ConfigParser()
        Config.read(configfile)
        self.debug = Config.getboolean('tpm', 'debug')
        self.sendmail = Config.getboolean('mail', 'sendmail')
        self.sendmailhome = Config.getboolean('mail', 'sendmailwork')
        self.sendmailwork = Config.getboolean('mail', 'sendmailhome')
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
        self.reviewoutputpdf = Config.getboolean('review', 'outputpdf')
        self.reviewoutputhtml = Config.getboolean('review', 'outputhtml')
        self.reviewoutputmd = Config.getboolean('review', 'outputmd')
        self.reviewhome = Config.getboolean('review', 'reviewhome')
        self.reviewwork = Config.getboolean('review', 'reviewwork')
        self.pushoverhome = Config.getboolean('pushover', 'pushoverhome')
        self.pushoverwork = Config.getboolean('pushover', 'pushoverwork')


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


def printDebugOutput(con, prepend):
    try:
        cursel = con.cursor()
        cursel.execute("SELECT prio, startdate, project, taskline, done, repeat,\
            repeatinterval, duedate, duesoon, overdue, maybe FROM tasks")
        for row in cursel:
            print("{0}: {1} | {2} | {3} | {4} | {5} | {6} | {7} | {8} | {9} | {10} | {11}".format(
                prepend, row[0], row[1], row[2], row[3],
                row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11]))
        con.commit()
    except sqlite3.Error as e:
        sys.exit("printDebugOutput - An error occurred: {0}".format(e.args[0]))


def parseInput(tpfile, con, configfile):
    sett = settings(configfile)
    try:
        cur = con.cursor()
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
                        - timedelta(**{sett.duedelta: sett.dueinterval})
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
                            ( priotag, starttag, project, line.strip(), done, repeat,
                            repeatinterval, duedate, duesoon, overdue, maybe))
                    except sqlite3.Error as e:
                        sys.exit("parseInput - An error occurred: {0}".format(e.args[0]))
                else:
                    try:
                        cur.execute("insert into tasks (prio, startdate, project, taskline, done,\
                            repeat, repeatinterval, duedate, duesoon, overdue, maybe) values\
                            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (None, None, project, line.strip(), done, repeat,
                            repeatinterval, duedate, duesoon, overdue, maybe))
                    except sqlite3.Error as e:
                        sys.exit("parseInput - An error occurred: {0}".format(e.args[0]))
                con.commit()
            except Exception as e:
                errlist.append((line, e))
        f.close()
    except Exception as exc:
        sys.exit("parsing input file to db failed; {0}".format(exc))


# remove overdue and duesoon tags
def removeTags(con):
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


# set overdue and duesoon tags
def setTags(con):
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


# check @done and mark for later move to archive
def archiveDone(con):
    try:
        cursel = con.cursor()
        curup = con.cursor()
        cursel.execute("SELECT taskid, taskline, project FROM tasks where done = 1")
        for row in cursel:
            #print(row)
            taskstring = removeTaskParts(row[1], '@done')
            newtask = '{0} @project({1}) @done({2})'.format(taskstring, row[2], DAYBEFORE)
            curup.execute("UPDATE tasks SET taskline=?, project=? WHERE taskid=?",
                         (newtask, 'Archive', row[0]))
        con.commit()
    except sqlite3.Error as e:
        sys.exit("archiveDone - An error occurred: {0}".format(e.args[0]))


# check @maybe and mark for later move to maybe file
def archiveMaybe(con):
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


# check repeat statements; instantiate new tasks if startdate + repeat interval = today
def setRepeat(con):
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
                    datetime.date(parser.parse(row[1])) \
                    + timedelta(**{delta: intnum})
            if delta == 'month':
                newstartdate = \
                    datetime.date(parser.parse(row[1])) \
                    + relativedelta(months=intnum)

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
                    # ! todo: repeatinterval durch NULL ersetzen
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


def printDebug(con, tpfile):
    try:
        print('work:')
        cursel = con.cursor()
        cursel.execute("SELECT taskline, project, prio, startdate FROM tasks\
            where project = 'work' ORDER BY prio asc, startdate desc ")
        for row in cursel:
            print('\t{0}'.format(row[0]).encode("utf-8"))
        print('\nhome:')
        cursel.execute("SELECT taskline, project, prio, startdate FROM tasks\
            where project = 'home' ORDER BY prio asc, startdate desc ")
        for row in cursel:
            print('\t{0}'.format(row[0]).encode("utf-8"))
        print('\nRepeat:')
        cursel.execute("SELECT taskline, project, prio, startdate FROM tasks\
            where project = 'Repeat' ORDER BY prio asc, startdate desc ")
        for row in cursel:
            print('\t{0}'.format(row[0]).encode("utf-8"))
        print('\nArchive:')
        print('\nINBOX:')
        cursel.execute("SELECT taskline, project, prio, startdate FROM tasks\
            where project = 'INBOX' ORDER BY prio asc, startdate desc ")
        for row in cursel:
            print('\t{0}'.format(row[0]).encode("utf-8"))
        print('\nArchive:')
        cursel.execute("SELECT taskline, project, prio, startdate FROM tasks\
            where project = 'Archive' ORDER BY prio asc, startdate desc ")
        for row in cursel:
            print('\t{0}'.format(row[0]).encode("utf-8"))
        print('\nError:')
        cursel.execute("SELECT taskline, project, prio, startdate FROM tasks\
            where project = 'Error' ORDER BY prio asc, startdate desc ")
        for row in cursel:
            print('\t{0}'.format(row[0]).encode("utf-8"))
        print('\nMaybe:')
        cursel.execute("SELECT taskline, project, prio, startdate FROM tasks\
            where project = 'Maybe' ORDER BY prio asc, startdate desc ")
        for row in cursel:
            print('\t{0}'.format(row[0]).encode("utf-8"))
        con.commit()
    except sqlite3.Error as e:
        sys.exit("printDebug - An error occurred: {0}".format(e.args[0]))


def createOutFile(con):
    try:
        mytxt = ''
        mytxt = 'work:\n'
        cursel = con.cursor()
        cursel.execute("SELECT taskline, project, prio, startdate FROM tasks\
            where project = 'work' ORDER BY prio asc, startdate desc ")
        for row in cursel:
            mytxt = '{0}\t{1}\n'.format(mytxt, row[0])
        mytxt = '{0}\nhome:\n'.format(mytxt)
        cursel.execute("SELECT taskline, project, prio, startdate FROM tasks\
            where project = 'home' ORDER BY prio asc, startdate desc ")
        for row in cursel:
            mytxt = '{0}\t{1}\n'.format(mytxt, row[0])
        mytxt = '{0}\nRepeat:\n'.format(mytxt)
        cursel.execute("SELECT taskline, project, prio, startdate FROM tasks\
            where project = 'Repeat' ORDER BY prio asc, startdate desc ")
        for row in cursel:
            mytxt = '{0}\t{1}\n'.format(mytxt, row[0])
        mytxt = '{0}\nError:\n'.format(mytxt)
        cursel.execute("SELECT taskline, project, prio, startdate FROM tasks\
            where project = 'Error' ORDER BY prio asc, startdate desc ")
        for row in cursel:
            mytxt = '{0}\t{1}\n'.format(mytxt, row[0])
        mytxt = '{0}\nINBOX:\n'.format(mytxt)
        cursel.execute("SELECT taskline, project, prio, startdate FROM tasks\
            where project = 'INBOX' ORDER BY prio asc, startdate desc ")
        for row in cursel:
            mytxt = '{0}\t{1}\n'.format(mytxt, row[0])
        mytxtdone = ''
        cursel.execute("SELECT taskline, project, prio, startdate FROM tasks\
            where project = 'Archive' ORDER BY prio asc, startdate desc ")
        for row in cursel:
            mytxtdone = '{0}\t{1}\n'.format(mytxtdone, row[0])
        mytxtmaybe = ''
        cursel.execute("SELECT taskline, project, prio, startdate FROM tasks\
            where project = 'Maybe' ORDER BY prio asc, startdate desc ")
        for row in cursel:
            mytxtmaybe = '{0}\t{1}\n'.format(mytxtmaybe, row[0])
        con.commit()
    except sqlite3.Error as e:
        sys.exit("createOutFile - An error occurred: {0}".format(e.args[0]))
    return (mytxt, mytxtdone, mytxtmaybe)


def createTaskListHighOverdue(con, destination):
    try:
        mytxt = '## Open tasks with prio high:\n'
        cursel = con.cursor()
        cursel.execute("SELECT taskline, project, prio, startdate FROM tasks\
            where project = ? and prio = 1 and \
            startdate <= date( julianday(date('now'))) and done = 0 ORDER BY prio asc,\
            startdate desc ", (destination,))
        for row in cursel:
            taskstring = removeTaskParts(row[0], '@start')
            mytxt = '{0}{1}\n'.format(mytxt, taskstring.strip())
        mytxt = '{0}\n## Open tasks - overdue:\n'.format(mytxt)
        cursel.execute("SELECT taskline, project, prio, startdate FROM tasks\
            where project = ? and overdue = 1 and \
            done = 0 ORDER BY prio asc, startdate desc ", (destination,))
        for row in cursel:
            taskstring = removeTaskParts(row[0], '@start')
            mytxt = '{0}{1}\n'.format(mytxt, taskstring.strip())
        con.commit()
    except sqlite3.Error as e:
        sys.exit("createTaskListHighOverdue - An error occurred: {0}".format(e.args[0]))
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


def sendPushover(content, configfile):
    sett = settings(configfile)
    content = content.encode("utf-8")
    try:
        conn = httplib.HTTPSConnection("api.pushover.net:443")
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
    sett = settings(configfile)
    content = content.encode("utf-8")
    try:
        if encrypted is False:
            msg = MIMEText(content, text_subtype)
        elif encrypted is True:
            if sett.encryptmail:
                gpg = gnupg.GPG(gnupghome=sett.gnupghome)
                gpg.encoding = 'utf-8'
                contentenc = gpg.encrypt(content, sett.targetfingerprint, always_trust=True)
                msg = MIMEText(str(contentenc), text_subtype)
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


def createMail(con, destination, encrypted, configfile):
    sett = settings(configfile)
    if sett.sendmail:
        try:
            cursel = con.cursor()

            source = sett.sourceemail
            desthome = sett.desthomeemail
            destwork = sett.destworkemail

            mytxt = '<html><head><title>Tasks for Today</title></head><body>'
            mytxt = '{0}<h1>Tasks for Today</h1><p>'.format(mytxt)
            mytxtasc = '# Tasks for Today\n'
            mytxt = '{0}<h2>Overdue tasks</h2><p>'.format(mytxt)
            mytxtasc = '{0}\n## Overdue tasks\n'.format(mytxtasc)

            # Overdue
            cursel.execute("SELECT taskline, project, prio, startdate, duedate FROM tasks\
                where project = ? and overdue = 1 and done = 0 ORDER BY prio asc,\
                startdate desc ", (destination,))
            for row in cursel:
                taskstring = removeTaskParts(row[0], '@')
                taskstring = '{0} @due({1})'.format(taskstring, row[4])
                mytxt = '{0}<FONT COLOR="#ff0033">{1}</FONT><br/>'.format(mytxt,
                        taskstring.strip())
                mytxtasc = '{0}{1}\n'.format(mytxtasc, taskstring.strip())
            mytxt = '{0}<h2>Due soon tasks</h2>'.format(mytxt)
            mytxtasc = '{0}\n## Due soon tasks\n'.format(mytxtasc)

            # Due soon
            cursel.execute("SELECT taskline, project, prio, startdate, duedate FROM tasks\
                where project = ? and duesoon = 1 and done = 0 ORDER BY prio asc,\
                startdate desc ", (destination,))
            for row in cursel:
                taskstring = removeTaskParts(row[0], '@')
                taskstring = '{0} @due({1})'.format(taskstring, row[4])
                mytxt = '{0}{1}<br/>'.format(mytxt, taskstring.strip())
                mytxtasc = '{0}{1}\n'.format(mytxtasc, taskstring.strip())

            mytxt = '{0}<h2>High priority tasks</h2><p>'.format(mytxt)
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
                mytxt = '{0}<FONT COLOR="#ff0033">{1}</FONT><br/>'.format(mytxt,
                        taskstring.strip())
                mytxtasc = '{0}{1}\n'.format(mytxtasc, taskstring.strip())
            mytxt = '{0}</table></body></html>'.format(mytxt)

            if destination == 'home':
                sendMail(mytxt, 'Taskpaper daily overview', source, desthome, 'html', False, configfile)
            elif destination == 'work':
                sendMail(mytxtasc, 'Taskpaper daily overview', source, destwork, 'text', True, configfile)
            else:
                raise "wrong destination"

        except Exception as exc:
            sys.exit("creating email failed; {0}".format(exc))


def createUniqueList(con, element, group):
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
                        mytasks = '{0}\n{1}'.format(mytasks, row[0])
        except sqlite3.Error as e:
            sys.exit("createTaskList - An error occurred: {0}".format(e.args[0]))
    return mytasks


def myFile(mytext, filename, mode):
    try:
        mytext = mytext.encode("utf-8")
        outfile = open(filename, mode)
        outfile.write(b'{0}'.format(mytext))
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
        setRepeat(mycon)
        sanitizer(mycon)
        if sett.debug:
            printDebug(mycon, inputfile)
        else:
            (mytxt, mytxtdone, mytxtmaybe) = createOutFile(mycon)
            shutil.move(inputfile, '{0}backup/todo_{1}.txt'.format(inputfile[:-8], TODAY))
            myFile(mytxt, inputfile, 'w')
            myFile(mytxtdone, '{0}archive.txt'.format(inputfile[:-8]), 'a')
            myFile(mytxtmaybe, '{0}maybe.txt'.format(inputfile[:-8]), 'a')
        if sett.sendmail:
            if sett.sendmailhome:
                createMail(mycon, 'home', False, configfile)
            if sett.sendmailwork:
                createMail(mycon, 'work', True, configfile)
        if sett.pushover:
            if sett.pushoverhome:
                pushovertxt = createTaskListHighOverdue(mycon, 'home')
                # pushover limits messages sizes to 512 characters
                if len(pushovertxt) > 512:
                        pushovertxt = pushovertxt[:512]
                sendPushover(pushovertxt, configfile)
            if sett.pushoverwork:
                pushovertxt = createTaskListHighOverdue(mycon, 'work')
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
            reviewtext = '{0}\n{1}'.format(reviewtext, createTaskListHighOverdue(mycon, group))
            if sett.reviewagenda:
                agendalist = createUniqueList(mycon, 'agenda', group)
                agendatasks = createTaskList(mycon, 'agenda', 'Agenda', agendalist, group)
                reviewtext = '{0}\n{1}'.format(reviewtext, agendatasks)
            if sett.reviewwaiting:
                waitinglist = createUniqueList(mycon, 'waiting', group)
                waitingtasks = createTaskList(mycon, 'waiting',
                    'Waiting For', waitinglist, group)
                reviewtext = '{0}\n{1}'.format(reviewtext, waitingtasks)
            if sett.reviewcustomers:
                customerlist = createUniqueList(mycon, 'customer', group)
                customertasks = createTaskList(mycon, 'customer',
                    'Customers', customerlist, group)
                reviewtext = '{0}\n{1}'.format(reviewtext, customertasks)
            if sett.reviewprojects:
                projectlist = createUniqueList(mycon, 'project', group)
                projecttasks = createTaskList(mycon, 'project', 'Projects', projectlist, group)
                reviewtext = '{0}\n{1}'.format(reviewtext, projecttasks)

            html = markdown2html(reviewtext)

            if sett.reviewoutputmd:
                myFile(reviewtext, '{0}.md'.format(reviewfile), 'w')
            if sett.reviewoutputhtml:
                myFile(html, '{0}.html'.format(reviewfile), 'w')
            if sett.reviewoutputpdf:
                html2pdf(html, '{0}.pdf'.format(reviewfile))
    else:
        print("modus error")
        sys.exit()


if __name__ == '__main__':
    sys.exit(main())
