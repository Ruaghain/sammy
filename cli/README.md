# sammy

Starts Sammy: reads its settings from the environment (and `.env`), sets up
the log file, creates the database engine, migrates each package's tables
and builds the services. Provides the `sammy` command. Unit tests live in
`tests/`.
