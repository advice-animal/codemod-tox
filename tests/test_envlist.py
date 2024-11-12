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


def test_transform_matching():
    e = ToxEnvlist.parse("py37, style")
    result = e.transform_matching(
        (lambda x: x.startswith("py3")),
        (lambda y: y | "py38"),
    )
    assert str(result) == "py3{7,8}\nstyle"
    with pytest.raises(NoMatch):
        e.transform_matching(
            (lambda x: x.startswith("foo")),
            (lambda y: y | "py38"),
        )

    result = e.transform_matching(
        (lambda x: x.startswith("py3")),
        (lambda y: None),
    )
    assert str(result) == "style"

    e = ToxEnvlist.parse("py{37,38}")
    result = e.transform_matching(
        (lambda x: True),
        (lambda y: None),
    )
    assert str(result) == ""


def test_transform_matching_max():
    e = ToxEnvlist.parse("py37, tests, style, py38, py39")
    result = e.transform_matching(
        (lambda x: x.startswith("py3")),
        (lambda y: y | "py310"),
    )
    assert str(result) == "py3{7,10}\ntests\nstyle\npy38\npy39"

    result = e.transform_matching(
        (lambda x: x.startswith("py3")),
        (lambda y: y | "py310"),
        max=2,
    )
    assert str(result) == "py3{7,10}\ntests\nstyle\npy3{8,10}\npy39"

    result = e.transform_matching(
        (lambda x: x.startswith("py3")),
        (lambda y: y | "py310"),
        max=None,
    )
    assert str(result) == "py3{7,10}\ntests\nstyle\npy3{8,10}\npy3{9,10}"
