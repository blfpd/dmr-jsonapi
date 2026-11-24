import pytest

from dmr_jsonapi.negotiation import is_accept_unsatisfiable

_TYPE = 'application/vnd.api+json'


@pytest.mark.parametrize(
    'accept',
    [
        None,
        '',
        '*/*',
        'application/json',
        # Not a JSON:API media type, so it is not our business:
        'application/json; charset=utf-8',
        _TYPE,
        f'{_TYPE}; ext="https://example.com/ext"',
        f'{_TYPE}; profile="https://example.com/profile"',
        f'{_TYPE}; ext="a,b"; profile="c;d"',
        # `q` is not a media type parameter:
        f'{_TYPE}; q=0.5',
        f'{_TYPE};q=0.5;foo=bar',
        # At least one clean instance is enough:
        f'{_TYPE}; foo=bar, {_TYPE}',
        f'{_TYPE}; foo=bar, {_TYPE}; ext="x"',
        f'{_TYPE.upper()}; EXT="x"',
    ],
)
def test_satisfiable(accept: str | None) -> None:
    """Ensure that valid headers are not reported."""
    assert not is_accept_unsatisfiable(accept)


@pytest.mark.parametrize(
    'accept',
    [
        f'{_TYPE}; charset=utf-8',
        f'{_TYPE}; ext="x"; foo=bar',
        f'{_TYPE}; foo=bar, {_TYPE}; baz=1',
        f'{_TYPE}; foo=bar, application/json',
        f'{_TYPE.upper()}; FOO=bar',
        f'{_TYPE};foo="a,b"',
    ],
)
def test_unsatisfiable(accept: str) -> None:
    """Ensure that all instances with parameters are reported."""
    assert is_accept_unsatisfiable(accept)


def test_allowed_params() -> None:
    """Ensure that allowed parameters can be customized."""
    accept = f'{_TYPE}; foo=bar'
    assert is_accept_unsatisfiable(accept)
    assert not is_accept_unsatisfiable(accept, {'foo'})
