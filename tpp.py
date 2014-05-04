#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# TaskPaper Parser
# originally based on a small script for printing a task summary from K. Marchand
# now completely re-written and modified for my own requirements
#
# License: GPL v3 (for details see LICENSE file)

from __future__ import print_function

from datetime import datetime, timedelta
from collections import namedtuple
from operator import itemgetter
from dateutil import parser
from dateutil.relativedelta import relativedelta
import ConfigParser
import gnupg

import shutil
import sys
import re
import smtplib
from email.mime.text import MIMEText


def ConfigSectionMap(section):
    dict1 = {}
    options = Config.options(section)
    for option in options:
        try:
            dict1[option] = Config.get(section, option)
            if dict1[option] == -1:
                print('skip: %s' % option)
        except:
            print('exception on %s!' % option)
            dict1[option] = None
    return dict1


# tpp.cfg config file required - for details see README.md

Config = ConfigParser.ConfigParser()

# set correct path if not in local directory
Config.read('tpp.cfg')


DEBUG = Config.getboolean('tpp', 'debug')
SENDMAIL = Config.getboolean('mail', 'sendmail')
if SENDMAIL is True:
    SMTPSERVER = ConfigSectionMap('mail')['smtpserver']
    SMTPPORT = Config.getint('mail', 'smtpport')
    SMTPUSER = ConfigSectionMap('mail')['smtpuser']
    SMTPPASSWORD = ConfigSectionMap('mail')['smtppassword']

DUEDELTA = ConfigSectionMap('tpp')['duedelta']
DUEINTERVAL = Config.getint('tpp', 'dueinterval')


if Config.getboolean('mail', 'encryptmail') is True:
    gpg = gnupg.GPG(gnupghome=ConfigSectionMap('mail')['gnupghome'])
    gpg.encoding = 'utf-8'

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


Flagged = namedtuple('Flagged', [
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
])
Flaggednew = namedtuple('Flaggednew', [
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
])
Flaggedarchive = namedtuple('Flaggedarchive', [
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
])

TODAY = datetime.date(datetime.now())
DAYBEFORE = TODAY - timedelta(days=1)


def parseInput(tpfile):
    with open(tpfile, 'rb') as f:
        tplines = f.readlines()
    flaglist = []
    errlist = []
    project = ''

    for line in tplines:
        try:
            done = False
            repeat = False
            repeatinterval = '-'
            duedate = '2999-12-31'
            duesoon = False
            overdue = False

            if not line.strip():
                continue
            if line.strip() == '-':
                continue
            if ':\n' in line:
                project = line.strip()[:-1]
                continue
            if '@done' in line:
                done = True
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
                ))
        except Exception, e:
            errlist.append((line, e))
    f.close()
    if DEBUG:
        for task in flaglist:
            print('IN:' + str(task.prio) + ' | ' + str(task.startdate)
                  + ' | ' + str(task.project) + ' | '
                  + str(task.taskline) + ' | ' + str(task.done) + ' | '
                  + str(task.repeat) + ' | ' + str(task.repeatinterval)
                  + ' | ' + str(task.duesoon) + ' | '
                  + str(task.overdue))
    return flaglist


# remove overdue and duesoon tags

def removeTags(flaglist):
    flaglistnew = []
    for task in flaglist:
        if '@overdue' in task.taskline or '@duesoon' in task.taskline:
            taskstring = ''
            cut_string = task.taskline.split(' ')
            for i in range(0, len(cut_string)):
                if '@overdue' in cut_string[i]:
                    continue
                if '@duesoon' in cut_string[i]:
                    continue
                taskstring = taskstring + cut_string[i] + ' '
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
            ))

    # move items from flaglistnew back to flaglist

    flaglist = []
    for tasknew in flaglistnew:
        flaglist.append(Flagged(
            tasknew.prio,
            tasknew.startdate,
            tasknew.project,
            tasknew.taskline,
            tasknew.done,
            tasknew.repeat,
            tasknew.repeatinterval,
            tasknew.duedate,
            tasknew.duesoon,
            tasknew.overdue,
        ))
    return flaglist


