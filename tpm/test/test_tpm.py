import pytest
from pytest import fixture
import sqlite3
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import tpm.tpm



@fixture
def my_initDB():
    mycon = tpm.tpm.initDB()
    return mycon


def test_initDB():
    mycon = my_initDB()
    cursel = mycon.cursor()
    cursel.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='tasks'")
    for row in cursel:
        assert row[0] == 1
    #assert cursel.fetchone() == 1
    cursel.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='comments'")
    #assert cursel.fetchone() == 1
    for row in cursel:
        assert row[0] == 1


def test_removeTags1():
    mycon = my_initDB()
    cursel = mycon.cursor()
    curin = mycon.cursor()
    curin.execute("insert into tasks (prio, startdate, project, taskline, done,\
        repeat, repeatinterval, duedate, duesoon, overdue, maybe) values\
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ( 1, '2999-12-31', 'home', '- testtask @prio(high) @start(2999-12-31) @duesoon', 0, 0,
        '-', '2999-12-31', 1, 0, 0))
    mycon.commit()
    tpm.tpm.removeTags(mycon)
    cursel.execute("SELECT taskline FROM tasks")
    for row in cursel:
        assert '@duesoon' not in row[0]


def test_removeTags2():
    mycon = my_initDB()
    cursel = mycon.cursor()
    curin = mycon.cursor()
    curin.execute("insert into tasks (prio, startdate, project, taskline, done,\
        repeat, repeatinterval, duedate, duesoon, overdue, maybe) values\
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ( 1, '2999-12-31', 'home', '- testtask @prio(high) @start(2999-12-31) @overdue', 0, 0,
        '-', '2999-12-31', 0, 1, 0))
    mycon.commit()
    tpm.tpm.removeTags(mycon)
    cursel.execute("SELECT taskline FROM tasks")
    for row in cursel:
        assert '@overdue' not in row[0]


def test_removeTags3():
    mycon = my_initDB()
    cursel = mycon.cursor()
    curin = mycon.cursor()
    curin.execute("insert into tasks (prio, startdate, project, taskline, done,\
        repeat, repeatinterval, duedate, duesoon, overdue, maybe) values\
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ( 1, '2999-12-31', 'home', '- testtask @prio(high) @start(2999-12-31)', 0, 0,
        '-', '2999-12-31', 0, 0, 0))
    mycon.commit()
    tpm.tpm.removeTags(mycon)
    cursel.execute("SELECT taskline FROM tasks")
    for row in cursel:
        assert '@overdue' not in row[0]
        assert '@duesoon' not in row[0]


def test_removeTaskParts1():
    taskstring = tpm.tpm.removeTaskParts('testtask @start(2999-12-31) @prio(medium) @overdue', '@overdue')
    assert '@overdue' not in taskstring


def test_removeTaskParts2():
    taskstring = tpm.tpm.removeTaskParts('testtask @start(2999-12-31) @prio(medium) @overdue', '@')
    assert taskstring.strip() == 'testtask'


def test_filterWhitespaces():
    mycon = my_initDB()
    cursel = mycon.cursor()
    curin = mycon.cursor()
    curin.execute("insert into tasks (prio, startdate, project, taskline, done,\
        repeat, repeatinterval, duedate, duesoon, overdue, maybe) values\
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ( 1, '2999-12-31', 'home', '   -      testtask        @prio(high)      @start(2999-12-31)      @overdue', 0, 0,
        '-', '2999-12-31', 0, 1, 0))
    mycon.commit()
    tpm.tpm.filterWhitespaces(mycon)
    cursel.execute("SELECT taskline FROM tasks")
    for row in cursel:
        assert row[0] == '- testtask @prio(high) @start(2999-12-31) @overdue'


def test_SetTags1():
    mycon = my_initDB()
    cursel = mycon.cursor()
    curin = mycon.cursor()
    curin.execute("insert into tasks (prio, startdate, project, taskline, done,\
        repeat, repeatinterval, duedate, duesoon, overdue, maybe) values\
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ( 1, '2999-12-31', 'home', '- testtask @prio(high) @start(2999-12-31)', 0, 0,
        '-', '2999-12-31', 1, 0, 0))
    mycon.commit()
    tpm.tpm.setTags(mycon)
    cursel.execute("SELECT taskline FROM tasks")
    for row in cursel:
        assert '@duesoon' in row[0]


