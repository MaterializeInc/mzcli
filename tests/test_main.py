import os
import platform
from unittest import mock

import pytest

try:
    import setproctitle
except ImportError:
    setproctitle = None

from mzcli.main import (
    obfuscate_process_password,
    format_output,
    PGCli,
    OutputSettings,
    COLOR_CODE_REGEX,
)
from mzcli.pgexecute import PGExecute
from pgspecial.main import PAGER_OFF, PAGER_LONG_OUTPUT, PAGER_ALWAYS
from utils import dbtest, run, mz_xfail
from collections import namedtuple


@pytest.mark.skipif(platform.system() == "Windows", reason="Not applicable in windows")
@pytest.mark.skipif(not setproctitle, reason="setproctitle not available")
def test_obfuscate_process_password():
    original_title = setproctitle.getproctitle()

    setproctitle.setproctitle("mzcli user=materialize password=secret host=localhost")
    obfuscate_process_password()
    title = setproctitle.getproctitle()
    expected = "mzcli user=materialize password=xxxx host=localhost"
    assert title == expected

    setproctitle.setproctitle(
        "mzcli user=materialize password=top secret host=localhost"
    )
    obfuscate_process_password()
    title = setproctitle.getproctitle()
    expected = "mzcli user=materialize password=xxxx host=localhost"
    assert title == expected

    setproctitle.setproctitle("mzcli user=materialize password=top secret")
    obfuscate_process_password()
    title = setproctitle.getproctitle()
    expected = "mzcli user=materialize password=xxxx"
    assert title == expected

    setproctitle.setproctitle("mzcli postgres://materialize:secret@localhost/db")
    obfuscate_process_password()
    title = setproctitle.getproctitle()
    expected = "mzcli postgres://materialize:xxxx@localhost/db"
    assert title == expected

    setproctitle.setproctitle(original_title)


def test_format_output():
    settings = OutputSettings(table_format="psql", dcmlfmt="d", floatfmt="g")
    results = format_output(
        "Title", [("abc", "def")], ["head1", "head2"], "test status", settings
    )
    expected = [
        "Title",
        "+-------+-------+",
        "| head1 | head2 |",
        "|-------+-------|",
        "| abc   | def   |",
        "+-------+-------+",
        "test status",
    ]
    assert list(results) == expected


def test_format_output_truncate_on():
    settings = OutputSettings(
        table_format="psql", dcmlfmt="d", floatfmt="g", max_field_width=10
    )
    results = format_output(
        None,
        [("first field value", "second field value")],
        ["head1", "head2"],
        None,
        settings,
    )
    expected = [
        "+------------+------------+",
        "| head1      | head2      |",
        "|------------+------------|",
        "| first f... | second ... |",
        "+------------+------------+",
    ]
    assert list(results) == expected


def test_format_output_truncate_off():
    settings = OutputSettings(
        table_format="psql", dcmlfmt="d", floatfmt="g", max_field_width=None
    )
    long_field_value = ("first field " * 100).strip()
    results = format_output(None, [(long_field_value,)], ["head1"], None, settings)
    lines = list(results)
    assert lines[3] == f"| {long_field_value} |"


@dbtest
@mz_xfail("casting from integer to bigint?")
def test_format_array_output(executor):
    statement = """
    SELECT
        array[1, 2, 3]::bigint[] as bigint_array,
        '{{1,2},{3,4}}'::numeric[] as nested_numeric_array,
        '{å,魚,текст}'::text[] as 配列
    UNION ALL
    SELECT '{}', NULL, array[NULL]
    """
    results = run(executor, statement)
    expected = [
        "+--------------+----------------------+--------------+",
        "| bigint_array | nested_numeric_array | 配列         |",
        "|--------------+----------------------+--------------|",
        "| {1,2,3}      | {{1,2},{3,4}}        | {å,魚,текст} |",
        "| {}           | <null>               | {<null>}     |",
        "+--------------+----------------------+--------------+",
        "SELECT 2",
    ]
    assert list(results) == expected


