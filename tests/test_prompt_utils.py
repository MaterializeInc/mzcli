import click

from mzcli.packages.prompt_utils import confirm_destructive_query


def test_confirm_destructive_query_notty():
    stdin = click.get_text_stream("stdin")
    if not stdin.isatty():
        sql = "drop database foo;"
        assert confirm_destructive_query(sql, "all") is None
