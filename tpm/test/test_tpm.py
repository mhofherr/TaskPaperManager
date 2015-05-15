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
    cursel.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='notes'")
    #assert cursel.fetchone() == 1
    for row in cursel:
        assert row[0] == 1


def test_removeTags1():
    mycon = my_initDB()
    cursel = mycon.cursor()
    curin = mycon.cursor()
    curin.execute("insert into tasks (prio, startdate, project, taskline, done,\
        repeat, repeatinterval, duedate, duesoon, overdue, maybe, today) values\
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ( 1, '2999-12-31', 'home', '- testtask @prio(high) @start(2999-12-31) @duesoon', 0, 0,
        '-', '2999-12-31', 1, 0, 0, 0))
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
        repeat, repeatinterval, duedate, duesoon, overdue, maybe, today) values\
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ( 1, '2999-12-31', 'home', '- testtask @prio(high) @start(2999-12-31) @overdue', 0, 0,
        '-', '2999-12-31', 0, 1, 0, 0))
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
        repeat, repeatinterval, duedate, duesoon, overdue, maybe, today) values\
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ( 1, '2999-12-31', 'home', '- testtask @prio(high) @start(2999-12-31)', 0, 0,
        '-', '2999-12-31', 0, 0, 0, 0))
    mycon.commit()
    tpm.tpm.removeTags(mycon)
    cursel.execute("SELECT taskline FROM tasks")
    for row in cursel:
        assert '@overdue' not in row[0]
        assert '@duesoon' not in row[0]


def test_removeTags4():
    mycon = my_initDB()
    cursel = mycon.cursor()
    curin = mycon.cursor()
    curin.execute("insert into tasks (prio, startdate, project, taskline, done,\
        repeat, repeatinterval, duedate, duesoon, overdue, maybe, today) values\
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ( 1, '2999-12-31', 'home', '- testtask @prio(high) @start(2999-12-31) @today', 0, 0,
        '-', '2999-12-31', 0, 1, 0, 1))
    mycon.commit()
    tpm.tpm.removeTags(mycon)
    cursel.execute("SELECT taskline FROM tasks")
    for row in cursel:
        assert '@today' not in row[0]


def test_removeTaskParts1():
    taskstring = tpm.tpm.removeTaskParts('testtask @start(2999-12-31) @prio(medium) @overdue', '@overdue')
    assert '@overdue' not in taskstring


def test_removeTaskParts2():
    taskstring = tpm.tpm.removeTaskParts('testtask @start(2999-12-31) @prio(medium) @overdue', '@')
    assert taskstring.strip() == 'testtask'


# def test_sanitizer1():
#     mycon = my_initDB()
#     cursel = mycon.cursor()
#     curin = mycon.cursor()
#     curin.execute("insert into tasks (prio, startdate, project, taskline, done,\
#         repeat, repeatinterval, duedate, duesoon, overdue, maybe) values\
#         (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
#         ( 1, '2999-12-31', 'home', '   -      testtask        @prio(high)      @start(2999-12-31)      @overdue', 0, 0,
#         '-', '2999-12-31', 0, 1, 0))
#     mycon.commit()
#     tpm.tpm.sanitizer(mycon)
#     cursel.execute("SELECT taskline FROM tasks")
#     for row in cursel:
#         assert row[0] == '- testtask @prio(high) @start(2999-12-31) @overdue'


# def test_sanitizer2():
#     mycon = my_initDB()
#     cursel = mycon.cursor()
#     curin = mycon.cursor()
#     curin.execute("insert into tasks (prio, startdate, project, taskline, done,\
#         repeat, repeatinterval, duedate, duesoon, overdue, maybe) values\
#         (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
#         ( 1, '2999-12-31', 'home', '- testtask @start(2999-12-31)', 0, 0,
#         '-', '2999-12-31', 0, 1, 0))
#     curin.execute("insert into tasks (prio, startdate, project, taskline, done,\
#         repeat, repeatinterval, duedate, duesoon, overdue, maybe) values\
#         (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
#         ( 1, '2999-12-31', 'home', '- testtask @prio(medium)', 0, 0,
#         '-', '2999-12-31', 0, 1, 0))
#     curin.execute("insert into tasks (prio, startdate, project, taskline, done,\
#         repeat, repeatinterval, duedate, duesoon, overdue, maybe) values\
#         (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
#         ( 1, '2999-12-31', 'home', '- testtask @duesoon', 0, 0,
#         '-', '2999-12-31', 0, 1, 0))
#     mycon.commit()
#     tpm.tpm.sanitizer(mycon)
#     cursel.execute("SELECT count(*) FROM tasks where project='Error'")
#     for row in cursel:
#         assert row[0] == 3


