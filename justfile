set shell := ["bash", "-eu", "-o", "pipefail", "-c"]
set dotenv-load := false

# Do not update the env, when running
export UV_NO_SYNC := '1'

# List all available recipes
_default:
    @just --list --unsorted

# Install all dependencies
[group('dev')]
install *args='':
    uv sync --all-groups {{ args }}

# Install only what is needed to run unit tests
[group('dev')]
install-test:
    uv sync --no-default-groups --group unit-test --locked

# Replace the locked `django-modern-rest` with a minor release, like `0.16`
[group('dev')]
install-dmr version:
    uv pip install "django-modern-rest=={{ version }}.*"

# Format code with ruff
[group('dev')]
format:
    uv run python -m ruff format
    uv run python -m ruff check

# Run all linters
[group('dev')]
lint:
    uv run python -m ruff check --exit-non-zero-on-fix
    uv run python -m ruff format --check --diff
    uv run python -m flake8 .

# Run all type checkers
[group('dev')]
type-check:
    uv run python -m mypy .
    uv run python -m pyright

# Run all checks
[group('dev')]
test *args='': lint type-check package (unit args)

# Run unit tests
[group('testing')]
unit *args='':
    uv run python -m pytest -n auto --max-worker-restart=1 \
      --inline-snapshot=disable {{ args }}
    uv run strict-no-cover

# Validate package dependencies and run security audit
[group('testing')]
package:
    # Validates `uv.lock` against `pyproject.toml`:
    uv lock --check
    # Validates the environment against `uv.lock`:
    uv sync --all-groups --locked --check
    uv pip check
    uv --preview-features audit audit

# Build sdist and wheel
[group('build')]
build: clean
    uv build

# Remove build artifacts
[group('build')]
clean:
    rm -rf build/ dist/

# Set a new version in `pyproject.toml` and `uv.lock`
[group('release')]
bump version:
    uv version {{ version }}
    @echo 'Now update CHANGELOG.md, commit, and open a pull request.'
    @echo 'When it is merged, run: just release {{ version }}'

# Create a git tag and a GitHub release, CI then publishes it to PyPI
[confirm('Create a tag and a GitHub release in the origin repository?')]
[group('release')]
release version:
    #!/usr/bin/env bash
    set -euo pipefail

    tag='v{{ version }}'
    sha="$(git rev-parse HEAD)"

    if [[ "$(git branch --show-current)" != 'main' ]]; then
      echo 'Releases are only created from the `main` branch' >&2
      exit 1
    fi
    if [[ -n "$(git status --porcelain)" ]]; then
      echo 'Working tree is not clean, commit or stash your changes' >&2
      exit 1
    fi

    git fetch --quiet origin main
    if [[ "$sha" != "$(git rev-parse origin/main)" ]]; then
      echo 'Local `main` differs from `origin/main`, push or pull first' >&2
      exit 1
    fi
    if ! grep -qx 'version = "{{ version }}"' pyproject.toml; then
      echo 'Version in `pyproject.toml` is not {{ version }}, run `just bump`' >&2
      exit 1
    fi
    if gh release view "$tag" >/dev/null 2>&1; then
      echo "Release $tag already exists" >&2
      exit 1
    fi

    # Never release a commit that did not pass the tests:
    conclusion="$(gh run list --workflow test.yaml --branch main \
      --commit "$sha" --json conclusion --jq '.[0].conclusion')"
    if [[ "$conclusion" != 'success' ]]; then
      echo "Tests for $sha did not succeed (status: ${conclusion:-none})" >&2
      exit 1
    fi

    # Pre-releases (`0.2.0rc1`, `0.2.0a1`, etc.) are marked as such:
    prerelease=()
    if [[ '{{ version }}' =~ [a-zA-Z] ]]; then
      prerelease=(--prerelease)
    fi

    # This creates the tag and the release,
    # `publish.yaml` starts when the release is published:
    gh release create "$tag" --target "$sha" --title "$tag" \
      --generate-notes ${prerelease[@]+"${prerelease[@]}"}