# set overdue and duesoon tags

def setTags(flaglist):
    flaglistnew = []
    for task in flaglist:
        if task.overdue:
            flaglistnew.append(Flaggednew(
                task.prio,
                task.startdate,
                task.project,
                task.taskline + ' @overdue',
                task.done,
                task.repeat,
                task.repeatinterval,
                task.duedate,
                task.duesoon,
                task.overdue,
            ))
        elif task.duesoon:
            flaglistnew.append(Flaggednew(
                task.prio,
                task.startdate,
                task.project,
                task.taskline + ' @duesoon',
                task.done,
                task.repeat,
                task.repeatinterval,
                task.duedate,
                task.duesoon,
                task.overdue,
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
            ))

    # move items from flaglistnew back to flaglist

    flaglist = []
    for tasknew in flaglistnew:
        flaglist.append(Flagged(
            tasknew.prio,
            tasknew.startdate,
            tasknew.project,
            tasknew.taskline,
            tasknew.done,
            tasknew.repeat,
            tasknew.repeatinterval,
            tasknew.duedate,
            tasknew.duesoon,
            tasknew.overdue,
        ))
    return flaglist


# check @done and move to archive file

def archiveDone(flaglist):
    flaglistnew = []
    flaglistarchive = []

    for task in flaglist:
        if task.done:
            if DEBUG:
                print('DONELOOP:' + str(task.prio) + ' | '
                      + str(task.startdate) + ' | ' + str(task.project)
                      + ' | ' + str(task.taskline) + ' | '
                      + str(task.done) + ' | ' + str(task.repeat)
                      + ' | ' + str(task.repeatinterval) + ' | '
                      + str(task.duedate) + ' | ' + str(task.duesoon)
                      + ' | ' + str(task.overdue))

            taskstring = ''
            cut_string = task.taskline.split(' ')
            for i in range(0, len(cut_string)):
                if '@done' in cut_string[i]:
                    continue
                taskstring = taskstring + cut_string[i] + ' '
            newtask = taskstring + ' @project(' + task.project \
                + ') @done(' + str(DAYBEFORE) + ')'
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
            ))
    flaglist = []
    for tasknew in flaglistnew:
        flaglist.append(Flagged(
            tasknew.prio,
            tasknew.startdate,
            tasknew.project,
            tasknew.taskline,
            tasknew.done,
            tasknew.repeat,
            tasknew.repeatinterval,
            tasknew.duedate,
            tasknew.duesoon,
            tasknew.overdue,
        ))
    return (flaglist, flaglistarchive)


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

                taskstring = ''
                cut_string = task.taskline.split(' ')
                for i in range(0, len(cut_string)):
                    if '@repeat' in cut_string[i]:
                        continue
                    if '@home' in cut_string[i]:
                        continue
                    if '@work' in cut_string[i]:
                        continue
                    if '@start' in cut_string[i]:
                        continue
                    taskstring = taskstring + cut_string[i] + ' '
                taskstring = taskstring + ' ' + '@start(' \
                    + str(newstartdate) + ')'
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
                ))

                # remove old start-date in taskstring; add newstartdate as start date instead

                taskstring = ''
                cut_string = task.taskline.split(' ')
                for i in range(0, len(cut_string)):
                    if '@start' in cut_string[i]:
                        continue
                    taskstring = taskstring + cut_string[i] + ' '
                taskstring = taskstring + ' ' + '@start(' \
                    + str(newstartdate) + ')'

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
            ))

    # move items from flaglistnew back to flaglist

    flaglist = []
    for tasknew in flaglistnew:
        flaglist.append(Flagged(
            tasknew.prio,
            tasknew.startdate,
            tasknew.project,
            tasknew.taskline,
            tasknew.done,
            tasknew.repeat,
            tasknew.repeatinterval,
            tasknew.duedate,
            tasknew.duesoon,
            tasknew.overdue,
        ))

    if DEBUG:
        for task in flaglist:
            print('OUT:' + str(task.prio) + ' | ' + str(task.startdate)
                  + ' | ' + str(task.project) + ' | '
                  + str(task.taskline) + ' | ' + str(task.done) + ' | '
                  + str(task.repeat) + ' | ' + str(task.repeatinterval))
    return flaglist


