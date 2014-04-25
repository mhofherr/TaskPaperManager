#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# TaskPaper Parser
# based on a script from K. Marchand
# heavily modified for my own requirements
#
from __future__ import print_function

from datetime import datetime, timedelta
from collections import namedtuple
from operator import itemgetter
from dateutil import parser
from dateutil.relativedelta import relativedelta

import shutil
import sys
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import email.utils

DEBUG = False
#DEBUG = True
SENDMAIL = True
#SENDMAIL = False

DUEDELTA = 'days'
# how many days before the due date should the task be highlighted as duesoon?
DUEINTERVAL = 3

Flagged = namedtuple('Flagged', ['prio', 'taskdate', 'project', 'task', 'done', 'repeat', 'repeatinterval', 'duedate', 'duesoon', 'overdue'])
Flaggednew = namedtuple('Flaggednew', ['prio', 'taskdate', 'project', 'task', 'done', 'repeat', 'repeatinterval', 'duedate', 'duesoon', 'overdue'])
Flaggedarchive = namedtuple('Flaggedarchive', ['prio', 'taskdate', 'project', 'task', 'done', 'repeat', 'repeatinterval', 'duedate', 'duesoon', 'overdue'])

today_date = datetime.date(datetime.now())
daybefore = today_date - timedelta(days=1)


def parseInput(tpfile):
	with open(tpfile, 'rb') as f:
		tplines = f.readlines()
	flaglist = []
	flaglistnew = []
	flaglistarchive = []
	errlist = []
	project = ''

	for line in tplines:
		try:
			done = 'false'
			repeat = '-'
			repeatinterval = '-'
			duedate = '2999-12-31'
			duesoon = 'false'
			overdue = 'false'
			# remove empty lines and task-lines without any content
			if not line.strip():
				continue
			if line.strip() == '-':
				continue
			if ':\n' in line:
				project = line.strip()[:-1]
				continue
			if '@done' in line:
				done = 'true'
			if '@repeat' in line:
				repeat = 'true'
				repeatinterval = re.search(r'\@repeat\((.*?)\)', line).group(1)
			if '@due' in line:
				duedate = re.search(r'\@due\((.*?)\)', line).group(1)
				duealert = datetime.date(parser.parse(duedate)) - timedelta(**{ DUEDELTA: DUEINTERVAL})
				if duealert <= today_date <= datetime.date(parser.parse(duedate)):
					duesoon = 'true'
				if datetime.date(parser.parse(duedate)) < today_date:
					overdue = 'true'
			if '@start' in line and '@prio' in line:
				priotag = re.search(r'\@prio\((.*?)\)', line).group(1)
				if priotag == 'high':
					priotag = 1
				elif priotag == 'medium':
					priotag = 2
				elif priotag == 'low':
					priotag = 3
				starttag = re.search(r'\@start\((.*?)\)', line).group(1)
				taskdate = datetime.date(parser.parse(starttag))
				flaglist.append(
					Flagged(priotag, starttag, project, line.strip(), done, repeat, repeatinterval, duedate, duesoon, overdue))
			else:
				flaglist.append(
					Flagged('-', '-', project, line.strip(), done, repeat, repeatinterval, duedate, duesoon, overdue))
		except Exception, e:
			errlist.append((line, e))
	f.close()
	if DEBUG:
	    for task in flaglist:
	        print ('IN:' + str(task.prio) + ' | ' + str(task.taskdate ) + ' | ' +  str(task.project) + ' | ' + str(task.task) + ' | ' + str(task.done) + ' | ' + str(task.repeat) + ' | ' + str(task.repeatinterval) + ' | ' + str(task.duesoon) + ' | ' + str(task.overdue))
	return flaglist

