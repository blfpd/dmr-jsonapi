# How to contribute


## Dependencies

We use [uv](https://github.com/astral-sh/uv) to manage the dependencies
and [just](https://github.com/casey/just) as a command runner.

To install `just` run:

```bash
uv tool install rust-just
```

To install project dependencies via `just` run:

```bash
just install
```

To activate your `virtualenv` run:

```bash
source .venv/bin/activate
```


## One magic command

After you installed the deps, run `just test` to run all the checks we have!

To see all available commands:

```bash
just
```


## Tests

We have 100% test coverage, it is enforced.
To run the tests on your machine:

```bash
just unit
```

CI runs them with Python 3.13, 3.14, and 3.15 against the three latest
minor releases of `django-modern-rest`. To try another release locally:

```bash
just install-dmr 0.16
just unit
```

Use `just install` to get back to the locked version.


## Code style

We use [wemake-python-styleguide](https://wemake-python-styleguide.readthedocs.io/en/latest/)
and [ruff](https://docs.astral.sh/ruff/). To format and check your code:

```bash
just format
just lint
just type-check
```

We also use [pre-commit](https://pre-commit.com/), install the hooks with:

```bash
uvx pre-commit install
```


## Releases

Maintainers only. Releases are published to PyPI by GitHub Actions
when a GitHub release is created.

1. Run `just bump <version>`, update `CHANGELOG.md`,
   commit the changes, and merge them to `main`
2. Run `just release <version>` from an up to date `main` branch.
   It checks that tests are green for the commit,
   then creates the `v<version>` tag and a GitHub release with notes
3. `publish.yaml` runs the tests once again, builds the package,
   and publishes it using
   [trusted publishing](https://docs.pypi.org/trusted-publishers/)

One time setup for a new project:

- On PyPI, add a pending publisher for `dmr-jsonapi`:
  repository `blfpd/dmr-jsonapi`, workflow `publish.yaml`,
  environment `pypi`
- On GitHub, create the `pypi` environment in the repository settings
