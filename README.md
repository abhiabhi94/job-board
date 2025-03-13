### Installing development version
```sh
pip install -e ".[dev]"
pre-commit install
```

### Running as a command

- Most options should be available using the `--help` flag.

```sh
job-notifier --help
```

- For running the command immediately

```sh
job-notifier run
```

- For running it as a schedule, that runs once per day.

```sh
job-notifier schedule
```

- For running the schedule immediately, usually useful in checking stuff

```sh
job-notifier schedule -I
```

### Running Tests

```sh
pytest
```

### Contributing

- Please use global `gitignore`, rather than adding a `gitignore` to the repository.
A writeup illustrating the reasoning behind this decision: https://sebastiandedeyne.com/setting-up-a-global-gitignore-file/
