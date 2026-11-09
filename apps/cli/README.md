# cli

The `sammy` command. It only parses the command line; how Sammy starts
(settings, logging, database, services) lives in the `sammy.bootstrap` package in
`libs/bootstrap`, which the web backend will share. Unit tests live in
`tests/`.
