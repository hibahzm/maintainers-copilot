# Migrate service

This one-shot container becomes the Alembic runner for the stack.

Right now it proves the container shape exists. During the foundation milestone, `alembic.ini` and the first migration revision will be added so the container runs `alembic upgrade head` before the API starts.
