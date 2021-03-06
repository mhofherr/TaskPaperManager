TaskPaperManager
================

TaskPaperManager (TPM) is a python script to parse and modify a
TaskPaper file. It provides the following features:

-  Move done tasks (@done) to a separate archive file
-  Check any repeat-tasks (@repeat) and instantiate a new task entry if
   a repeat-cycle comes up
-  send daily status mails for @high, @duesoon and @overdue tasks
-  flag tasks with due dates as @duesoon or @overdue (helpful for
   hightlighting with modified TaskPaper Theme)
-  Sort the list (primary sort criterium: @prio, secondary: @start)
-  Copy tasks with the tag @maybe in a dedicated maybe list and remove
   from master list
-  Provide a weekly review report (pdf, html, markdown)
-  verify validity of required tags
-  set a @note tag if task has associated notes
-  optionally: create a backup before modifying the todo list

Build Status
------------

|Build Status|

|Coverage Status|

Installation
------------

Follow these steps for installation:

-  copy ``tpm.py`` to a script directory on your machine
-  create a config file (content see below)
-  for Python 2.7:

   -  copy the file ``requirements.txt``
   -  ``pip install -r requirements.txt``

-  for Python 3.4:

   -  copy the file ``requirements_python3.txt``
   -  ``pip install -r requirements_python3.txt``

-  test the script on a copy of your task file
-  if it works:

   -  add a cron job for regular execution

Command line
------------

The script requires the following command line:
``tpm.py -i <inputfile> -c <configfile> -m <daily|review>``

The individual options are: \* -i: The full path to your taskpaper file
\* -c: The full path to ypur config file (contents see below) \* -m: the
mode of execution; may be either ``daily`` or ``review``

Optionally: \* -b: makes a backup of the todo file in subdirectory
``backup``, relative to the todo list; only in daily mode

Modes
-----

TaskPaperParser support two modes of execution:

-  ``Daily mode``: this should be run once per day; it performs the
   daily maintenance tasks on your taskpaper file
-  ``Review mode``: this is intended for the weekly review; it should
   run once per week (or whenever you want to perform a review) after
   the daily run

Python versions
---------------

TPM is developed on Python 2.7. It is tested on python 3.4 as well.

Future features
---------------

-  support pgp/mime for sending encrypted emails (to support encrypted
   html emails)
-  provide a pypi package

Configuration
-------------

The variable parameters are configured via a separate config file
(tpm.cfg):

::

    [tpm]
    debug: False
    duedelta: days
    dueinterval: 3

    [mail]
    sendmail: True
    smtpserver: <FQDN of your smtp server>
    smtpport: <listening port of your smtp server>
    smtpuser: <your user on the server>
    smtppassword: <your password>
    sourceemail: <sender mail address>
    destemail: <receiver mail address>
    encryptmail: True
    gnupghome: <Path to your home>/.gnupg
    targetfingerprint: <Fingerprint of the gpg key of the email receiver>

    [pushover]
    pushover: True
    pushovertoken: <application token>
    pushoveruser: <user string>

    [review]
    outputpdf: True
    outputhtml: True
    outputmd: True
    reviewpath: <path to save the review files>
    reviewagenda: True
    reviewprojects: True
    reviewcustomers: True
    reviewwaiting: True
    reviewmaybe: True

Parameter Explanations
~~~~~~~~~~~~~~~~~~~~~~

-  **debug**: When enabling debug mode the script will not modify your
   tasklist but will print instead debug output. This has no influence
   on sending email or sending pushover messages.
-  **dueinterval**: all tasks will be tagged as @duesoon when today is x
   days (or whatever you define for *duedelta*) before the duedate
   (defined in @due(...))
-  **duedelta**: unit for *dueinterval*; may be ``days``, ``weeks`` or
   ``months``