def test_SetTags2():
    mycon = my_initDB()
    cursel = mycon.cursor()
    curin = mycon.cursor()
    curin.execute("insert into tasks (prio, startdate, project, taskline, done,\
        repeat, repeatinterval, duedate, duesoon, overdue, maybe) values\
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ( 1, '2999-12-31', 'home', '- testtask @prio(high) @start(2999-12-31)', 0, 0,
        '-', '2999-12-31', 0, 1, 0))
    mycon.commit()
    tpm.tpm.setTags(mycon)
    cursel.execute("SELECT taskline FROM tasks")
    for row in cursel:
        assert '@overdue' in row[0]


def test_SetTags3():
    mycon = my_initDB()
    cursel = mycon.cursor()
    curin = mycon.cursor()
    curin.execute("insert into tasks (prio, startdate, project, taskline, done,\
        repeat, repeatinterval, duedate, duesoon, overdue, maybe) values\
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ( 1, '2999-12-31', 'home', '- testtask @prio(high) @start(2999-12-31)', 0, 0,
        '-', '2999-12-31', 0, 0, 0))
    mycon.commit()
    tpm.tpm.setTags(mycon)
    cursel.execute("SELECT taskline FROM tasks")
    for row in cursel:
        assert '@overdue' not in row[0]
        assert '@duesoon' not in row[0]


def test_parseArgs():
    (myinfile, myconfigfile, mymode) = tpm.tpm.parseArgs(['-i', 'myinfile', '-c', 'myconfigfile', '-m', 'review'])
    assert myinfile == 'myinfile'
    assert myconfigfile == 'myconfigfile'
    assert mymode == 'review'


def test_setrepeat():
    mycon = my_initDB()
    cursel = mycon.cursor()
    curin = mycon.cursor()
    TODAY = datetime.date(datetime.now())
    DAYS2 = TODAY - timedelta(days=2)
    WEEKS10 = TODAY - timedelta(weeks=10)
    MONTH24 = TODAY - relativedelta(months=24)

    curin.execute("insert into tasks (prio, startdate, project, taskline, done,\
        repeat, repeatinterval, duedate, duesoon, overdue, maybe) values\
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ( 1, DAYS2, 'Repeat', '    - testtask1 @prio(high) @repeat(2d) @work @start({0})'.format(DAYS2), 0, 1,
        '2d', '2999-12-31', 0, 0, 0))
    curin.execute("insert into tasks (prio, startdate, project, taskline, done,\
        repeat, repeatinterval, duedate, duesoon, overdue, maybe) values\
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ( 2, WEEKS10, 'Repeat', '    - testtask2 @prio(medium) @repeat(10w) @work @start({0})'.format(WEEKS10), 0, 1,
        '2d', '2999-12-31', 0, 0, 0))
    curin.execute("insert into tasks (prio, startdate, project, taskline, done,\
        repeat, repeatinterval, duedate, duesoon, overdue, maybe) values\
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ( 3, MONTH24, 'Repeat', '    - testtask3 @prio(low) @repeat(24m) @work @start({0})'.format(MONTH24), 0, 1,
        '2d', '2999-12-31', 0, 0, 0))
    mycon.commit()
    tpm.tpm.setRepeat(mycon)
    #cursel.execute("SELECT taskline FROM tasks where project = 'Repeat'")
    #for row in cursel:
    #    assert '@start({0})'.format(TODAY) in row[0]
    cursel.execute("SELECT count(*) FROM tasks where project = 'Repeat'")
    for row in cursel:
        assert row[0] == 3
    cursel.execute("SELECT count(*) FROM tasks where project = 'work'")
    for row in cursel:
        assert row[0] == 3


