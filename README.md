# TaskPaperManager


TaskPaperManager (TPM) is a python script to parse and modify a TaskPaper file.
It provides the following features:

* Move done tasks (@done) to a separate archive file
* Check any repeat-tasks (@repeat) and instantiate a new task entry if a repeat-cycle comes up
* send daily status mails for @high, @duesoon and @overdue tasks
* flag tasks with due dates as @duesoon or @overdue (helpful for hightlighting with modified TaskPaper Theme)
* Sort the list (primary sort criterium: @prio, secondary: @start)
* Copy tasks with the tag @maybe in a dedicated maybe list and remove from master list
* Provide a weekly review report (pdf, html, markdown)

## Build Status

[![Build Status](https://travis-ci.org/mhofherr/TaskPaperManager.svg?branch=develop)](https://travis-ci.org/mhofherr/TaskPaperManager)

[![Coverage Status](https://coveralls.io/repos/mhofherr/TaskPaperManager/badge.png?branch=develop)](https://coveralls.io/r/mhofherr/TaskPaperManager?branch=develop)

## Installation

Follow these steps for installation:

* copy `tpm.py` to a script directory on your machine
* create a config file (content see below)
* copy the file `requirements.txt`
* `pip install -r requirements.txt`
* test the script on a copy of your task file
* if it works:
    *  add a cron job for regular execution

## Command line

The script requires the following command line:  
`tpm.py -i <inputfile> -c <configfile> -m <mode:daily|review>`

The individual options are:  
* -i: The full path to your taskpaper file
* -c: The full path to ypur config file (contents see below)
* -m: the mode of execution; may be either `daily` or `review`

## Modes

TaskPaperParser support two modes of execution:

* `Daily mode`: this should be run once per day; it performs the daily maintenance tasks on your taskpaper file
* `Review mode`: this is intended for the weekly review; it should run once per week (or whenever you want to perform a review) after the daily run

## Python versions

TPM is developed on Python 2.7. Support for Python 3.4 is planned for the 1.1.0 release.

## Future features

* Full support for Python 3.4
* Support for multi-lin tasks (1-n comment lines per task)
* sanitize the tags: bring the tags in a fixed order; detection malformed/missing tags
* support pgp/mime for sending encrypted emails (to support encrypted html emails)
* provide a pypi package
* Technical: change to sqlite in-memory database for data management

## Current limitations

* One task - one line: comment line for tasks are currently not supported
* Stacked projects: there is no multi-level support of projects


## Configuration

The variable parameters are configured via a separate config file (tpm.cfg):

    [tpm]
    debug: False
    duedelta: days
    dueinterval: 3

    [mail]
    sendmail: True
    sendmailhome: True
    sendmailwork: False
    smtpserver: <FQDN of your smtp server>
    smtpport: <listening port of your smtp server>
    smtpuser: <your user on the server>
    smtppassword: <your password>
    sourceemail: <sender mail address>
    destworkemail: <receiver mail address; work>
    desthomeemail: <receiver mail address; home>
    encryptmail: True
    gnupghome: <Path to your home>/.gnupg
    targetfingerprint: <Fingerprint of the gpg key of the email receiver>

    [pushover]
    pushover: True
    pushoverhome: True
    pushoverwork: False
    pushovertoken: <application token>
    pushoveruser: <user string>

    [review]
    reviewwork: True
    reviewhome: True
    outputpdf: True
    outputhtml: True
    outputmd: True
    reviewpath: <path to save the review files>
    reviewagenda: True
    reviewprojects: True
    reviewcustomers: True
    reviewwaiting: True

### Parameter Explanations

* **debug**: When enabling debug mode the script will not modify your tasklist but will print instead debug output. This has no influence on sending email or sending pushover messages.
* **dueinterval**: all tasks will be tagged as @duesoon when today is x days (or whatever you define for *duedelta*) before the duedate (defined in @due(...))
* **duedelta**: unit for *dueinterval*; may be `days`, `weeks` or `months` 
* **sendmail**: Do you want to get a daily overview for your tasks by mail? 
* **sendmailhome**: For your home tasks?
* **sendmailwork**: For your works tasks?
* **smtpserver**: The FQDN of your smtp server 
* **smtpport**: The listening port of your smtp server
* **smtpuser**: Username
* **smtppassword**: Password
* **sourceemail**: The sender mail address
* **destworkemail**: The mail address for the work email
* **desthomeemail**: The mail address for the home email
* **encryptmail**: Do you want to encrypt your email? Requires a working gpg-setup
* **gnupghome**: The path to your .gnupg directory
* **targetfingerprint**: the fingerprint for the recipient key
* **pushover**: Do you want to get a daily overview for your tasks by mail? 
* **pushoverhome**: For your home tasks?
* **pushoverwork**: For your works tasks?
* **pushovertoken**: Your application token for pushover
* **pushoveruser**: Your user token for pushover
* **reviewwork**: Review mode only: include work tasks?
* **reviewhome**: Review mode only: include home tasks?
* **outputpdf**: Create the review in PDF?
* **outputhtml**: Create the review in HTML?
* **outputmd**: Create the review in Markdown text?
* **reviewpath**: The directory where your review files will be stored
* **reviewagenda**: Include an overview for @agenda?
* **reviewprojects**: Include an overview for @project?
* **reviewcustomers**:  Include an overview for @customer?
* **reviewwaiting**: Include an overview for @waiting?

## Supported tags
The following tags are actively used in TPM:

* @start(): the start day of the task in ISO 8601 format (e.g. 2014-05-15)
* @due(): the due day; same format as above
* @prio(): high, medium or low; my used based in the MYN methodology of Michael Linenberger
* @done: task is done; will be moved to the file "archive.txt" in the same folder
* @customer(): the task is associated with a customer
* @maybe: will be moved to a separate list named "maybe.txt" in the same folder
* @project(): the task is associated with a project name or project number
* @waiting(): waiting for a specific person to complete the task
* @agenda(): task to discuss with a specific person
* @repeat(): repeating task; a special group of tasks which will be instantiated as new tasks after a certain interval (see details below)
* @home: only used in @repeat tasks; will instantiate the new task in the *home* section  
* @work: only used in @repeat tasks; will instantiate the new task in the *work* section

Any other tags are supported insofar, as they are not touched by TPM.

## Repeating tasks
Tasks which will be instantiated at regular intervals are marked with the tag "@repeat()". The value within the parentheses of the @repeat-tag determine the interval. The first value is a number, the second determines the unit (where "d"=day, "w"=week and "m"=month). So, **@repeat(2w)** will instantiate a new task with the same name every 2 weeks, starting from the @start-date. The original @repeat-task will stay in place, only a new @start-date will be set.
All repeat-tasks must be in a dedicated taskpaper group called "Repeat:". 

## Projects
TaskPaper treats all lines ending with a colon (:) as projects. I use these TaskPaper "projects" only as main sections in my TaskPaper file. My actual projects are grouped by the tag *@project()*. See "The TaskPaper file" below for an overview about required sections in the TaskPaper file. 

## The TaskPaper file
TPM requires all tasks in one task file, formated in TaskPaper syntax. A TaskPaper file sample for TPM looks as follows:

    work:
        - task 1 @prio(high) @start(2014-05-24) @due(2014-06-30)
        - task 2 @prio(medium) @start(2014-05-13) @project(XYZ) @customer(RTZ)
        - task 3 @prio(low) @start(2014-04-15) @waiting(Mr. X)

    home:
        - Task 4 @prio(high) @start(2014-05-17) @agenda(Mr. X)

    Repeat:
        - repeat task 1 @prio(high) @repeat(2d) @work @start(2014-05-16)
        - repeat task 2 @prio(medium) @repeat(3w) @home @start(2014-05-16)
        - repeat task 3 @prio(high) @repeat(6m) @work @start(2014-05-16)

    INBOX:

Tasks flagged as *@maybe* will be copied to a file named *maybe.txt* in the same directory as the TaskPaper file. Tasks flagged as *@done* will be copied to a file named *archive.txt* (same directory). Each run of the the script will make a copy of the existing TaskPaper file to the subdirectory *backup* before making any modifications. The files maybe.txt and archive.txt and the backup-directory must exist before running the script. 

## Regular script starts
TPM is intended to be run once every 24 hours (e.g. by using cron). I run it on my server on my server once every day at 05:00 am in the morning, where my TaskPaper file is available on a mounted dropbox folder. 

## Sending email
You can either send email encrypted (gpg) or in plain text. The communication to the server uses SSL/TLS with starttls. Content encryption requires gnupg installed and the python-gnupg module.

## Sending pushover messages
Enter your userstring and application token from pushover into the config file and enable the sending of pushover messages by setting "pushover: True". Pushover messages are limited to a maximum of 512 characters, so the scripts cuts of anything beyond.
Please mind: Pushover allows a maximum of 7500 messages per application token per month. The script provides no limiting for outgoing messages.

## TaskPaper Theme

The TaskPaper theme highlights @overdue and @prio(high) in red and bold. @Duesoon is highlighted in dark orange.

## KeyboardMaestro

Adding tags by hand can be quite tedious, so KeyboardMaestro comes to the rescue. You can find my KM macros for all supported text in the directory "KeyboardMaestro".

## Contact

Do you  have questions or comments about `TaskPaperManager`? Contact me via [taskpaper@mhofherr.de](mailto:taskpaper@mhofherr.de) or [twitter](https://twitter.com/MatthiasHofherr).

## Changelog

### Version 1.0.0

* Added review mode
* Added proper command line syntax
* enhanced config file
* heavy refactoring and bug fixing

### Version 0.9.0

* released after several bugfixes and heavy refactoring
* version 1.0.0 will include review mode
* internal: included tests, Travis CI, coveralls.io ... 

