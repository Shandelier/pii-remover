#!/usr/bin/env bash
set -euo pipefail

REPOSITORY="testpypi"
SKIP_TESTS=0
SKIP_BUILD=0

usage() {
  cat <<'EOF'
Usage:
  scripts/publish_package.sh [--repository testpypi|pypi] [--skip-tests] [--skip-build]

Environment:
  PYPI_API_TOKEN       Token for --repository pypi
  TEST_PYPI_API_TOKEN  Token for --repository testpypi

Examples:
  TEST_PYPI_API_TOKEN=pypi-... scripts/publish_package.sh
  PYPI_API_TOKEN=pypi-... scripts/publish_package.sh --repository pypi

Do not put tokens in this repo or in .env committed to git.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repository)
      REPOSITORY="${2:-}"
      shift 2
      ;;
    --skip-tests)
      SKIP_TESTS=1
      shift
      ;;
    --skip-build)
      SKIP_BUILD=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ "$REPOSITORY" != "testpypi" && "$REPOSITORY" != "pypi" ]]; then
  echo "--repository must be either testpypi or pypi" >&2
  exit 2
fi

TOKEN_VAR="TEST_PYPI_API_TOKEN"
REPOSITORY_URL="https://test.pypi.org/legacy/"
if [[ "$REPOSITORY" == "pypi" ]]; then
  TOKEN_VAR="PYPI_API_TOKEN"
  REPOSITORY_URL="https://upload.pypi.org/legacy/"
fi

TOKEN="${!TOKEN_VAR:-}"
if [[ -z "$TOKEN" ]]; then
  echo "Missing $TOKEN_VAR." >&2
  echo "Create an API token in PyPI/TestPyPI and pass it as an environment variable." >&2
  exit 1
fi

python3 -m pip install -q --upgrade build twine

if [[ "$SKIP_TESTS" == "0" ]]; then
  python3 -m pytest -q
fi

if [[ "$SKIP_BUILD" == "0" ]]; then
  rm -rf dist
  python3 -m build --sdist --wheel
fi

python3 -m twine check dist/*
python3 -m twine upload \
  --repository-url "$REPOSITORY_URL" \
  --username __token__ \
  --password "$TOKEN" \
  dist/*