@dbtest
@mz_xfail("casting from integer to bigint?")
def test_format_array_output_expanded(executor):
    statement = """
    SELECT
        array[1, 2, 3]::bigint[] as bigint_array,
        '{{1,2},{3,4}}'::numeric[] as nested_numeric_array,
        '{å,魚,текст}'::text[] as 配列
    UNION ALL
    SELECT '{}', NULL, array[NULL]
    """
    results = run(executor, statement, expanded=True)
    expected = [
        "-[ RECORD 1 ]-------------------------",
        "bigint_array         | {1,2,3}",
        "nested_numeric_array | {{1,2},{3,4}}",
        "配列                   | {å,魚,текст}",
        "-[ RECORD 2 ]-------------------------",
        "bigint_array         | {}",
        "nested_numeric_array | <null>",
        "配列                   | {<null>}",
        "SELECT 2",
    ]
    assert "\n".join(results) == "\n".join(expected)


def test_format_output_auto_expand():
    settings = OutputSettings(
        table_format="psql", dcmlfmt="d", floatfmt="g", max_width=100
    )
    table_results = format_output(
        "Title", [("abc", "def")], ["head1", "head2"], "test status", settings
    )
    table = [
        "Title",
        "+-------+-------+",
        "| head1 | head2 |",
        "|-------+-------|",
        "| abc   | def   |",
        "+-------+-------+",
        "test status",
    ]
    assert list(table_results) == table
    expanded_results = format_output(
        "Title",
        [("abc", "def")],
        ["head1", "head2"],
        "test status",
        settings._replace(max_width=1),
    )
    expanded = [
        "Title",
        "-[ RECORD 1 ]-------------------------",
        "head1 | abc",
        "head2 | def",
        "test status",
    ]
    assert "\n".join(expanded_results) == "\n".join(expanded)


termsize = namedtuple("termsize", ["rows", "columns"])
test_line = "-" * 10
test_data = [
    (10, 10, "\n".join([test_line] * 7)),
    (10, 10, "\n".join([test_line] * 6)),
    (10, 10, "\n".join([test_line] * 5)),
    (10, 10, "-" * 11),
    (10, 10, "-" * 10),
    (10, 10, "-" * 9),
]

# 4 lines are reserved at the bottom of the terminal for pgcli's prompt
use_pager_when_on = [True, True, False, True, False, False]

# Can be replaced with pytest.param once we can upgrade pytest after Python 3.4 goes EOL
test_ids = [
    "Output longer than terminal height",
    "Output equal to terminal height",
    "Output shorter than terminal height",
    "Output longer than terminal width",
    "Output equal to terminal width",
    "Output shorter than terminal width",
]


@pytest.fixture
def pset_pager_mocks():
    cli = PGCli()
    cli.watch_command = None
    with mock.patch("mzcli.main.click.echo") as mock_echo, mock.patch(
        "mzcli.main.click.echo_via_pager"
    ) as mock_echo_via_pager, mock.patch.object(cli, "prompt_app") as mock_app:

        yield cli, mock_echo, mock_echo_via_pager, mock_app


@pytest.mark.parametrize("term_height,term_width,text", test_data, ids=test_ids)
def test_pset_pager_off(term_height, term_width, text, pset_pager_mocks):
    cli, mock_echo, mock_echo_via_pager, mock_cli = pset_pager_mocks
    mock_cli.output.get_size.return_value = termsize(
        rows=term_height, columns=term_width
    )

    with mock.patch.object(cli.pgspecial, "pager_config", PAGER_OFF):
        cli.echo_via_pager(text)

    mock_echo.assert_called()
    mock_echo_via_pager.assert_not_called()


@pytest.mark.parametrize("term_height,term_width,text", test_data, ids=test_ids)
def test_pset_pager_always(term_height, term_width, text, pset_pager_mocks):
    cli, mock_echo, mock_echo_via_pager, mock_cli = pset_pager_mocks
    mock_cli.output.get_size.return_value = termsize(
        rows=term_height, columns=term_width
    )

    with mock.patch.object(cli.pgspecial, "pager_config", PAGER_ALWAYS):
        cli.echo_via_pager(text)

    mock_echo.assert_not_called()
    mock_echo_via_pager.assert_called()


pager_on_test_data = [l + (r,) for l, r in zip(test_data, use_pager_when_on)]


