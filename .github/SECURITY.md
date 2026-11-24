# Security Policy


## Supported versions

`dmr-jsonapi` is in alpha. Security fixes go to the latest release only,
so please upgrade before reporting.


## Reporting a vulnerability

Please do not open a public issue, pull request, or discussion.
Report it privately through
[GitHub security advisories](https://github.com/blfpd/dmr-jsonapi/security/advisories/new),
only the maintainers can see it.

A useful report includes:

- the affected version, and the versions of `django-modern-rest` and Django
- a description of the issue and its impact
- steps or a minimal controller to reproduce it

We will acknowledge your report, keep you updated while we work on a fix,
and credit you in the advisory unless you prefer otherwise.
Please give us a reasonable time to release the fix before you disclose it.

Vulnerabilities in `django-modern-rest`, Django, or any other dependency
should go to that project's own security contact.


## How we protect the project

- **Static analysis:** the code is checked with the
  [Bandit rules](https://docs.astral.sh/ruff/rules/#flake8-bandit-s) of `ruff`
- **Known vulnerabilities:** CI checks the locked dependencies with `uv audit`
- **Dependency updates:** Dependabot updates the dependencies and the actions,
  and waits 7 days after each release, so a compromised release
  is likely to be found and yanked before we use it
- **Small footprint:** only two runtime dependencies,
  `django-modern-rest` and `typing-extensions`
- **CI hardening:** workflows are checked with
  [`zizmor`](https://docs.zizmor.sh), run with read-only permissions
  by default, and pin every action and pre-commit hook to a commit hash
- **Releases:** packages are built in CI and published with
  [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/),
  without any long-lived token
