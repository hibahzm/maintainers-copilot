# Migrate service

This one-shot container is the Alembic runner for the stack.

It copies the root `alembic.ini` plus `migrations/`, then runs:

```bash
alembic upgrade head
```

The API depends on this container completing successfully before it starts.
