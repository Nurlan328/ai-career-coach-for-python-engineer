# Migrations (Alembic)

Schema versioning for the database. The URL comes from app settings
(`DATABASE_URL`), injected in `env.py`.

```bash
# apply all migrations (create/upgrade schema)
alembic upgrade head

# create a new migration after changing models
alembic revision --autogenerate -m "add column X"

# roll back the last migration
alembic downgrade -1

# show current / history
alembic current
alembic history
```

To let Alembic own the schema (instead of the dev-time auto-create), set
`AUTO_CREATE_TABLES=false` in the backend `.env` and run `alembic upgrade head`.
