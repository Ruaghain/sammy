# sammy-cli

The `sammy` command. It only parses the command line; how Sammy starts
(settings, logging, database, services) lives in the `sammy` package in
`libs/sammy`, which the web backend will share. Unit tests live in `tests/`.