# overdue und duesoon tags enfernen
def removeTags(flaglist):
	flaglistnew = []
	for task in flaglist:
		if '@overdue' in task.task or '@duesoon' in task.task:
			taskstring = ''
			cut_string = task.task.split(' ')
			for i in range(0, len(cut_string)):
				if '@overdue' in cut_string[i]:
					continue
				if '@duesoon' in cut_string[i]:
					continue
				taskstring = taskstring + cut_string[i] + ' '
			flaglistnew.append(
				Flaggednew(task.prio, task.taskdate, task.project, taskstring, task.done, task.repeat, task.repeatinterval, task.duedate, task.duesoon, task.overdue))
		else:
			flaglistnew.append(
				Flaggednew(task.prio, task.taskdate, task.project, task.task, task.done, task.repeat, task.repeatinterval, task.duedate, task.duesoon, task.overdue))

	# move items from flaglistnew back to flaglist
	flaglist = []
	for tasknew in flaglistnew:
		flaglist.append(
					Flagged(tasknew.prio, tasknew.taskdate, tasknew.project, tasknew.task, tasknew.done, tasknew.repeat, tasknew.repeatinterval, tasknew.duedate, tasknew.duesoon, tasknew.overdue))
	return flaglist

# overdue und duesoon tags setzen
def setTags(flaglist):
	flaglistnew = []
	for task in flaglist:
		if task.overdue == 'true':
			flaglistnew.append(
				Flaggednew(task.prio, task.taskdate, task.project, task.task + ' @overdue', task.done, task.repeat, task.repeatinterval, task.duedate, task.duesoon, task.overdue))
		elif  task.duesoon == 'true':
			flaglistnew.append(
				Flaggednew(task.prio, task.taskdate, task.project, task.task + ' @duesoon', task.done, task.repeat, task.repeatinterval, task.duedate, task.duesoon, task.overdue))
		else:
			flaglistnew.append(
				Flaggednew(task.prio, task.taskdate, task.project, task.task, task.done, task.repeat, task.repeatinterval, task.duedate, task.duesoon, task.overdue))

	# move items from flaglistnew back to flaglist
	flaglist = []
	for tasknew in flaglistnew:
		flaglist.append(
					Flagged(tasknew.prio, tasknew.taskdate, tasknew.project, tasknew.task, tasknew.done, tasknew.repeat, tasknew.repeatinterval, tasknew.duedate, tasknew.duesoon, tasknew.overdue))
	return flaglist

# done durchgehen und ins Archiv umhaengen
def archiveDone(flaglist):
	Flaggedarchive = namedtuple('Flaggedarchive', ['prio', 'taskdate', 'project', 'task', 'done', 'repeat', 'repeatinterval', 'duedate', 'duesoon', 'overdue'])
	flaglistnew = []
	flaglistarchive = []

	for task in flaglist:
		if task.done == 'true':
			if DEBUG:
				print('DONELOOP:' + str(task.prio) + ' | ' + str(task.taskdate )+ ' | ' +  str(task.project) + ' | ' + str(task.task) + ' | ' + str(task.done) + ' | ' + str(task.repeat) + ' | ' + str(task.repeatinterval) + ' | ' + str(task.duedate) + ' | ' + str(task.duesoon) + ' | ' + str(task.overdue))

			taskstring = ''
			cut_string = task.task.split(' ')
			for i in range(0, len(cut_string)):
				if '@done' in cut_string[i]:
					continue
				taskstring = taskstring + cut_string[i] + ' '
			newtask = taskstring + ' @project(' + task.project + ') @done(' + str(daybefore) + ')'
			flaglistarchive.append(
				Flaggedarchive(task.prio, task.taskdate, 'Archive', newtask, task.done, task.repeat, task.repeatinterval, task.duedate, task.duesoon, task.overdue))
		else:
			flaglistnew.append(
				Flaggednew(task.prio, task.taskdate, task.project, task.task, task.done, task.repeat, task.repeatinterval, task.duedate, task.duesoon, task.overdue))


	# move items from flaglistnew back to flaglist
	flaglist = []
	for tasknew in flaglistnew:
		flaglist.append(
					Flagged(tasknew.prio, tasknew.taskdate, tasknew.project, tasknew.task, tasknew.done, tasknew.repeat, tasknew.repeatinterval, tasknew.duedate, tasknew.duesoon, tasknew.overdue))
	return flaglist, flaglistarchive

