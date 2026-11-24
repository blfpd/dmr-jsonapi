"""
Prints the latest minor releases of ``django-modern-rest`` as JSON.

We use it to build the test matrix, so we always test
against the newest versions of the library that we extend.
Pre-releases and yanked releases are ignored.
"""

import json
import re
from typing import Any
from urllib.request import urlopen

_PYPI_URL = 'https://pypi.org/pypi/django-modern-rest/json'
_TIMEOUT = 30
_COUNT = 3
_STABLE = re.compile(r'(\d+)\.(\d+)\.\d+')


def _is_installable(release_files: list[dict[str, Any]]) -> bool:
    # An empty or fully yanked release can't be installed:
    return any(not release_file['yanked'] for release_file in release_files)


def _minor_releases(releases: dict[str, Any]) -> set[tuple[int, ...]]:
    stable = (
        _STABLE.fullmatch(version)
        for version, release_files in releases.items()
        if _is_installable(release_files)
    )
    return {tuple(map(int, match.groups())) for match in stable if match}


def main() -> None:
    """Print the latest minor releases, the newest one goes first."""
    with urlopen(_PYPI_URL, timeout=_TIMEOUT) as response:
        releases = json.load(response)['releases']
    latest = sorted(_minor_releases(releases), reverse=True)[:_COUNT]
    versions = ['.'.join(map(str, minor)) for minor in latest]
    print(json.dumps(versions))  # noqa: WPS421


if __name__ == '__main__':
    main()