# def test_sanitizer3():
#     mycon = my_initDB()
#     cursel = mycon.cursor()
#     curin = mycon.cursor()
#     curin.execute("insert into tasks (prio, startdate, project, taskline, done,\
#         repeat, repeatinterval, duedate, duesoon, overdue, maybe) values\
#         (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
#         ( 1, '2999-12-31', 'home', '- testtask @repeat(2w) @prio(medium) @start(2999-12-31) @work', 0, 0,
#         '-', '2999-12-31', 0, 1, 0))
#     curin.execute("insert into tasks (prio, startdate, project, taskline, done,\
#         repeat, repeatinterval, duedate, duesoon, overdue, maybe) values\
#         (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
#         ( 1, '2999-12-31', 'home', '- testtask @repeat(2w) @prio(medium) @start(2999-12-31) @home', 0, 0,
#         '-', '2999-12-31', 0, 1, 0))
#     mycon.commit()
#     tpm.tpm.sanitizer(mycon)
#     cursel.execute("SELECT count(*) FROM tasks where project='Error'")
#     for row in cursel:
#         assert row[0] == 0


# def test_sanitizer4():
#     mycon = my_initDB()
#     cursel = mycon.cursor()
#     curin = mycon.cursor()
#     curin.execute("insert into tasks (prio, startdate, project, taskline, done,\
#         repeat, repeatinterval, duedate, duesoon, overdue, maybe) values\
#         (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
#         ( 1, '2999-12-31', 'Repeat', '- testtask @repeat(2w) @prio(medium) @start(2999-12-31)', 0, 0,
#         '-', '2999-12-31', 0, 1, 0))
#     curin.execute("insert into tasks (prio, startdate, project, taskline, done,\
#         repeat, repeatinterval, duedate, duesoon, overdue, maybe) values\
#         (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
#         ( 1, '2999-12-31', 'Repeat', '- testtask @repeat(2w) @prio(medium) @work', 0, 0,
#         '-', '2999-12-31', 0, 1, 0))
#     curin.execute("insert into tasks (prio, startdate, project, taskline, done,\
#         repeat, repeatinterval, duedate, duesoon, overdue, maybe) values\
#         (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
#         ( 1, '2999-12-31', 'Repeat', '- testtask @repeat(2w) @start(2999-12-31) @work', 0, 0,
#         '-', '2999-12-31', 0, 1, 0))
#     curin.execute("insert into tasks (prio, startdate, project, taskline, done,\
#         repeat, repeatinterval, duedate, duesoon, overdue, maybe) values\
#         (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
#         ( 1, '2999-12-31', 'Repeat', '- testtask @start(2999-12-31) @prio(medium) @work', 0, 0,
#         '-', '2999-12-31', 0, 1, 0))
#     mycon.commit()
#     tpm.tpm.sanitizer(mycon)
#     cursel.execute("SELECT count(*) FROM tasks where project='Error'")
#     for row in cursel:
#         assert row[0] == 4


