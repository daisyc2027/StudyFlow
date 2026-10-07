# Stage 01 — executable foundation and testing first

## Build

Inspect this new workspace and read the scope/test contract. Create a short execution
plan. Set up an isolated Python environment, supported pinned dependencies, Flask
application factory, SQLAlchemy, migrations, configuration and a temporary-test setup.
Do not copy the previous app or its model dependencies.

Implement registration, login/logout, sessions, password hashing, authorization helpers,
CSRF protection and a small real dashboard. Configure local-only development serving;
use a generated local secret rather than committing a production secret. Set up linter
and pytest commands, plus the initial scripts/check.py entry point.

Install the isolated Chromium test browser within permitted setup operations. Prove
that Playwright can start the app and interact with a real page now, rather than
discovering browser setup problems after all features are written. No global browser
replacement or OS-wide dependency changes.

## Gate

App boots on a configurable localhost port. Auth and health tests pass. Two-user
isolation fixtures exist. A headless browser registers/logs in and sees the dashboard.
Record actual setup/version/command output. Establish clean test database/server
teardown. Update progress, then start Stage 02.