def test_parseConfig():
    mytext = ""
    mytext = mytext + "[tpm]\n"
    mytext = mytext + "debug: True\n"
    mytext = mytext + "duedelta: days\n"
    mytext = mytext + "dueinterval: 3\n"
    mytext = mytext + "\n"
    mytext = mytext + "[mail]\n"
    mytext = mytext + "sendmail: False\n"
    mytext = mytext + "sendmailhome: True\n"
    mytext = mytext + "sendmailwork:  False\n"
    mytext = mytext + "smtpserver: mail.user.test\n"
    mytext = mytext + "smtpport: 587\n"
    mytext = mytext + "smtpuser: user\n"
    mytext = mytext + "smtppassword: password\n"
    mytext = mytext + "sourceemail: source@test.de\n"
    mytext = mytext + "destworkemail: destwork@test.de\n"
    mytext = mytext + "desthomeemail: desthome@test.de\n"
    mytext = mytext + "encryptmail: True\n"
    mytext = mytext + "gnupghome: /Users/user/.gnupg\n"
    mytext = mytext + "targetfingerprint: 1234567890\n"
    mytext = mytext + "\n"
    mytext = mytext + "[pushover]\n"
    mytext = mytext + "pushover: False\n"
    mytext = mytext + "pushoverhome: True\n"
    mytext = mytext + "pushoverwork: False\n"
    mytext = mytext + "pushovertoken: 2345678901\n"
    mytext = mytext + "pushoveruser: 3456789012\n"
    mytext = mytext + "\n"
    mytext = mytext + "[review]\n"
    mytext = mytext + "reviewwork: True\n"
    mytext = mytext + "reviewhome: True\n"
    mytext = mytext + "outputpdf: True\n"
    mytext = mytext + "outputhtml: True\n"
    mytext = mytext + "outputmd: True\n"
    mytext = mytext + "reviewpath: /Users/user/review/\n"
    mytext = mytext + "reviewagenda: True\n"
    mytext = mytext + "reviewprojects: True\n"
    mytext = mytext + "reviewcustomers: True\n"
    mytext = mytext + "reviewwaiting: True\n"
    mytext = mytext + "\n"

    tpm.tpm.myFile(mytext, '/tmp/test.cfg', 'w')
    (DEBUG, SENDMAIL, SENDMAILHOME, SENDMAILWORK, SMTPSERVER, SMTPPORT,
    SMTPUSER, SMTPPASSWORD, PUSHOVER, DUEDELTA, DUEINTERVAL, ENCRYPTMAIL,
    GNUPGHOME, PUSHOVERTOKEN, PUSHOVERUSER, TARGETFINGERPRINT, SOURCEEMAIL,
    DESTHOMEEMAIL, DESTWORKEMAIL, REVIEWPATH, REVIEWAGENDA, REVIEWPROJECTS,
    REVIEWCUSTOMERS, REVIEWWAITING, REVIEWOUTPUTPDF, REVIEWOUTPUTHTML,
    REVIEWOUTPUTMD, REVIEWHOME, REVIEWWORK, PUSHOVERHOME, PUSHOVERWORK) = tpm.tpm.parseConfig('/tmp/test.cfg')

    assert DEBUG is True
    assert SENDMAIL is False
    assert SENDMAILHOME is True
    assert SENDMAILWORK is False
    assert SMTPSERVER == 'mail.user.test'
    assert SMTPPORT == 587
    assert SMTPUSER == 'user'
    assert SMTPPASSWORD == 'password'
    assert PUSHOVER is False
    assert DUEDELTA == 'days'
    assert DUEINTERVAL == 3
    assert ENCRYPTMAIL is True
    assert GNUPGHOME == '/Users/user/.gnupg'
    assert PUSHOVERTOKEN == '2345678901'
    assert PUSHOVERUSER == '3456789012'
    assert TARGETFINGERPRINT == '1234567890'
    assert SOURCEEMAIL == 'source@test.de'
    assert DESTHOMEEMAIL == 'desthome@test.de'
    assert DESTWORKEMAIL == 'destwork@test.de'
    assert REVIEWPATH == '/Users/user/review/'
    assert REVIEWAGENDA is True
    assert REVIEWPROJECTS is True
    assert REVIEWCUSTOMERS is True
    assert REVIEWWAITING is True
    assert REVIEWOUTPUTPDF is True
    assert REVIEWOUTPUTHTML is True
    assert REVIEWOUTPUTMD is True
    assert REVIEWHOME is True
    assert REVIEWWORK is True
    assert PUSHOVERHOME is True
    assert PUSHOVERWORK is False


if __name__ == '__main__':
    pytest.main()
