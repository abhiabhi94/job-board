### Installing development version
```sh
pip install -e ".[dev]"
pre-commit install
```

### Running as a command

- Most options should be available using the `--help` flag.

```sh
job-board --help
```

- For running the command immediately

```sh
job-board run
```

- For running it as a schedule, that runs once per day.

```sh
job-board schedule
```

- For running the schedule immediately, usually useful in checking stuff

```sh
job-board schedule -I
```

### Running Tests

```sh
pytest
```

### Contributing

- Please use global `gitignore`, rather than adding a `gitignore` to the repository.
A writeup illustrating the reasoning behind this decision: https://sebastiandedeyne.com/setting-up-a-global-gitignore-file/
