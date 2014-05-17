import pytest
from pytest import fixture
from collections import namedtuple
import TaskPaperParser.tpp

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
        1, '2999-12-31', 'home', '   - testtask @prio(high) @start(2999-12-31) @due(2999-12-31) @duesoon',
        True, False, '2w', '2999-12-31', True, False, False,
    ))
    flaglist.append(Flagged(
        2, '2999-12-31', 'home', '   - testtask @prio(medium) @start(2999-12-31) @due(2999-12-31) @overdue',
        True, False, '2w', '2999-12-31', True, False, False,
    ))
    return flaglist


def test_removeTagsDueSoon():
    flaglist = createFlagList()
    flaglist = TaskPaperParser.tpp.removeTags(flaglist)
    for task in flaglist:
        if '@duesoon' in task.taskline:
            assert True == False
        else:
            assert True == True


def test_removeTagsOverDue():
    flaglist = createFlagList()
    flaglist = TaskPaperParser.tpp.removeTags(flaglist)
    for task in flaglist:
        if '@overdue' in task.taskline:
            assert True == False
        else:
            assert True == True


def test_removeTaskParts1():
    taskstring = TaskPaperParser.tpp.removeTaskParts('testtask @start(2999-12-31) @prio(medium) @overdue', '@overdue')
    if '@overdue' in taskstring:
        assert True == False
    else:
        assert True == True


def test_removeTaskParts2():
    taskstring = TaskPaperParser.tpp.removeTaskParts('testtask @start(2999-12-31) @prio(medium) @overdue', '@')
    if taskstring.strip() != 'testtask':
        assert True == False
    else:
        assert True == True


if __name__ == '__main__':
    pytest.main()