def sortList(flaglist):

    # sort in following order: project (asc), prio (asc), date (desc)

    flaglist = sorted(flaglist,
		key=itemgetter(Flagged._fields.index('startdate'
        )), reverse=True)
    flaglist = sorted(flaglist,
        key=itemgetter(Flagged._fields.index('project'),
        Flagged._fields.index('prio')))
    return flaglist


def printOutFile(flaglist, flaglistarchive, tpfile):
    if DEBUG:
        print('work:')
        for task in flaglist:
            if task.project == 'work':
                print('\t' + str(task.taskline))

        print('\nhome:')

        for task in flaglist:
            if task.project == 'home':
                print('\t' + str(task.taskline))

        print('\nRepeat:')

        for task in flaglist:
            if task.project == 'Repeat':
                print('\t' + str(task.taskline))

        print('\nArchive:')

        print('\nINBOX:')

        for task in flaglist:
            if task.project == 'INBOX':
                print('\t' + str(task.taskline))

        print('\n')

        # append all done-files to archive-file

        for task in flaglistarchive:
            if task.project == 'Archive':
                print('\t' + str(task.taskline))
    else:

        shutil.move(tpfile, tpfile[:-8] + 'backup/todo_' + str(TODAY) + '.txt')
        appendfile = open(tpfile[:-8] + 'archive.txt', 'a')

        outfile = open(tpfile, 'w')

        print('work:', file=outfile)
        for task in flaglist:
            if task.project == 'work':
                print('\t' + str(task.taskline), file=outfile)

        print('\nhome:', file=outfile)

        for task in flaglist:
            if task.project == 'home':
                print('\t' + str(task.taskline), file=outfile)

        print('\nRepeat:', file=outfile)

        for task in flaglist:
            if task.project == 'Repeat':
                print('\t' + str(task.taskline), file=outfile)

        print('\nArchive:', file=outfile)

        print('\nINBOX:', file=outfile)

        for task in flaglist:
            if task.project == 'INBOX':
                print('\t' + str(task.taskline), file=outfile)

        print('\n', file=outfile)

        # append all done-files to archive-file

        for task in flaglistarchive:
            if task.project == 'Archive':
                print('\t' + str(task.taskline), file=appendfile)


def sendMail(content, subject, sender, receiver, text_subtype, encrypted):
    try:
        if encrypted is False:
            msg = MIMEText(content, text_subtype)
        elif encrypted is True:
            contentenc = gpg.encrypt(content,
                ConfigSectionMap('mail')['targetfingerprint'], always_trust=True)
            msg = MIMEText(str(contentenc), text_subtype)
        else:
            print('encrypted parameter is not boolean')
            return -1
        msg['Subject'] = subject
        msg['From'] = sender

        conn = smtplib.SMTP(SMTPSERVER, SMTPPORT)
        conn.starttls()
        conn.set_debuglevel(False)
        conn.login(SMTPUSER, SMTPPASSWORD)
        try:
            conn.sendmail(sender, receiver, msg.as_string())
        finally:
            conn.close()

    except Exception, exc:
        sys.exit("sending email failed; %s" % str(exc))


