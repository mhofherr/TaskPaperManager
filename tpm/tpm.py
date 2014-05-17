#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# TaskPaperManager
# originally based on a small script for printing a task summary from K. Marchand
# now completely re-written and modified for my own requirements
#
# License: GPL v3 (for details see LICENSE file)

from __future__ import (absolute_import, division, print_function, unicode_literals)

from datetime import datetime, timedelta
from collections import namedtuple
from operator import itemgetter
from dateutil import parser
from dateutil.relativedelta import relativedelta
import ConfigParser

import shutil
import sys
import re
import os

"""Data structure
....prio: priority of the task - high, medium or low; mapped to 1, 2 or 3
....startdate: when will the task be visible - format: yyyy-mm-dd
....project: with which project is the task associated
....taskline: the actual task line
....done: is it done?; based on @done tag; boolean
....repeat: only for tasks in the project"repeat"; boolean
....repeatinterval: the repeat inteval is given by a number followed by an interval type; e.g.
........2w = 2 weeks
........3d = 3 days
........1m = 1 month
....duedate: same format as startdate
....duesoon: boolean; true if today is duedate minus DUEDELTA in DUEINTERVAL (constants) or less
....overdue: boolean; true if today is after duedate"""

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


# filter unnecessary spaces
def filterWhitespaces(flaglist):
    flaglistnew = []
    for task in flaglist:
        print('Vorher:{0}'.format(task.taskline))
        taskstring = ' '.join(task.taskline.split())
        print('Nachher:{0}'.format(taskstring))
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


def parseConfig():
    # sets the config parameters as global variables
    # tpm.cfg config file required - for details see README.md
    # set correct path if not in same directory as script
    dn = os.path.dirname(os.path.realpath(__file__))
    Config = ConfigParser.ConfigParser()
    Config.read('{0}/tpm.cfg'.format(dn))
    global DEBUG
    global SENDMAIL
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

    DEBUG = Config.getboolean('tpm', 'debug')
    SENDMAIL = Config.getboolean('mail', 'sendmail')
    SMTPSERVER = ConfigSectionMap(Config, 'mail')['smtpserver']
    SMTPPORT = Config.getint('mail', 'smtpport')
    SMTPUSER = ConfigSectionMap(Config, 'mail')['smtpuser']
    SMTPPASSWORD = ConfigSectionMap(Config, 'mail')['smtppassword']
    PUSHOVER = Config.getboolean('pushover', 'pushover')
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

        # move items from flaglistnew back to flaglist
        flaglist = flaglistnew
        return flaglist
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

        # move items from flaglistnew back to flaglist
        flaglist = flaglistnew
        return flaglist
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
        flaglist = flaglistnew
        return (flaglist, flaglistarchive)
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
    flaglist = flaglistnew
    return (flaglist, flaglistmaybe)


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
    flaglist = flaglistnew

    #if DEBUG:
    #    printDebugOutput(flaglist, 'AfterRepeat')
    return flaglist


def sortList(flaglist):
    try:
        # sort in following order: project (asc), prio (asc), date (desc)
        flaglist = sorted(flaglist, key=itemgetter(Flagged._fields.index('startdate')), reverse=True)
        flaglist = sorted(flaglist, key=itemgetter(Flagged._fields.index('project'),Flagged._fields.index('prio')))
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

def createPushover(flaglist, destination):
    try:
        mytxt = 'Open tasks with prio high or overdue:\n'
        for task in flaglist:
            if task.project == destination and \
                (task.overdue or task.prio == 1) and task.startdate <= str(TODAY):
                    taskstring = removeTaskParts(task.taskline, '@start')
                    mytxt = '{0}{1}\n'.format(mytxt, taskstring.strip())
        # pushover limits messages sizes to 512 characters
        if len(mytxt) > 512:
                mytxt = mytxt[:512]
        sendPushover(mytxt)

    except Exception as exc:
        sys.exit("creating pushover message failed; {0}".format(exc))


def sendPushover(content):
    import httplib
    import urllib
    try:
        conn = httplib.HTTPSConnection("api.pushover.net:443")
        conn.request("POST", "/1/messages.json",
            urllib.urlencode({
                "token": PUSHOVERTOKEN,
                "user": PUSHOVERUSER,
                "message": content,
            }), {"Content-type": "application/x-www-form-urlencoded"})
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
                    print('Before:{0}'.format(task.taskline))
                    taskstring = removeTaskParts(task.taskline, '@')
                    print('After:{0}'.format(taskstring))
                    taskstring = '{0} @due({1})'.format(taskstring, task.duedate)
                    mytxt = '{0}<FONT COLOR="#ff0033">{1}</FONT><br/>'.format(mytxt, taskstring.strip())
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
                    mytxt = '{0}<FONT COLOR="#ff0033">{1}</FONT><br/>'.format(mytxt, taskstring.strip())
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


def main():
    parseConfig()
    tpfile = sys.argv[1]
    flaglist = parseInput(tpfile)
    flaglist = removeTags(flaglist)
    flaglist = setTags(flaglist)
    (flaglist, flaglistarchive) = archiveDone(flaglist)
    (flaglist, flaglistmaybe) = archiveMaybe(flaglist)
    flaglist = setRepeat(flaglist)
    flaglist = sortList(flaglist)
    flaglist = filterWhitespaces(flaglist)
    flaglistarchive = filterWhitespaces(flaglistarchive)
    flaglistmaybe = filterWhitespaces(flaglistmaybe)
    if DEBUG:
        printOutFileDebug(flaglist, flaglistarchive, flaglistmaybe, tpfile)
    else:
        printOutFile(flaglist, flaglistarchive, flaglistmaybe, tpfile)
    if SENDMAIL:
        createMail(flaglist, 'home', False)
        #createMail(flaglist, 'work', True)
    if PUSHOVER:
        createPushover(flaglist, 'home')

if __name__ == '__main__':
    sys.exit(main())
