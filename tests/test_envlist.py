import pytest
from codemod_tox.envlist import ToxEnvlist
from codemod_tox.exceptions import NoMatch


def test_envlist():
    e = ToxEnvlist.parse("a , b{c,d},")
    assert tuple(e) == ("a", "bc", "bd")


def test_trailing_comma():
    e = ToxEnvlist.parse("a,b")
    assert tuple(e) == ("a", "b")
    e = ToxEnvlist.parse("a,b,")
    assert tuple(e) == ("a", "b")
    assert str(e) == "a\nb"

    e = ToxEnvlist.parse("a , b , ")
    assert tuple(e) == ("a", "b")
    assert str(e) == "a\nb"

    e = ToxEnvlist.parse("a\nb\n")
    assert tuple(e) == ("a", "b")
    assert str(e) == "a\nb"

    e = ToxEnvlist.parse("a,b\nc")
    assert tuple(e) == ("a", "b", "c")
    assert str(e) == "a\nb\nc"


def test_changefirst():
    e = ToxEnvlist.parse("py37, style")
    result = e.changefirst(
        (lambda x: x.startswith("py3")),
        (lambda y: y | "py38"),
    )
    assert str(result) == "py3{7,8}\nstyle"
    with pytest.raises(NoMatch):
        e.changefirst(
            (lambda x: x.startswith("foo")),
            (lambda y: y | "py38"),
        )

    result = e.changefirst(
        (lambda x: x.startswith("py3")),
        (lambda y: None),
    )
    assert str(result) == "style"

    e = ToxEnvlist.parse("py{37,38}")
    result = e.changefirst(
        (lambda x: True),
        (lambda y: None),
    )
    assert str(result) == ""
