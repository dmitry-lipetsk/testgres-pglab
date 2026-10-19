#!/usr/bin/env python3
import importlib
import inspect
import sys
from importlib import metadata
from pathlib import Path

import src as pglab
from testgres.backup import NodeBackup
from testgres.node import PostgresNode

errors = []

try:
    testgres_ver = metadata.version("testgres")
except metadata.PackageNotFoundError:
    testgres_ver = "NOT INSTALLED"
    errors.append("testgres distribution metadata is not installed")

replicate_sig = inspect.signature(PostgresNode.replicate)
for name in ("target_os_ops", "target_host", "target_port"):
    if name not in replicate_sig.parameters:
        errors.append("PostgresNode.replicate() misses {!r}".format(name))

backup_init_sig = inspect.signature(NodeBackup.__init__)
if "os_ops" not in backup_init_sig.parameters:
    errors.append("NodeBackup.__init__() misses 'os_ops'")

spawn_sig = inspect.signature(NodeBackup.spawn_replica)
for name in ("target_host", "target_port"):
    if name not in spawn_sig.parameters:
        errors.append("NodeBackup.spawn_replica() misses {!r}".format(name))

clone_sig = inspect.signature(PostgresNode.clone_with_new_name_and_base_dir)
for name in ("target_os_ops", "target_host", "target_port"):
    if name not in clone_sig.parameters:
        errors.append(
            "PostgresNode.clone_with_new_name_and_base_dir() misses {!r}".format(name)
        )

if not isinstance(PostgresNode.os_ops, property):
    errors.append("PostgresNode.os_ops lost its @property decorator")

try:
    os_ops_ver = metadata.version("testgres.os_ops")
except metadata.PackageNotFoundError:
    os_ops_ver = "NOT INSTALLED"
    errors.append("testgres.os_ops is not installed")

node_mod = importlib.import_module("testgres.node")
backup_mod = importlib.import_module("testgres.backup")

print("Python:            {}".format(sys.version.split()[0]))
print("Testgres:          {}".format(testgres_ver))
print("Testgres node:     {}".format(Path(node_mod.__file__).resolve()))
print("Testgres backup:   {}".format(Path(backup_mod.__file__).resolve()))
print("testgres.os_ops:   {}".format(os_ops_ver))
print("PgLab source:      {}".format(Path(pglab.__file__).resolve()))
print("replicate:         {}".format(replicate_sig))
print("spawn_replica:     {}".format(spawn_sig))

if errors:
    print("\nFAILED:")
    for error in errors:
        print("  - " + error)
    raise SystemExit(1)

print("\nOK: compatible Testgres + PgLab are installed")