-  **sendmail**: Do you want to get a daily overview for your tasks by
   mail? If set to ´False\`, the other parameters in section [mail] can
   be empty.
-  **smtpserver**: The FQDN of your smtp server
-  **smtpport**: The listening port of your smtp server
-  **smtpuser**: Username
-  **smtppassword**: Password
-  **sourceemail**: The sender mail address
-  **destemail**: The destination mail address
-  **encryptmail**: Do you want to encrypt your email? Requires a
   working gpg-setup
-  **gnupghome**: The path to your .gnupg directory
-  **targetfingerprint**: the fingerprint for the recipient key
-  **pushover**: Do you want to get a daily overview for your tasks by
   mail? If set to ´False\`, the other parameters in section [Pushover]
   can be empty.
-  **pushovertoken**: Your application token for pushover
-  **pushoveruser**: Your user token for pushover
-  **outputpdf**: Create the review in PDF?
-  **outputhtml**: Create the review in HTML?
-  **outputmd**: Create the review in Markdown text?
-  **reviewpath**: The directory where your review files will be stored
-  **reviewagenda**: Include an overview for @agenda?
-  **reviewprojects**: Include an overview for @project?
-  **reviewcustomers**: Include an overview for @customer?
-  **reviewwaiting**: Include an overview for @waiting?
-  **reviewmaybe**: Include maybe list in review?

Supported tags
--------------

The following tags are actively used in TPM:

-  @start(): the start day of the task in ISO 8601 format (e.g.
   2014-05-15)
-  @due(): the due day; same format as above
-  @prio(): high, medium or low; my used based in the MYN methodology of
   Michael Linenberger
-  @done(): task is done, with date of date finished; will be moved to
   the file "archive.txt" in the same folder
-  @maybe: will be moved to a separate list named "maybe.txt" in the
   same folder
-  @project(): only for repeating tasks, to instantiate the new task in
   the correct project
-  @waiting(): waiting for a specific person to complete the task
-  @agenda(): task to discuss with a specific person
-  @repeat(): repeating task; a special group of tasks which will be
   instantiated as new tasks after a certain interval (see details
   below)
-  @note: show that the task has notes added (additional lines);
   necessary since TaskPaper does not show notes when filtering for tags
-  @SOC: Significant Outcome (see MYN from Michael Linenberger for
   details); shows tasks which require several days
-  @today: handled by TPM, not manually; is set if startdate is today
-  @overdue: handled by TPM, not manually; duedate is before today
-  @duesoon: handled by TPM, not manually; duedate is in the next x days
   (x defined in config file)

Any other tags are supported insofar, as they are not touched by TPM.

Validity of tags
----------------

TPM performs some base checks regarding the validity of tags. The rules
are:

-  tasks in projects (anything with a colon at the end): at least
   require '@prio' and '@start'
-  tasks in 'Repeat': at least require '@prio', '@start', '@repeat' and
   '@project'

If a task does not fulfill these requirements it is sorted in project
'Error'.

TPM additionally checks for matching round brackets. If the brackets do
not match, the task is sorted into project 'Error'.

Repeating tasks
---------------

Tasks which will be instantiated at regular intervals are marked with
the tag "@repeat()". The value within the parentheses of the @repeat-tag
determine the interval. The first value is a number, the second
determines the unit (where "d"=day, "w"=week and "m"=month). So,
**@repeat(2w)** will instantiate a new task with the same name every 2
weeks, starting from the @start-date. The original @repeat-task will
stay in place, only a new @start-date will be set. All repeat-tasks must
be in a dedicated taskpaper group called "Repeat:".

Projects
--------

TaskPaper treats all lines ending with a colon (:) as projects. TPM uses
two special projects:

-  **Inbox**: Is always at the bottom of the file, which helps to add
   tasks on iOS with Drafts and the Dropbox-append action
-  **Repeat**: For repeating tasks

The TaskPaper file
------------------

TPM requires all tasks in one task file, formated in TaskPaper syntax. A
TaskPaper file sample for TPM looks as follows:

::

    <Project 1>:
        - task 1 @prio(high) @start(2014-05-24) @due(2014-06-30)
        - task 2 @prio(medium) @start(2014-05-13)
        - task 3 @prio(low) @start(2014-04-15) @waiting(Mr. X)

    <Project 2>:
        - Task 4 @prio(high) @start(2014-05-17) @agenda(Mr. X)

    Repeat:
        - repeat task 1 @prio(high) @repeat(2d) @project(Project 1) @start(2014-05-16)
        - repeat task 2 @prio(medium) @repeat(3w) @project(Project 2) @start(2014-05-16)
        - repeat task 3 @prio(high) @repeat(6m) @project(Project 1) @start(2014-05-16)

    Error:

    INBOX:

Tasks flagged as *@maybe* will be copied to a file named *maybe.txt* in
the same directory as the TaskPaper file. Tasks flagged as *@done* will
be copied to a file named *archive.txt* (same directory). Optionally
(with -b on the command line) a backup of the current tasklist will be
made to the backup-directory (named "backup" in the local directory of
the task file). The backup-directory must exist before running the
script.

Regular script starts
---------------------

TPM is intended to be run once every 24 hours (e.g. by using cron). I
run it on my server once every day at 05:00 am in the morning, where my
TaskPaper file is available on a mounted dropbox folder.

Sending email
-------------

You can either send email encrypted (gpg) or in plain text. The
communication to the server uses SSL/TLS with starttls. Content
encryption requires gnupg installed and the python-gnupg module.

Sending pushover messages
-------------------------

Enter your userstring and application token from pushover into the
config file and enable the sending of pushover messages by setting
"pushover: True". Pushover messages are limited to a maximum of 512
characters, so the scripts cuts of anything beyond. Please mind:
Pushover allows a maximum of 7500 messages per application token per
month. The script provides no limiting for the number of outgoing
messages.

TaskPaper Theme
---------------

The TaskPaper theme highlights @overdue and @prio(high) in red and bold.
@Duesoon is highlighted in dark orange. @SOC is dark blue and bold.
@prio(low) is light grey.

KeyboardMaestro
---------------

Adding tags by hand can be quite tedious, so KeyboardMaestro comes to
the rescue. You can find my KM macros for all supported tags in the
directory "KeyboardMaestro".

Contact
-------

Do you have questions or comments about ``TaskPaperManager``? Contact me
via taskpaper@mhofherr.de or
`twitter <https://twitter.com/MatthiasHofherr>`__.

