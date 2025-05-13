### Introduction

A remote job board, this was initially built out of boring job hunting.
This basically scans through different portals and based upon the
preferences like keywords, salary, etc., and brings the jobs that match
your preference.

### Portals Integrated
- [WeWorkRemotely](https://weworkremotely.com)
- [Remotive](https://remotive.com)
- [Python](https://python.org)
- [Himalayas](https://himalayas.app)
- [Work At A Startup](https://workatastartup.com)
- [Wellfound](https://wellfound.com)

### Configurations
Most configurations can be set through a `.env` file. All configurations
can be found in [`job_board/config.py`](./job_board/config.py) file.


### CLI
- Most options should be available using the `--help` flag.

```sh
job-board --help
```

- Running the webserver in debug mode.
```sh
job-board runserver -d
```

- Fetching the jobs immediately

```sh
job-board fetch
```

- Run it for only specific portals(_include_ these portals)
```sh
job-board fetch -I weworkremotely -I python_dot_org
```

- Run it for all portals, but _exclude_ some(maybe the portal is down, etc)
```sh
job-board fetch -E wellfound -E work_at_a_startup
```

- Run it as a schedule, that runs once per day

```sh
job-board schedule
```

- Run the schedule immediately, usually useful in checking stuff

```sh
job-board schedule -I
```

### Tests

```sh
pytest
```

### Contributing

- Please use global `gitignore`, rather than adding a `gitignore` to the repository.
A writeup illustrating the reasoning behind this decision: https://sebastiandedeyne.com/setting-up-a-global-gitignore-file/

#### Installing development version
```sh
pip install -e ".[dev]"
pre-commit install
```

#### Integrations Per Portal

The below text is mostly written as a note to future me.
In hope, that it helps to debug in case of an issue.

##### [WeWorkRemotely](https://weworkremotely.com)

- Although, they have a public RSS feed, for some reason they seem to be
using some sort of cloudfare protection that is blocking HTTP requests
from scripts.

- So [scrapfly](https://scrapfly.io) is used to bypass it.


##### [Remotive](https://remotive.com)
- Although, they have API for fetching jobs, the data is pretty unstructured.

##### [Python](https://python.org)
- They have a public RSS feed, so the integration is mostly straightforward.


#### [Himalayas](https://himalayas.app)
- They have a public API, so the integration is straightforward.


#### [Wellfound](https://wellfound.com)
- They have special mechanisms setup to stop scripts from scraping
  their website.
- So [scrapfly](https://scrapfly.io) along with its ASP(Anti Scraping Protection)
  feature is used to bypass them.
    - Although this works, it makes the whole integration very slow
      since it takes close to 50 - 200 seconds to scrape a single page.
    - Total pages to scrape maybe around 20 - 40.
    - So yeah, a better alternative that reliably works faster is welcome.


#### [Work At A Startup](https://workatastartup.com)
- They don't show all jobs unless you're logged in to their profile.
- For now, the browser cookies(after logging in) are used
  to make requests and scrape.
    - These cookies seem to be long-lasting(haven't needed to change them even
    once since this was implemented.)


### TODO
- Add filtering as per location, nowadays remote doesn't actually
mean remote. Some job descriptions say remote India, remote USA etc.