@pytest.mark.parametrize(
    "term_height,term_width,text,use_pager", pager_on_test_data, ids=test_ids
)
def test_pset_pager_on(term_height, term_width, text, use_pager, pset_pager_mocks):
    cli, mock_echo, mock_echo_via_pager, mock_cli = pset_pager_mocks
    mock_cli.output.get_size.return_value = termsize(
        rows=term_height, columns=term_width
    )

    with mock.patch.object(cli.pgspecial, "pager_config", PAGER_LONG_OUTPUT):
        cli.echo_via_pager(text)

    if use_pager:
        mock_echo.assert_not_called()
        mock_echo_via_pager.assert_called()
    else:
        mock_echo_via_pager.assert_not_called()
        mock_echo.assert_called()


@pytest.mark.parametrize(
    "text,expected_length",
    [
        (
            "22200K .......\u001b[0m\u001b[91m... .......... ...\u001b[0m\u001b[91m.\u001b[0m\u001b[91m...... .........\u001b[0m\u001b[91m.\u001b[0m\u001b[91m \u001b[0m\u001b[91m.\u001b[0m\u001b[91m.\u001b[0m\u001b[91m.\u001b[0m\u001b[91m.\u001b[0m\u001b[91m...... 50% 28.6K 12m55s",
            78,
        ),
        ("=\u001b[m=", 2),
        ("-\u001b]23\u0007-", 2),
    ],
)
def test_color_pattern(text, expected_length, pset_pager_mocks):
    cli = pset_pager_mocks[0]
    assert len(COLOR_CODE_REGEX.sub("", text)) == expected_length


@dbtest
def test_i_works(tmpdir, executor):
    sqlfile = tmpdir.join("test.sql")
    sqlfile.write("SELECT NOW()")
    rcfile = str(tmpdir.join("rcfile"))
    cli = PGCli(pgexecute=executor, mzclirc_file=rcfile)
    statement = r"\i {0}".format(sqlfile)
    run(executor, statement, pgspecial=cli.pgspecial)


@dbtest
def test_watch_works(executor):
    cli = PGCli(pgexecute=executor)

    def run_with_watch(
        query, target_call_count=1, expected_output="", expected_timing=None
    ):
        """
        :param query: Input to the CLI
        :param target_call_count: Number of times the user lets the command run before Ctrl-C
        :param expected_output: Substring expected to be found for each executed query
        :param expected_timing: value `time.sleep` expected to be called with on every invocation
        """
        with mock.patch.object(cli, "echo_via_pager") as mock_echo, mock.patch(
            "mzcli.main.sleep"
        ) as mock_sleep:
            mock_sleep.side_effect = [None] * (target_call_count - 1) + [
                KeyboardInterrupt
            ]
            cli.handle_watch_command(query)
        # Validate that sleep was called with the right timing
        for i in range(target_call_count - 1):
            assert mock_sleep.call_args_list[i][0][0] == expected_timing
        # Validate that the output of the query was expected
        assert mock_echo.call_count == target_call_count
        for i in range(target_call_count):
            assert expected_output in mock_echo.call_args_list[i][0][0]

    # With no history, it errors.
    with mock.patch("mzcli.main.click.secho") as mock_secho:
        cli.handle_watch_command(r"\watch 2")
    mock_secho.assert_called()
    assert (
        r"\watch cannot be used with an empty query"
        in mock_secho.call_args_list[0][0][0]
    )

    # Usage 1: Run a query and then re-run it with \watch across two prompts.
    run_with_watch("SELECT 111", expected_output="111")
    run_with_watch(
        "\\watch 10", target_call_count=2, expected_output="111", expected_timing=10
    )

    # Usage 2: Run a query and \watch via the same prompt.
    run_with_watch(
        "SELECT 222; \\watch 4",
        target_call_count=3,
        expected_output="222",
        expected_timing=4,
    )

    # Usage 3: Re-run the last watched command with a new timing
    run_with_watch(
        "\\watch 5", target_call_count=4, expected_output="222", expected_timing=5
    )


def test_missing_rc_dir(tmpdir):
    rcfile = str(tmpdir.join("subdir").join("rcfile"))

    PGCli(mzclirc_file=rcfile)
    assert os.path.exists(rcfile)