def createMail(flaglist, destination, encrypted):
    if SENDMAIL:
        source = ConfigSectionMap('mail')['sourceemail']
        desthome = ConfigSectionMap('mail')['desthomeemail']
        destwork = ConfigSectionMap('mail')['destworkemail']

        mytxt = '<html><head><title>Tasks for Today</title></head><body>'

        mytxt = mytxt + '<h1>Tasks for Today</h1><p>'
        mytxtasc = '# Tasks for Today #\n'
        mytxt = mytxt + '<h2>Overdue tasks</h2><p>'
        mytxtasc = mytxtasc + '\n## Overdue tasks ##\n'
        # Overdue

        for task in flaglist:
            if task.overdue is True and task.project == destination:
                taskstring = ''
                cut_string = task.taskline.split(' ')
                for i in range(0, len(cut_string)):
                    if '@' in cut_string[i]:
                        continue
                    taskstring = taskstring + cut_string[i] + ' '
                taskstring = taskstring + '@due(' + task.duedate + ')'
                mytxt = mytxt + '<FONT COLOR="#ff0033">' + taskstring.strip() + '</FONT>' + '<br/>'
                mytxtasc = mytxtasc + taskstring.strip() + '\n'

        mytxt = mytxt + '<h2>Due soon tasks</h2>'
        mytxtasc = mytxtasc + '\n## Due soon tasks ##\n'

        # Due soon

        for task in flaglist:
            if task.project == destination and task.duesoon is True and task.done is False:
                taskstring = ''
                cut_string = task.taskline.split(' ')
                for i in range(0, len(cut_string)):
                    if '@' in cut_string[i]:
                        continue
                    taskstring = taskstring + cut_string[i] + ' '
                taskstring = taskstring + '@due(' + task.duedate + ')'
                mytxt = mytxt + taskstring.strip() + '<br/>'
                mytxtasc = mytxtasc + taskstring.strip() + '\n'

        mytxt = mytxt + '<h2>High priority tasks</h2><p>'
        mytxtasc = mytxtasc + '\n## High priority tasks ##\n'

        # All other high prio tasks

        for task in flaglist:
            if task.project == destination and task.prio == 1 \
                    and task.startdate <= str(TODAY) \
                    and (task.overdue is not True or task.duesoon is not True) \
                    and task.done is False:
                taskstring = ''
                cut_string = task.taskline.split(' ')
                for i in range(0, len(cut_string)):
                    if '@start' in cut_string[i]:
                        continue
                    if '@prio' in cut_string[i]:
                        continue
                    taskstring = taskstring + cut_string[i] + ' '
                if task.duedate != '2999-12-31':
                    taskstring = taskstring + '@due(' + task.duedate + ')'
                mytxt = mytxt + '<FONT COLOR="#ff0033">' + taskstring.strip() + '</FONT>' + '<br/>'
                mytxtasc = mytxtasc + taskstring.strip() + '\n'

        mytxt = mytxt + '<h2>Medium priority tasks</h2><p>'
        mytxtasc = mytxtasc + '\n## Medium priority tasks ##\n'

        # All other medium prio tasks

        for task in flaglist:
            if task.project == destination and \
                    task.prio == 2 and task.startdate <= str(TODAY) \
                    and (task.overdue is not True or task.duesoon is not True) \
                    and task.done is False:
                taskstring = ''
                cut_string = task.taskline.split(' ')
                for i in range(0, len(cut_string)):
                    if '@start' in cut_string[i]:
                        continue
                    if '@prio' in cut_string[i]:
                        continue
                    taskstring = taskstring + cut_string[i] + ' '
                if task.duedate != '2999-12-31':
                    taskstring = taskstring + '@due(' + task.duedate \
                        + ')'
                mytxt = mytxt + taskstring.strip() + '<br/>'
                mytxtasc = mytxtasc + taskstring.strip() + '\n'

        mytxt = mytxt + '</table></body></html>'

        if destination == 'home':
            sendMail(mytxt, 'Taskpaper daily overview', source, desthome, 'html', False)
        elif destination == 'work':
            sendMail(mytxtasc, 'Taskpaper daily overview', source, destwork, 'text', True)
        else:
            print("wrong destination, aborting")
            return -1


def main():
    tpfile = sys.argv[1]
    flaglist = parseInput(tpfile)
    flaglist = removeTags(flaglist)
    flaglist = setTags(flaglist)
    (flaglist, flaglistarchive) = archiveDone(flaglist)
    flaglist = setRepeat(flaglist)
    flaglist = sortList(flaglist)
    printOutFile(flaglist, flaglistarchive, tpfile)
    createMail(flaglist, 'home', False)
    createMail(flaglist, 'work', True)


main()