# check repeat statements; instanciate new tasks if startdate + repeat interval = today
def setRepeat(flaglist):
	flaglistnew = []

	for task in flaglist:
		if task.project == 'Repeat' and task.repeat == 'true':
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
				newtaskdate = datetime.date(parser.parse(task.taskdate)) + timedelta(**{delta: intnum})
			if delta == 'month':
				newtaskdate = datetime.date(parser.parse(task.taskdate)) + relativedelta(months=intnum)
			# instanciate anything which is older or equal then today 
			if newtaskdate <= today_date:
				if '@home' in task.task:
					projecttag = 'home'
				if '@work' in task.task:
					projecttag = 'work'
				# get the relevant information from the task description
				taskstring = ''
				cut_string = task.task.split(' ')
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
				taskstring = taskstring + ' ' + '@start(' + str(newtaskdate) + ')'
				done = 'false'
				repeat = '-'
				repeatinterval = '-'
				# create new instance of repeat task
				flaglistnew.append(
						Flaggednew(task.prio, str(newtaskdate), projecttag, taskstring, done, repeat, repeatinterval, task.duedate, task.duesoon, task.overdue))
				# remove old start-date in taskstring; add newtaskdate as start date instead
				taskstring = ''
				cut_string = task.task.split(' ')
				for i in range(0, len(cut_string)):
					if '@start' in cut_string[i]:
						continue
					taskstring = taskstring + cut_string[i] + ' '
				taskstring = taskstring + ' ' + '@start(' + str(newtaskdate) + ')'
				# prepare modified entry for repeat-task
				flaglistnew.append(
					Flaggednew(task.prio, task.taskdate, task.project, taskstring, task.done, task.repeat, task.repeatinterval, task.duedate, task.duesoon, task.overdue))
			else:
				# write back repeat tasks with non-matching date
				flaglistnew.append(
					Flaggednew(task.prio, task.taskdate, task.project, task.task, task.done, task.repeat, task.repeatinterval, task.duedate, task.duesoon, task.overdue))
		else:
			flaglistnew.append(
				Flaggednew(task.prio, task.taskdate, task.project, task.task, task.done, task.repeat, task.repeatinterval, task.duedate, task.duesoon, task.overdue))
	# move items from flaglistnew back to flaglist
	flaglist = []
	for tasknew in flaglistnew:
		flaglist.append(
					Flagged(tasknew.prio, tasknew.taskdate, tasknew.project, tasknew.task, tasknew.done, tasknew.repeat, tasknew.repeatinterval, tasknew.duedate, tasknew.duesoon, tasknew.overdue))

	if DEBUG:
	    for task in flaglist:
	        print ('OUT:' + str(task.prio) + ' | ' + str(task.taskdate )+ ' | ' +  str(task.project) + ' | ' + str(task.task) + ' | ' + str(task.done) + ' | ' + str(task.repeat) + ' | ' + str(task.repeatinterval))
	return flaglist

def sortList(flaglist):
	# sort in following order: project (asc), prio (asc), date (desc)
	flaglist = sorted(flaglist, key=itemgetter(Flagged._fields.index('taskdate')), reverse=True)
	flaglist = sorted(flaglist, key=itemgetter(Flagged._fields.index('project'), Flagged._fields.index('prio')))
	return flaglist

def printOutFile(flaglist, flaglistarchive, tpfile):
	if DEBUG:
		print ('work:')
		for task in flaglist:
			if task.project == 'work':
				print ('\t' + str(task.task))

		print ('\nhome:')

		for task in flaglist:
			if task.project == 'home':
				print ('\t' + str(task.task))


		print ('\nRepeat:')

		for task in flaglist:
			if task.project == 'Repeat':
				print ('\t' + str(task.task))


		print ('\nArchive:')


		print ('\nINBOX:')

		for task in flaglist:
			if task.project == 'INBOX':
				print ('\t' + str(task.task))

		print ('\n')

		# append all done-files to archive-file
		for task in flaglistarchive:
			if task.project == 'Archive':
				print ('\t' + str(task.task))

	else:

		shutil.move(tpfile, tpfile[:-8] + 'backup/todo_' + str(today_date) + '.txt')
		appendfile = open(tpfile[:-8] + 'archive.txt', 'a')

		outfile = open(tpfile, 'w')

		print ('work:', file=outfile)
		for task in flaglist:
			if task.project == 'work':
				print ('\t' + str(task.task), file=outfile)

		print ('\nhome:', file=outfile)

		for task in flaglist:
			if task.project == 'home':
				print ('\t' + str(task.task), file=outfile)


		print ('\nRepeat:', file=outfile)

		for task in flaglist:
			if task.project == 'Repeat':
				print ('\t' + str(task.task), file=outfile)


		print ('\nArchive:', file=outfile)


		print ('\nINBOX:', file=outfile)

		for task in flaglist:
			if task.project == 'INBOX':
				print ('\t' + str(task.task), file=outfile)

		print ('\n', file=outfile)

		# append all done-files to archive-file
		for task in flaglistarchive:
			if task.project == 'Archive':
				print ('\t' + str(task.task), file=appendfile)

