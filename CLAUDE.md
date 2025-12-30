# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A job board aggregator that scrapes multiple job portals (WeWorkRemotely, Remotive, Python.org, Himalayas, Work At A Startup, Wellfound) and filters them based on preferences like keywords, salary, and location. Built with Python/Flask backend and PostgreSQL database.

## Development Setup

```sh
# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Install JavaScript dependencies (for JS tests)
npm install

# Setup PostgreSQL database
job-board setup-db

# Run database migrations
alembic upgrade head
```

## Common Commands

### Running the Application

```sh
# Run the Flask development server
job-board runserver

# Run in debug mode
job-board runserver -d

# Run on specific host/port
job-board runserver -h 0.0.0.0 -p 8000
```

### Fetching Jobs

```sh
# Fetch jobs from all portals
job-board fetch

# Fetch from specific portals only
job-board fetch -I weworkremotely -I python_dot_org

# Exclude specific portals
job-board fetch -E wellfound -E work_at_a_startup

# Drop into pdb on exception (debugging)
job-board fetch --pdb
```

### Job Scheduler

```sh
# Start the scheduler (runs jobs per their cron schedules)
job-board scheduler start

# List all registered jobs
job-board scheduler list-jobs

# Run a specific job manually
job-board scheduler run-job fetch_jobs_daily

# Remove all scheduled jobs (useful before deployment)
job-board scheduler remove-jobs
```

### Testing

```sh
# Run Python tests
ENV=test pytest

# Run single test file
ENV=test pytest tests/test_models.py

# Run single test function
ENV=test pytest tests/test_models.py::test_function_name

# Run with coverage
ENV=test coverage run && coverage report

# Run JavaScript tests
npm run test:run

# Run JS tests with coverage
npm run test:coverage

# Run JS tests in watch mode
npm test
```

### Database Migrations

```sh
# Create a new migration
alembic revision --autogenerate -m "description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show migration history
alembic history
```

### CSS Development

```sh
# Build Tailwind CSS manually
bash scripts/build-tailwind.sh
```

**Note**: Pre-commit hooks automatically build CSS when templates change. In development (`ENV=dev`), Tailwind CDN is used; production uses optimized local CSS.

### Code Quality

```sh
# Run all pre-commit hooks manually
pre-commit run --all-files

# Run specific hook
pre-commit run ruff --all-files
```

## Architecture

### Portal System

All job portals inherit from `BasePortal` (in `job_board/portals/base.py`). Each portal implements:
- `make_request()`: Fetch data from the portal
- `get_items()`: Extract job items from response
- Portal-specific parser class inheriting from `JobParser`

Portals auto-register via `__init_subclass__` into the `PORTALS` dictionary using their `portal_name` attribute.

**Important portal-specific notes**:
- **WeWorkRemotely** & **Wellfound**: Use Scrapfly API to bypass anti-scraping protection (requires `SCRAPFLY_API_KEY`)
- **Work At A Startup**: Requires authenticated cookies (`WORK_AT_A_STARTUP_COOKIE` and `WORK_AT_A_STARTUP_CSRF_TOKEN`)
- **Wellfound**: Very slow due to ASP (Anti Scraping Protection), scheduled separately at noon to avoid consuming credits

### Database Models

Core models in `job_board/models.py`:
- **Job**: Main job listing with salary, locations, tags, remote status
- **Tag**: Skills/technologies extracted via OpenAI LLM
- **JobTag**: Many-to-many relationship between jobs and tags
- **Payload**: Stores raw job data for debugging

Jobs use case-insensitive unique constraints on links. Location codes validated against ISO 3166 (pycountry).

### Job Parsing & Storage

1. Portal fetches raw data via `make_request()`
2. `get_items()` extracts individual job items
3. `filter_items()` removes old jobs and duplicates (by link)
4. Each item parsed by portal-specific `JobParser` subclass
5. Batch storage via `store_jobs()` using PostgreSQL `INSERT ... ON CONFLICT DO NOTHING`
6. Tags extracted asynchronously using OpenAI API (gpt-4o-mini) in batches

### Scheduler System

Uses APScheduler with cron expressions. Jobs registered in `job_board/schedules.py`:
- Most portals: Run at 1 AM/PM daily (avoiding midnight due to exchange rate API issues)
- Wellfound: Once daily at noon (slow, high credit cost)
- Tag filling: Every 5 minutes for jobs without tags
- Old job purging: Daily at midnight

The scheduler must import `job_board.schedules` to register jobs globally.

### Flask Application

