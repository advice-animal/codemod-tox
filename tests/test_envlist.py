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
    assert str(e) == "a,b"

    e = ToxEnvlist.parse("a , b , ")
    assert tuple(e) == ("a", "b")
    assert str(e) == "a, b"

    e = ToxEnvlist.parse("a\nb\n")
    assert tuple(e) == ("a", "b")
    assert str(e) == "\na\nb"

    e = ToxEnvlist.parse("a,b\nc")
    assert tuple(e) == ("a", "b", "c")
    assert str(e) == "\na\nb\nc"


def test_transform_matching():
    e = ToxEnvlist.parse("py37, style")
    result = e.transform_matching(
        (lambda x: x.startswith("py3")),
        (lambda y: y | "py38"),
    )
    assert str(result) == "py3{7,8}, style"
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
    assert str(result) == "py3{7,10}, tests, style, py38, py39"

    result = e.transform_matching(
        (lambda x: x.startswith("py3")),
        (lambda y: y | "py310"),
        max=2,
    )
    assert str(result) == "py3{7,10}, tests, style, py3{8,10}, py39"

    result = e.transform_matching(
        (lambda x: x.startswith("py3")),
        (lambda y: y | "py310"),
        max=None,
    )
    assert str(result) == "py3{7,10}, tests, style, py3{8,10}, py3{9,10}"


def test_add_numeric_option_to_envlist():
    e = ToxEnvlist.parse("py3{9}")
    result = e.add_numeric_option("py312")
    assert str(result) == "py3{9,12}"

    e = ToxEnvlist.parse("py3{9,10,11}, py3{9,10,11}t, style")
    result = e.add_numeric_option("py312")
    assert str(result) == "py3{9,10,11,12}, py3{9,10,11}t, style"

    e = ToxEnvlist.parse("py3{9,10,11}, style")
    result = e.add_numeric_option("py312t")
    assert str(result) == "py3{9,10,11}, style, py312t"

    e = ToxEnvlist.parse("py3{9,10,11},\npy3{9,10,11}t, style")
    result = e.add_numeric_option("py312t")
    assert str(result) == "\npy3{9,10,11}\npy3{9,10,11,12}t\nstyle"

    e = ToxEnvlist.parse("py3{9,10}, style")
    result = e.add_numeric_option("py311")
    assert str(result) == "py3{9,10,11}, style"

    e = ToxEnvlist.parse("py3{9,10}-django{5,6}-cov{6,7}, style")
    result = e.add_numeric_option("py311")
    assert str(result) == "py3{9,10,11}-django{5,6}-cov{6,7}, style"

    e = ToxEnvlist.parse("py3{9,10}-django{5,6}-cov{6,7}, py3{9,10}-nocov, style")
    result = e.add_numeric_option("py311")
    assert str(result) == "py3{9,10,11}-django{5,6}-cov{6,7}, py3{9,10,11}-nocov, style"

    e = ToxEnvlist.parse("py37,py310,linters")
    result = e.add_numeric_option("py313")
    assert str(result) == "py37,py310,linters,py313"

    e = ToxEnvlist.parse("py3{6,10},py37,linters")
    result = e.add_numeric_option("py313")
    assert str(result) == "py3{6,10,13},py37,linters"