def sendMail(flaglist, destination):
	if SENDMAIL:
		source = "matthias@hofherr.me"
		desthome = "matthias@hofherr.me"
		destwork = "matthias@atsec.com"

		
		mytxt = '*Tasks for Today*\n\n'
		mytxt = mytxt + "*Overdue tasks*\n\n"
		# Overdue
		for task in flaglist:
			if task.overdue == 'true':
				taskstring = ''
				cut_string = task.task.split(' ')
				for i in range(0, len(cut_string)):
					if '@' in cut_string[i]:
						continue
					taskstring = taskstring + cut_string[i] + ' '
				taskstring = taskstring + '@due(' + task.duedate + ')'
				mytxt = mytxt + taskstring.strip() + '\n'

		mytxt = mytxt + "\n\n*Due soon tasks*\n\n"
		# Due soon
		for task in flaglist:
			if task.duesoon == 'true' and task.done == 'false':
				taskstring = ''
				cut_string = task.task.split(' ')
				for i in range(0, len(cut_string)):
					if '@' in cut_string[i]:
						continue
					taskstring = taskstring + cut_string[i] + ' '
				taskstring = taskstring + '@due(' + task.duedate + ')'
				mytxt = mytxt + taskstring.strip() + '\n'

		mytxt = mytxt + "\n\n*High and Medium tasks*\n\n"
		# All other high and medium prio tasks
		for task in flaglist:
			if task.project == 'home' and ( task.prio == 1 or task.prio == 2 ) and task.taskdate <= str(today_date) and ( task.overdue != 'true' or task.duesoon != 'true' ) and task.done == 'false':
				taskstring = ''
				cut_string = task.task.split(' ')
				for i in range(0, len(cut_string)):
					if '@start' in cut_string[i]:
						continue
					if '@prio' in cut_string[i]:
						continue
					taskstring = taskstring + cut_string[i] + ' '
				taskstring = taskstring + '@due(' + task.duedate + ')'
				mytxt = mytxt + taskstring.strip() + '\n'

		#msg = MIMEText(unicode(mytxt))
		msg = MIMEText(mytxt)
		if destination == 'HOME':
			msg['To'] = email.utils.formataddr(('TaskPaper', desthome))
		elif destination == 'WORK':
			msg['To'] = email.utils.formataddr(('TaskPaper', destwork))
		else:
			print('Error, wrong destination')
			return -1			
		msg['From'] = email.utils.formataddr(('Matthias Hofherr', source))
		msg['Subject'] = 'Taskpaper daily overview'

		s = smtplib.SMTP('localhost')

		if destination == 'HOME':
			s.sendmail(source, desthome, msg.as_string())
		elif destination == 'WORK':
			s.sendmail(source, destwork, msg.as_string())
		s.quit()

def main():
	tpfile = sys.argv[1]
	flaglist = parseInput(tpfile)
	flaglist = removeTags(flaglist)
	flaglist = setTags(flaglist)
	(flaglist, flaglistarchive) = archiveDone(flaglist)
	flaglist = setRepeat(flaglist)
	flaglist = sortList(flaglist)
	printOutFile(flaglist, flaglistarchive, tpfile)
	sendMail(flaglist, 'HOME')
	#sendMail(flaglist, 'WORK')

main ()