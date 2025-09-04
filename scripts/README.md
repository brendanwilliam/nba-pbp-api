# Scripts Directory

This directory contains development and maintenance utilities that are separate from the core WNBA scraping business logic.

## Current Scripts

### `manage_test_expectations.py`
Development utility for managing test expectations and test data.

## Usage Pattern

Scripts in this directory are standalone utilities meant to be run directly:
```bash
python scripts/script_name.py
```

## Distinction from `/src/scripts/`

- **`/scripts/`** (this directory): Development/maintenance utilities
- **`/src/scripts/`**: Core business logic scripts that run as modules (`python -m src.scripts.script_name`)

For core WNBA scraping functionality, see `/src/scripts/README.md`.