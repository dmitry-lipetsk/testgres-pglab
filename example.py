#!/usr/bin/env python3
import os
from pathlib import Path

from src import PgLab


def need_env(name):
    value = os.environ.get(name)
    if not value:
        raise SystemExit("{} is required".format(name))
    return value


PG_BIN = need_env("PG_BIN")
OS_USER = need_env("PGLAB_OS_USER")
DB_USER = os.environ.get("PGLAB_DB_USER", "postgres")
TEST_ROOT = Path(os.environ.get("PGLAB_TEST_ROOT", "/var/tmp"))

with PgLab(
    pg_bin=PG_BIN,
    base_dir=str(TEST_ROOT / "pglab-smoke"),
    subnet="10.203.0.0/24",
    bridge_name="pglab0",
    os_user=OS_USER,
    db_superuser=DB_USER,
) as lab:
    primary = lab.create_primary("primary", "10.203.0.10", port=5432)
    primary.init().start()

    replica = lab.create_replica("primary", "replica1", "10.203.0.11", port=5432)
    replica.start()
    replica.catchup()

    primary.execute("create table smoke(i int primary key)")
    primary.execute("insert into smoke values (1)")
    replica.catchup()
    assert replica.execute("select * from smoke") == [(1,)]

    replica.netem(delay_ms=50, loss_pct=1)
    replica.clear_netem()

    primary.execute("insert into smoke values (2)")
    replica.catchup()
    assert replica.execute("select array_agg(i order by i) from smoke") == [([1, 2],)]

print("OK: PgLab primary/replica + catchup + netem smoke test")
