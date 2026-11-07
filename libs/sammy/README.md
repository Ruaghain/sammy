# sammy

How Sammy starts, whatever starts it (the `sammy` command now, the web
backend later): settings from the environment and `.env`, the log file, the
one database engine, each package's migrations, then the services. Unit
tests live in `tests/`.
