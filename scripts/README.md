# Release scripts

## PyPI token

Do not put PyPI tokens in this repo or in `.env` committed to git.

Use environment variables:

```bash
export TEST_PYPI_API_TOKEN=pypi-...
export PYPI_API_TOKEN=pypi-...
```

For local convenience you can also keep tokens in your shell profile or password manager.

## Publish

Upload to TestPyPI first:

```bash
TEST_PYPI_API_TOKEN=pypi-... scripts/publish_package.sh
```

Upload to real PyPI:

```bash
PYPI_API_TOKEN=pypi-... scripts/publish_package.sh --repository pypi
```

The script runs tests, rebuilds `dist/`, checks artifacts with `twine`, and uploads.
