# Database Migration Rollout

## Current state

The FastAPI lifespan currently calls `Base.metadata.create_all()`. Alembic is configured and imports all SQLAlchemy models, but there is no checked-in versioned schema baseline yet. Do not remove `create_all()` or run `alembic upgrade head` against an existing deployment until the baseline and adoption path have been validated.

## Required rollout

1. **Capture the schema contract.** Generate an initial Alembic revision from the complete, explicitly imported model metadata against the current model set. Review it as a static migration: it must contain explicit table, column, constraint, enum, and index operations. Do not put `Base.metadata.create_all()`, runtime model imports, or other dynamic schema generation inside a revision.
2. **Fresh-database test.** Create an empty PostgreSQL database, run `alembic upgrade head`, and verify all expected tables, foreign keys, indexes, and enum types exist. Run this in CI.
3. **Existing-database adoption.** Back up the database and compare its schema against the initial revision first. If it exactly matches the baseline, record the baseline revision with `alembic stamp <revision>`; stamping records migration history and does not create or alter tables. If it differs, write and review a forward-only reconciliation migration before stamping. Never stamp blindly.
4. **Switch application startup.** Once the migration is reviewed and both fresh-database and existing-schema adoption paths are tested, remove startup `create_all()`. Deployments should apply `alembic upgrade head` as an explicit release step before starting application instances.
5. **Ongoing changes.** Every schema change gets a new immutable migration. Review generated diffs; do not edit a revision already applied to shared environments. Prefer expand/migrate/contract changes for production compatibility.

## Developer commands

Run from `backend/` with the same environment variables used by the app:

```bash
alembic revision --autogenerate -m "initial schema baseline"
alembic upgrade head
alembic current
alembic history
```

Autogenerate is a draft, not an approval: inspect the generated revision and verify enum names, server defaults, indexes, constraints, and downgrade behavior before committing it.

## Release safety checklist

- [ ] Static baseline migration is checked in and reviewed.
- [ ] Empty PostgreSQL database upgrades from zero to head.
- [ ] Existing database schema is compared before stamping.
- [ ] CI validates migration upgrade and schema expectations.
- [ ] Application startup no longer mutates schema implicitly.
- [ ] Backup and rollback/recovery procedure is documented.