def test_SetTags1():
    mycon = my_initDB()
    cursel = mycon.cursor()
    curin = mycon.cursor()
    curin.execute("insert into tasks (prio, startdate, project, taskline, done,\
        repeat, repeatinterval, duedate, duesoon, overdue, maybe, today) values\
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ( 1, '2999-12-31', 'home', '- testtask @prio(high) @start(2999-12-31)', 0, 0,
        '-', '2999-12-31', 1, 0, 0, 0))
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
        repeat, repeatinterval, duedate, duesoon, overdue, maybe, today) values\
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ( 1, '2999-12-31', 'home', '- testtask @prio(high) @start(2999-12-31)', 0, 0,
        '-', '2999-12-31', 0, 1, 0, 0))
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
        repeat, repeatinterval, duedate, duesoon, overdue, maybe, today) values\
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ( 1, '2999-12-31', 'home', '- testtask @prio(high) @start(2999-12-31)', 0, 0,
        '-', '2999-12-31', 0, 0, 0, 0))
    mycon.commit()
    tpm.tpm.setTags(mycon)
    cursel.execute("SELECT taskline FROM tasks")
    for row in cursel:
        assert '@overdue' not in row[0]
        assert '@duesoon' not in row[0]


def test_SetTags4():
    mycon = my_initDB()
    cursel = mycon.cursor()
    curin = mycon.cursor()
    curin.execute("insert into tasks (prio, startdate, project, taskline, done,\
        repeat, repeatinterval, duedate, duesoon, overdue, maybe, today) values\
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ( 1, '2999-12-31', 'home', '- testtask @prio(high) @start(2999-12-31)', 0, 0,
        '-', '2999-12-31', 0, 1, 0, 1))
    mycon.commit()
    tpm.tpm.setTags(mycon)
    cursel.execute("SELECT taskline FROM tasks")
    for row in cursel:
        assert '@today' in row[0]


def test_parseArgs1():
    (myinfile, myconfigfile, mymode, backup) = tpm.tpm.parseArgs(['-i', 'myinfile', '-c', 'myconfigfile', '-m', 'review'])
    assert myinfile == 'myinfile'
    assert myconfigfile == 'myconfigfile'
    assert mymode == 'review'


def test_parseArgs2():
    (myinfile, myconfigfile, mymode, backup) = tpm.tpm.parseArgs(['-i', 'myinfile', '-c', 'myconfigfile', '-m', 'daily'])
    assert myinfile == 'myinfile'
    assert myconfigfile == 'myconfigfile'
    assert mymode == 'daily'


def test_setrepeat():
    mycon = my_initDB()
    cursel = mycon.cursor()
    curin = mycon.cursor()
    TODAY = datetime.date(datetime.now())
    DAYS2 = TODAY - timedelta(days=2)
    WEEKS10 = TODAY - timedelta(weeks=10)
    MONTH24 = TODAY - relativedelta(months=24)

    curin.execute("insert into tasks (prio, startdate, project, taskline, done,\
        repeat, repeatinterval, duedate, duesoon, overdue, maybe, today) values\
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ( 1, DAYS2, 'Repeat', '    - testtask1 @prio(high) @repeat(2d) @project(work) @start({0})'.format(DAYS2), 0, 1,
        '2d', '2999-12-31', 0, 0, 0, 0))
    curin.execute("insert into tasks (prio, startdate, project, taskline, done,\
        repeat, repeatinterval, duedate, duesoon, overdue, maybe, today) values\
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ( 2, WEEKS10, 'Repeat', '    - testtask2 @prio(medium) @repeat(10w) @project(work) @start({0})'.format(WEEKS10), 0, 1,
        '2d', '2999-12-31', 0, 0, 0, 0))
    curin.execute("insert into tasks (prio, startdate, project, taskline, done,\
        repeat, repeatinterval, duedate, duesoon, overdue, maybe, today) values\
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ( 3, MONTH24, 'Repeat', '    - testtask3 @prio(low) @repeat(24m) @project(work) @start({0})'.format(MONTH24), 0, 1,
        '2d', '2999-12-31', 0, 0, 0, 0))
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