Single-file Flask app (`job_board/views.py`) with two routes:
- `/`: HTML job board with pagination and filtering
- `/.json`: JSON API with same filters

Query logic separated into `job_board/query.py` for reusability.

### Configuration

All config in `job_board/config.py`, loaded from `.env` (or `.test.env` when `ENV=test`).

**Critical environment variables**:
- `DATABASE_URL`: PostgreSQL connection string
- `SCRAPFLY_API_KEY`: Required for WeWorkRemotely and Wellfound
- `OPENAI_API_KEY`: Required for tag extraction
- `WORK_AT_A_STARTUP_COOKIE` & `WORK_AT_A_STARTUP_CSRF_TOKEN`: Required for Work At A Startup
- `ENV`: Set to `dev` for development, `test` for testing (auto-drops into pdb on exceptions)

## Important Patterns

### Location Handling

Locations stored as ISO 3166 codes (alpha-2 for countries, subdivision codes for states/provinces). Use `pycountry` for validation. Database enforces valid codes via CHECK constraint.

### Salary Handling

Salaries stored as `Numeric` type. Database constraints:
- Both min/max must be non-negative
- max_salary >= min_salary
- Nullable (many jobs don't list salary)

### Testing

Tests use `.test.env` for configuration. Database interactions should use fixtures from `tests/conftest.py`. Mock external APIs (Scrapfly, OpenAI) using `respx` for HTTP mocking.

### Pre-commit Hooks

Three custom hooks:
1. `encrypt-app-secrets`: Encrypts sensitive files with Ansible Vault
2. `build-tailwind-css`: Auto-builds CSS when templates change
3. `generate-js-test-module`: Generates test module from main.js

Never commit unformatted Python code - pre-commit runs `ruff` and `reorder-python-imports` automatically.

## Code Style

- Python 3.13+ required
- Line length: 88 characters (Ruff)
- Coverage requirement: 98% minimum
- Use type hints (see existing code for patterns)
- Pre-compiled regex patterns as constants
- No blanket try-except blocks

## Pre-Development Checklist

**IMPORTANT: Before making any code changes, always run:**

1. **Linting checks** to ensure code quality:
   ```bash
   pre-commit run --all-files
   ```

2. **Tests** to ensure nothing is broken:
   ```bash
   ENV=test pytest
   ```

This ensures that your changes don't introduce linting issues or break existing functionality.

## Code Quality and Linting

### Pre-commit Hooks

This project uses pre-commit hooks to automatically check code quality before commits. The hooks are configured in `.pre-commit-config.yaml`.

#### Available Hooks

1. **trailing-whitespace** - Removes trailing whitespace
2. **end-of-file-fixer** - Ensures files end with a newline
3. **check-yaml** - Validates YAML files
4. **check-added-large-files** - Prevents committing large files
5. **ruff** - Python linter with auto-fix
6. **ruff-format** - Python code formatter
7. **reorder-python-imports** - Sorts imports alphabetically
8. **yamlfmt** - Formats YAML files in `infra/` directory
9. **terraform_fmt** - Formats Terraform files in `infra/` directory

#### Running Pre-commit Hooks

```bash
# Install hooks (run once after cloning)
pre-commit install

# Run all hooks on all files
pre-commit run --all-files

# Run all hooks on staged files only
pre-commit run

# Run a specific hook
pre-commit run ruff --all-files
pre-commit run ruff-format --all-files

# Skip hooks for a commit (NOT RECOMMENDED)
git commit --no-verify
```

## Writing Tests

### Best Practices

1. **Follow existing patterns** - Review similar tests in the codebase for consistency before writing new ones
2. **Prefer function-based tests** - Use function-based tests (not class-based)
3. **Put imports at the top** - All imports should be at the beginning of the file
4. **No redundant docstrings/comments** - Don't add docstrings that just repeat the test name, or comments where code is self-explanatory
5. **Verify actual behavior** - Don't write placeholder tests; tests should verify real functionality
6. **Focus on unit tests** - Write unit tests for custom code; use integration tests only when necessary (use judgment)
7. **Cover branches** - Test all code branches, but don't test Django or third-party library logic
8. **Use respx for mocking** - When mocking external HTTP requests, use the `respx` fixture
9. **Minimal code in context managers** - Only put the mocked execution inside context managers, not assertions
10. **Don't test third-party functionality** - Only test code written as part of this project, not Python/Django internals
11. **Use fixtures wisely** - Use fixtures for reusable or large data; move reusable fixtures to `conftest.py`
12. **Avoid duplicate testing** - Don't test the same functionality repeatedly; use patching or Django testing tools instead
