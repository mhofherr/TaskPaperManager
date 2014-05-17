import pytest
from pytest import fixture
from collections import namedtuple
import tpm.tpm

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


@fixture
def createFlagList():
    flaglist = []
    flaglist.append(Flagged(
        2, '2888-12-31', 'home', '   - testtask4 @prio(medium) @start(2999-12-31) @due(2999-12-31) @overdue',
        True, False, '2w', '2999-12-31', True, False, False,
    ))
    flaglist.append(Flagged(
        2, '2999-12-31', 'home', '   - testtask3 @prio(medium) @start(2999-12-31) @due(2999-12-31) @overdue',
        True, False, '2w', '2999-12-31', True, False, False,
    ))
    flaglist.append(Flagged(
        1, '2888-12-31', 'home', '   - testtask2 @prio(high) @start(2999-12-31) @due(2999-12-31) @duesoon',
        True, False, '2w', '2999-12-31', True, False, False,
    ))
    flaglist.append(Flagged(
        1, '2999-12-31', 'home', '   - testtask1 @prio(high) @start(2999-12-31) @due(2999-12-31) @duesoon',
        True, False, '2w', '2999-12-31', True, False, False,
    ))
    return flaglist


def test_removeTags1():
    flaglist = createFlagList()
    flaglist = tpm.tpm.removeTags(flaglist)
    for task in flaglist:
        assert '@duesoon' not in task.taskline


def test_removeTags2():
    flaglist = createFlagList()
    flaglist = tpm.tpm.removeTags(flaglist)
    for task in flaglist:
        assert '@overdue' not in task.taskline


def test_removeTags3():
    flaglist = []
    flaglist.append(Flagged(
        1, '2999-12-31', 'home', '   - testtask @prio(high) @start(2999-12-31) @due(2999-12-31)',
        True, False, '2w', '2999-12-31', False, False, False,
    ))
    flaglist = tpm.tpm.removeTags(flaglist)
    for task in flaglist:
        assert '@overdue' not in task.taskline
        assert '@duesoon' not in task.taskline


def test_removeTaskParts1():
    taskstring = tpm.tpm.removeTaskParts('testtask @start(2999-12-31) @prio(medium) @overdue', '@overdue')
    assert '@overdue' not in taskstring


def test_removeTaskParts2():
    taskstring = tpm.tpm.removeTaskParts('testtask @start(2999-12-31) @prio(medium) @overdue', '@')
    assert taskstring.strip() == 'testtask'


def test_filterWhitespaces():
    flaglist = []
    flaglist.append(Flagged(
        1, '2999-12-31', 'home', '   - testtask @prio(high)    @start(2999-12-31)     @due(2999-12-31)    @duesoon',
        True, False, '2w', '2999-12-31', True, False, False,
    ))
    flaglist = tpm.tpm.filterWhitespaces(flaglist)
    for task in flaglist:
        assert task.taskline == '- testtask @prio(high) @start(2999-12-31) @due(2999-12-31) @duesoon'


def test_SetTags1():
    flaglist = []
    flaglist.append(Flagged(
        1, '2999-12-31', 'home', '- testtask @prio(high) @start(2999-12-31) @due(2999-12-31) @duesoon',
        True, False, '2w', '2999-12-31', True, False, False,
    ))
    flaglist = tpm.tpm.setTags(flaglist)
    for task in flaglist:
        assert '@duesoon' in task.taskline


def test_SetTags2():
    flaglist = []
    flaglist.append(Flagged(
        1, '2999-12-31', 'home', '   - testtask @prio(high)    @start(2999-12-31)     @due(2999-12-31)',
        True, False, '2w', '2999-12-31', False, True, False,
    ))
    flaglist = tpm.tpm.setTags(flaglist)
    for task in flaglist:
        assert '@overdue' in task.taskline


def test_SetTags3():
    flaglist = []
    flaglist.append(Flagged(
        1, '2999-12-31', 'home', '- testtask @prio(high) @start(2999-12-31) @due(2999-12-31)',
        True, False, '2w', '2999-12-31', False, False, False,
    ))
    flaglist = tpm.tpm.setTags(flaglist)
    for task in flaglist:
        assert '@overdue' not in task.taskline
        assert '@duesoon' not in task.taskline


def test_sortList1():
    flaglist = createFlagList()
    flaglist = tpm.tpm.sortList(flaglist)
    i = 1
    for task in flaglist:
        if i == 1:
            assert 'testtask1' in task.taskline
        elif i == 2:
            assert 'testtask2' in task.taskline
        elif i == 3:
            assert 'testtask3' in task.taskline
        elif i == 4:
            assert 'testtask4' in task.taskline
        i = i+1

if __name__ == '__main__':
    pytest.main()