# def test_settings():
#     mytext = ""
#     mytext = mytext + "[tpm]\n"
#     mytext = mytext + "debug: True\n"
#     mytext = mytext + "duedelta: days\n"
#     mytext = mytext + "dueinterval: 3\n"
#     mytext = mytext + "\n"
#     mytext = mytext + "[mail]\n"
#     mytext = mytext + "sendmail: True\n"
#     mytext = mytext + "smtpserver: mail.user.test\n"
#     mytext = mytext + "smtpport: 587\n"
#     mytext = mytext + "smtpuser: user\n"
#     mytext = mytext + "smtppassword: password\n"
#     mytext = mytext + "sourceemail: source@test.de\n"
#     mytext = mytext + "destemail: dest@test.de\n"
#     mytext = mytext + "encryptmail: True\n"
#     mytext = mytext + "gnupghome: /Users/user/.gnupg\n"
#     mytext = mytext + "targetfingerprint: 1234567890\n"
#     mytext = mytext + "\n"
#     mytext = mytext + "[pushover]\n"
#     mytext = mytext + "pushover: True\n"
#     mytext = mytext + "pushovertoken: 2345678901\n"
#     mytext = mytext + "pushoveruser: 3456789012\n"
#     mytext = mytext + "\n"
#     mytext = mytext + "[review]\n"
#     mytext = mytext + "outputpdf: True\n"
#     mytext = mytext + "outputhtml: True\n"
#     mytext = mytext + "outputmd: True\n"
#     mytext = mytext + "reviewpath: /Users/user/review/\n"
#     mytext = mytext + "reviewagenda: True\n"
#     mytext = mytext + "reviewprojects: True\n"
#     mytext = mytext + "reviewcustomers: True\n"
#     mytext = mytext + "reviewwaiting: True\n"
#     mytext = mytext + "reviewmaybe: True\n"
#     mytext = mytext + "\n"

#     tpm.tpm.myFile(mytext, '/tmp/test.cfg', 'w')
#     sett = tpm.tpm.settings('/tmp/test.cfg')

#     assert sett.debug is True
#     assert sett.sendmail is True
#     assert sett.smtpserver == 'mail.user.test'
#     assert sett.smtpport == 587
#     assert sett.smtpuser == 'user'
#     assert sett.smtppassword == 'password'
#     assert sett.pushover is True
#     assert sett.duedelta == 'days'
#     assert sett.dueinterval == 3
#     assert sett.encryptmail is True
#     assert sett.gnupghome == '/Users/user/.gnupg'
#     assert sett.pushovertoken == '2345678901'
#     assert sett.pushoveruser == '3456789012'
#     assert sett.targetfingerprint == '1234567890'
#     assert sett.sourceemail == 'source@test.de'
#     assert sett.destemail == 'dest@test.de'
#     assert sett.reviewpath == '/Users/user/review/'
#     assert sett.reviewagenda is True
#     assert sett.reviewprojects is True
#     assert sett.reviewcustomers is True
#     assert sett.reviewwaiting is True
#     assert sett.reviewmaybe is True
#     assert sett.reviewoutputpdf is True
#     assert sett.reviewoutputhtml is True
#     assert sett.reviewoutputmd is True


def test_usage(capsys):
    tpm.tpm.usage()
    out, err = capsys.readouterr()
    assert out == 'tpm.py -i <inputfile> -c <configfile> -m <mode:daily|review>\noptional: -b to backup the todo-file before modifying it\n'


def test_printDebugOutput(capsys):
    mycon = my_initDB()
    curin = mycon.cursor()
    curin.execute("insert into tasks (prio, startdate, project, taskline, done,\
        repeat, repeatinterval, duedate, duesoon, overdue, maybe, today) values\
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ( 1, '2d', 'work', '- testtask1 @prio(high) @repeat(2d) @work @start(2999-12-31)', 0, 1,
        '2d', '2999-12-31', 0, 0, 0, 0))
    mycon.commit()
    tpm.tpm.printDebugOutput(mycon, 'test')
    out, err = capsys.readouterr()
    assert out == 'test: 1 | 2d | work | - testtask1 @prio(high) @repeat(2d) @work @start(2999-12-31) | 0 | 1 | 2d | 2999-12-31 | 0 | 0 | 0 | 0\n'

if __name__ == '__main__':
    pytest.main()