FAQ
---

-  **I am on MAC OS X and get the error "OSError: cannot load library
   libcairo.so.2: dlopen(libcairo.so.2, 2): image not found"**:
   Weasyprint requires cairo. You have to install it with your package
   manager of choice. For homebrew: ``brew install cairo``. Rinse and
   repeat for pango, if not already installed.

Changelog
---------

Version 1.5.0
~~~~~~~~~~~~~

-  changed the schema for the task file; up to version 1.4 the idea was
   to use a single task file, with fixed projects for home and work
   usage. Starting with version 1.5, TPM supports arbitrary project
   names in taskpaper notation (a line with a colon at the end is a
   project). Projects are no longer identified by the "@project" tag.
   This makes daily usage much easier. I now use different files for
   home and work.
-  Fixed some wrong assumptions regarding names for backup , archive and
   maybe-files

Version 1.4.0
~~~~~~~~~~~~~

-  backups are no longer performed with every run in daily-mode; set the
   ``-b`` parameter to explicitely generate a backup of your todo file.
   Since I invoke the script several times a day via Alfred, I want to
   make a backup only during the regular nightly runs of tpm.
-  added Alfred workflow sample to invoke tpm
-  set ``@today`` tag if startdate is today; the TaskPaper theme now
   marks all tasks with the ``@today`` tag (supporting the MYN system
   from Michael Linenberger) in orange
-  ``@done`` now uses the user-supplied date and does not overwrite it
-  fixed a bug with function responsible for removing old tags
   (@overdue, @duesoon)

Version 1.3.6
~~~~~~~~~~~~~

-  added support for new tag ``@SOC`` (significant outcome; see MYN from
   Michael Linenberger); will now sort before high prio tasks
-  added new TaskPaper theme; ``@SOC`` is marked blue, ``@prio(low)`` is
   marked light gray
-  added sanity check for taskline; detects now mismatching round
   brackets and flags this as error

Version 1.3.5
~~~~~~~~~~~~~

-  Implemented request #14; if ``sendmail`` or ``pushover`` are set to
   False, the other parameters in the respective config section can be
   empty

Version 1.3.0
~~~~~~~~~~~~~

-  Support for Python 3.4
-  switched from xhtml2pdf to weasyprint for PDF generation
-  use jinja2 template for html generation
-  some smaller bugfixes

Version 1.2.0
~~~~~~~~~~~~~

-  Support for notes: each task can now have 1-n note lines
-  tasks with notes now automatically get the tag ``@note``
-  added inline docs for sphinx
-  added example config file
-  removed global variables
-  some refactoring

Version 1.1.0
~~~~~~~~~~~~~

-  Moved from namedTuples to sqlite3 in-memory database
-  prepared support for multiline tasks (a task line with multiple
   comment lines)
-  bugfix: @repeat only considered 1st digit of repeat interval; now
   support multi-digits
-  more tests
-  some refactoring

Version 1.0.0
~~~~~~~~~~~~~

-  Added review mode
-  Added proper command line syntax
-  enhanced config file
-  heavy refactoring and bug fixing

Version 0.9.0
~~~~~~~~~~~~~

-  released after several bugfixes and heavy refactoring
-  version 1.0.0 will include review mode
-  internal: included tests, Travis CI, coveralls.io ...

.. |Build Status| image:: https://travis-ci.org/mhofherr/TaskPaperManager.svg?branch=develop
   :target: https://travis-ci.org/mhofherr/TaskPaperManager
.. |Coverage Status| image:: https://coveralls.io/repos/mhofherr/TaskPaperManager/badge.png?branch=develop
   :target: https://coveralls.io/r/mhofherr/TaskPaperManager?branch=develop
