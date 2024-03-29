import time
import pytest
from unittest.mock import Mock, patch


@pytest.fixture
def refresher():
    from mzcli.completion_refresher import CompletionRefresher

    return CompletionRefresher()


def test_ctor(refresher):
    """
    Refresher object should contain a few handlers
    :param refresher:
    :return:
    """
    assert len(refresher.refreshers) > 0
    actual_handlers = list(refresher.refreshers.keys())
    expected_handlers = [
        "schemata",
        "tables",
        "sources",
        "views",
        "types",
        "databases",
        "casing",
        "functions",
    ]
    assert expected_handlers == actual_handlers


def test_refresh_called_once(refresher):
    """

    :param refresher:
    :return:
    """
    callbacks = Mock()
    pgexecute = Mock(**{"is_virtual_database.return_value": False})
    special = Mock()

    with patch.object(refresher, "_bg_refresh") as bg_refresh:
        actual = refresher.refresh(pgexecute, special, callbacks)
        time.sleep(1)  # Wait for the thread to work.
        assert len(actual) == 1
        assert len(actual[0]) == 4
        assert actual[0][3] == "Auto-completion refresh started in the background."
        bg_refresh.assert_called_with(pgexecute, special, callbacks, None, None)


def test_refresh_called_twice(refresher):
    """
    If refresh is called a second time, it should be restarted
    :param refresher:
    :return:
    """
    callbacks = Mock()

    pgexecute = Mock(**{"is_virtual_database.return_value": False})
    special = Mock()

    def dummy_bg_refresh(*args):
        time.sleep(3)  # seconds

    refresher._bg_refresh = dummy_bg_refresh

    actual1 = refresher.refresh(pgexecute, special, callbacks)
    time.sleep(1)  # Wait for the thread to work.
    assert len(actual1) == 1
    assert len(actual1[0]) == 4
    assert actual1[0][3] == "Auto-completion refresh started in the background."

    actual2 = refresher.refresh(pgexecute, special, callbacks)
    time.sleep(1)  # Wait for the thread to work.
    assert len(actual2) == 1
    assert len(actual2[0]) == 4
    assert actual2[0][3] == "Auto-completion refresh restarted."


def test_refresh_with_callbacks(refresher):
    """
    Callbacks must be called
    :param refresher:
    """
    callbacks = [Mock()]
    pgexecute = Mock(**{"is_virtual_database.return_value": False})
    pgexecute.extra_args = {}
    special = Mock()

    # Set refreshers to 0: we're not testing refresh logic here
    refresher.refreshers = {}
    refresher.refresh(pgexecute, special, callbacks)
    time.sleep(1)  # Wait for the thread to work.
    assert callbacks[0].call_count == 1