def test_quoted_db_uri(tmpdir):
    with mock.patch.object(PGCli, "connect") as mock_connect:
        cli = PGCli(mzclirc_file=str(tmpdir.join("rcfile")))
        cli.connect_uri("postgres://bar%5E:%5Dfoo@baz.com/testdb%5B")
    mock_connect.assert_called_with(
        database="testdb[", host="baz.com", user="bar^", passwd="]foo"
    )


def test_pg_service_file(tmpdir):

    with mock.patch.object(PGCli, "connect") as mock_connect:
        cli = PGCli(mzclirc_file=str(tmpdir.join("rcfile")))
        with open(tmpdir.join(".pg_service.conf").strpath, "w") as service_conf:
            service_conf.write(
                """File begins with a comment
            that is not a comment
            # or maybe a comment after all
            because psql is crazy

            [myservice]
            host=a_host
            user=a_user
            port=5433
            password=much_secure
            dbname=a_dbname

            [my_other_service]
            host=b_host
            user=b_user
            port=5435
            dbname=b_dbname
            """
            )
        os.environ["PGSERVICEFILE"] = tmpdir.join(".pg_service.conf").strpath
        cli.connect_service("myservice", "another_user")
        mock_connect.assert_called_with(
            database="a_dbname",
            host="a_host",
            user="another_user",
            port="5433",
            passwd="much_secure",
        )

    with mock.patch.object(PGExecute, "__init__") as mock_pgexecute:
        mock_pgexecute.return_value = None
        cli = PGCli(mzclirc_file=str(tmpdir.join("rcfile")))
        os.environ["PGPASSWORD"] = "very_secure"
        cli.connect_service("my_other_service", None)
    mock_pgexecute.assert_called_with(
        "b_dbname",
        "b_user",
        "very_secure",
        "b_host",
        "5435",
        "",
        application_name="pgcli",
    )
    del os.environ["PGPASSWORD"]
    del os.environ["PGSERVICEFILE"]


def test_ssl_db_uri(tmpdir):
    with mock.patch.object(PGCli, "connect") as mock_connect:
        cli = PGCli(mzclirc_file=str(tmpdir.join("rcfile")))
        cli.connect_uri(
            "postgres://bar%5E:%5Dfoo@baz.com/testdb%5B?"
            "sslmode=verify-full&sslcert=m%79.pem&sslkey=my-key.pem&sslrootcert=c%61.pem"
        )
    mock_connect.assert_called_with(
        database="testdb[",
        host="baz.com",
        user="bar^",
        passwd="]foo",
        sslmode="verify-full",
        sslcert="my.pem",
        sslkey="my-key.pem",
        sslrootcert="ca.pem",
    )


def test_port_db_uri(tmpdir):
    with mock.patch.object(PGCli, "connect") as mock_connect:
        cli = PGCli(mzclirc_file=str(tmpdir.join("rcfile")))
        cli.connect_uri("postgres://bar:foo@baz.com:2543/testdb")
    mock_connect.assert_called_with(
        database="testdb", host="baz.com", user="bar", passwd="foo", port="2543"
    )


def test_multihost_db_uri(tmpdir):
    with mock.patch.object(PGCli, "connect") as mock_connect:
        cli = PGCli(mzclirc_file=str(tmpdir.join("rcfile")))
        cli.connect_uri(
            "postgres://bar:foo@baz1.com:2543,baz2.com:2543,baz3.com:2543/testdb"
        )
    mock_connect.assert_called_with(
        database="testdb",
        host="baz1.com,baz2.com,baz3.com",
        user="bar",
        passwd="foo",
        port="2543,2543,2543",
    )


def test_application_name_db_uri(tmpdir):
    with mock.patch.object(PGExecute, "__init__") as mock_pgexecute:
        mock_pgexecute.return_value = None
        cli = PGCli(mzclirc_file=str(tmpdir.join("rcfile")))
        cli.connect_uri("postgres://bar@baz.com/?application_name=cow")
    mock_pgexecute.assert_called_with(
        "materialize", "bar", "", "baz.com", "6875", "", application_name="cow"
    )
