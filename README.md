[![CI Status](https://img.shields.io/github/actions/workflow/status/postgrespro/testgres_exts.pglab/.github/workflows/ci.yml?label=CI)](https://github.com/postgrespro/testgres_exts.pglab/actions/workflows/ci.yml)

# PgLab

PgLab is a Linux fault-injection layer for PostgreSQL tests built on top of
[Testgres](https://github.com/postgrespro/testgres).

Testgres owns PostgreSQL lifecycle, SQL access, backups and physical replication.
PgLab owns Linux isolation and faults:

- network namespaces, veth pairs and a bridge;
- cgroup v1/v2 I/O throttling;
- network partitions;
- `tc netem` delay, jitter, loss, duplication, corruption, reordering and rate limits;
- freeze/unfreeze of a PostgreSQL process group;
- cleanup of namespaces, cgroups, qdiscs and temporary firewall rules.

PgLab currently requires Linux and root privileges because it creates network
namespaces, interfaces and cgroups. PostgreSQL itself runs as a configurable
unprivileged Unix account.

## Why this needed changes in Testgres

Each PgLab node has a different `OsOperations` execution context: PostgreSQL
commands for a replica must run inside that replica's network namespace, and
server-starting commands must also enter its cgroup.  A replica therefore cannot
simply inherit the primary node's `os_ops`, host and port-management context.

The Testgres target execution-context API lets PgLab keep the proper separation
of responsibilities: Testgres still owns `pg_basebackup`, physical replication
and `PostgresNode` lifecycle; PgLab only supplies the target execution context
and Linux fault injection.

See [docs/why-testgres-execution-context.md](docs/why-testgres-execution-context.md)
for the concrete primary/replica flow and the reason behind the upstream
Testgres changes.

## Testgres compatibility

PgLab uses the target execution-context API in current Testgres:

```python
primary.replicate(
    target_os_ops=replica_ops,
    target_host=replica_ip,
    target_port=5432,
)
```

The compatible Testgres tree must provide:

- `PostgresNode.replicate(target_os_ops=..., target_host=..., target_port=...)`;
- `NodeBackup(..., os_ops=...)`, so `pg_basebackup` can run in the target context;
- target execution-context support in node cloning.

The current development target is Testgres 1.17.0 with that API. Until those
changes are present in a released Testgres build, install Testgres from the
compatible checkout and install PgLab editable beside it.

## Development install

With a compatible Testgres checkout in `../testgres`:

```bash
./setup.sh --testgres-dir ../testgres
```

Or manually:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -U pip setuptools wheel
.venv/bin/python -m pip install -e ../testgres
.venv/bin/python -m pip install -e '.[test]'
.venv/bin/python tools/verify_install.py
```

When the required Testgres API is available from PyPI, a normal editable install
is enough:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
```

No `setup.py` is required. Packaging metadata lives in `pyproject.toml`.

## PostgreSQL environment

Point PgLab at the PostgreSQL build you want to test:

```bash
export PG_BIN=/home/user/build/postgres/bin
export PGLAB_OS_USER=user
export PGLAB_DB_USER=postgres
export PGLAB_TEST_ROOT=/var/tmp
```

`PGLAB_TEST_ROOT` should live on a block-backed filesystem for cgroup I/O tests.
A tmpfs or overlay filesystem is fine for networking-only tests but cannot be
mapped reliably to a block device for `io.max`/blkio throttling.

Check the host:

```bash
./scripts/doctor.sh
```

## Example

```python
from pglab import PgLab

with PgLab(
    pg_bin="/home/user/build/postgres/bin",
    base_dir="/var/tmp/pglab-demo",
    subnet="10.203.0.0/24",
    os_user="user",
    db_superuser="postgres",
) as lab:
    primary = lab.create_primary("p1", "10.203.0.10", port=5432)
    primary.init().start()

    replica = lab.create_replica("p1", "r1", "10.203.0.11", port=5432)
    replica.start()
    replica.catchup()

    replica.netem(delay_ms=100, loss_pct=1)
    replica.clear_netem()

    lab.partition("p1", "r1")
    lab.heal_partition("p1", "r1")

    replica.freeze()
    replica.unfreeze()
```

The same TCP port may be used by several nodes because each PostgreSQL server
runs in its own network namespace. PgLab disables Unix-domain PostgreSQL
sockets to avoid collisions in the shared mount namespace.

## Tests

Smoke test:

```bash
./scripts/run-smoke.sh
```

Full integration suite:

```bash
./scripts/run-tests.sh
```

One file or test can be selected normally:

```bash
./scripts/run-tests.sh tests/test_pglab_netem_effects.py
```

The integration suite covers primary/replica lifecycle, same-port replicas,
partitions and recovery, cgroup I/O controls, cleanup after failures, netem
latency/loss/rate effects, freeze/unfreeze, replication lag and an unrecoverable
WAL-gap scenario.

## Project layout

```text
pglab.py                       PgLab implementation
pyproject.toml                 Python package metadata
example.py                     small usage example
smoke.py                       end-to-end smoke test
tests/                         integration and compatibility tests
scripts/doctor.sh              environment diagnostics
scripts/run-tests.sh           privileged test runner
scripts/run-smoke.sh           privileged smoke runner
scripts/install-system-deps.sh host package helper
tools/verify_install.py        Testgres API compatibility check
docs/why-testgres-execution-context.md
                              rationale for the Testgres target-context API
```

PgLab is still experimental. The public API and packaging may change while the
corresponding Testgres execution-context API is being reviewed upstream.

## License

PgLab is distributed under the PostgreSQL License. See [`LICENSE`](LICENSE).
