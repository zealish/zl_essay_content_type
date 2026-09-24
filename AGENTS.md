# AGENTS.md

# Odoo 18 Community Development Guide

## Project Overview

This project is an Odoo 18 Community application running with Docker Compose.

The Docker container is the runtime environment only.

All development must be performed on the host machine.

Never edit source code inside the Docker container.

---

# Initial Inspection (Mandatory)

Before starting any task, inspect the project configuration.

Read:

- docker-compose.yml
- compose.yml
- compose.yaml
- docker-compose.yaml
- etc/odoo.conf
- addons manifests when relevant

Determine automatically:

- Odoo service name
- PostgreSQL service name
- mounted addon directories
- addons_path
- configuration file location
- log configuration

Never assume container names or filesystem paths.

---

# Source of Truth

Custom modules are located on the host machine.

Always edit host files.

If a module has not yet been mounted into Docker, continue working on the host version.

Never edit files inside the container.

---

# Docker Usage

Docker is used only for:

- inspecting Odoo core
- inspecting installed addons
- checking logs
- opening Odoo shell
- upgrading modules
- debugging runtime issues

Never use Docker as the editing workspace.

---

# Odoo Core Reference

When implementation details are unclear:

Inspect Odoo core inside the running container.

Examples include:

- models
- ORM implementation
- existing Community addons
- Owl components
- QWeb templates

Read only.

Never modify Odoo core.

---

# Module Development

Always follow standard Odoo structure.

models/
views/
security/
wizard/
controllers/
report/
data/
demo/
static/
tests/

Keep modules clean and modular.

---

# Python

Follow Odoo conventions.

Prefer:

- ORM
- api.depends
- api.onchange
- api.constrains
- compute fields
- related fields

Avoid raw SQL unless absolutely necessary.

---

# XML

Prefer inherited views.

Use xpath whenever possible.

Never replace an entire view if inheritance is sufficient.

---

# Security

Always verify:

- ir.model.access.csv
- record rules
- user groups

Never expose models without proper security.

---

# ORM

Always use ORM.

Prefer:

- search()
- browse()
- create()
- write()
- unlink()
- mapped()
- filtered()

Avoid SQL.

---

# Performance

Avoid:

search() inside loops

Prefer:

- batch queries
- mapped()
- read_group()
- prefetch-friendly code

---

# JavaScript

When working with frontend:

Follow Odoo 18 Owl architecture.

Register assets correctly.

Update manifest assets.

---

# Manifest

Keep **manifest**.py synchronized.

Verify:

- depends
- data
- assets
- demo
- version

---

# Logging

Use Python logging.

Never use print().

---

# Validation

When validation is requested:

1. Detect Docker Compose services.
2. Detect the Odoo service.
3. Detect the database if possible.
4. Upgrade only the affected module.
5. Inspect logs.
6. Report traceback if any.

Do not assume:

- service names
- database names
- addon paths

Read configuration first.

---

# Communication

Before implementing:

Explain:

- affected models
- affected views
- business logic

After implementing:

Summarize:

- modified files
- created files
- upgrade commands if needed

---

# Never Do

Never:

- edit files inside Docker
- modify Odoo core
- duplicate existing Odoo functionality
- bypass ORM
- disable security
- hardcode container names
- hardcode database names
- hardcode filesystem paths

Always inspect the project configuration before making assumptions.

---

# Preferred Development Workflow

For every task:

1. Read project configuration.
2. Inspect the custom module.
3. Inspect Odoo core if necessary.
4. Design the solution.
5. Implement on the host machine.
6. Validate if requested.
7. Summarize the changes.

# Active credential for testing

username: admin@hracademy.id
passsword: admin
database: hra
