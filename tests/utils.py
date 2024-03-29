import pytest
import psycopg2
import psycopg2.extras
from mzcli.main import format_output, OutputSettings
from mzcli.pgexecute import register_json_typecasters
from os import getenv

POSTGRES_USER = getenv("MZUSER", getenv("PGUSER", "materialize"))
POSTGRES_HOST = getenv("MZHOST", getenv("PGHOST", "localhost"))
POSTGRES_PORT = getenv("MZPORT", getenv("PGPORT", 6875))
POSTGRES_PASSWORD = getenv("MZPASSWORD", getenv("PGPASSWORD", "materialize"))


def db_connection(dbname=None):
    conn = psycopg2.connect(
        user=POSTGRES_USER,
        host=POSTGRES_HOST,
        password=POSTGRES_PASSWORD,
        port=POSTGRES_PORT,
        database=dbname,
    )
    conn.autocommit = True
    return conn


try:
    conn = db_connection()
    CAN_CONNECT_TO_DB = True
    SERVER_VERSION = conn.server_version
    json_types = register_json_typecasters(conn, lambda x: x)
    JSON_AVAILABLE = "json" in json_types
    JSONB_AVAILABLE = "jsonb" in json_types
except:
    CAN_CONNECT_TO_DB = JSON_AVAILABLE = JSONB_AVAILABLE = False
    SERVER_VERSION = 0


dbtest = pytest.mark.skipif(
    not CAN_CONNECT_TO_DB,
    reason="Need a postgres instance at localhost accessible by user 'postgres'",
)


def mz_xfail(feature):
    return pytest.mark.xfail(reason=f"Materialize does not support {feature}")


def mz_skip(why):
    return pytest.mark.skip(f"materialize work needed: {why}")


requires_json = pytest.mark.skipif(
    not JSON_AVAILABLE, reason="Postgres server unavailable or json type not defined"
)


requires_jsonb = pytest.mark.skipif(
    not JSONB_AVAILABLE, reason="Postgres server unavailable or jsonb type not defined"
)


def create_db(dbname):
    with db_connection().cursor() as cur:
        try:
            cur.execute(f"""CREATE DATABASE {dbname}""")
        except:
            pass


def drop_tables(conn):
    with conn.cursor() as cur:
        # Materialize does not support dropping these items in transactions, so
        # we need to send them as individual queries.
        commands = """\
            DROP SCHEMA public CASCADE;
            CREATE SCHEMA public;
            DROP SCHEMA IF EXISTS schema1 CASCADE;
            DROP SCHEMA IF EXISTS schema2 CASCADE;\
        """.split(
            "\n"
        )
        for cmd in commands:
            cur.execute(cmd.strip())


def run(
    executor, sql, join=False, expanded=False, pgspecial=None, exception_formatter=None
):
    "Return string output for the sql to be run"

    results = executor.run(sql, pgspecial, exception_formatter)
    formatted = []
    settings = OutputSettings(
        table_format="psql", dcmlfmt="d", floatfmt="g", expanded=expanded
    )
    for title, rows, headers, status, sql, success, is_special in results:
        formatted.extend(format_output(title, rows, headers, status, settings))
    if join:
        formatted = "\n".join(formatted)

    return formatted


def completions_to_set(completions):
    return {
        (completion.display_text, completion.display_meta_text)
        for completion in completions
    }
