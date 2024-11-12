import pytest
from codemod_tox.options import ToxOptions


def test_options_roundtrip():
    assert str(ToxOptions.parse("{x}")) == "{x}"
    assert str(ToxOptions.parse("{ x }")) == "{x}"
    assert str(ToxOptions.parse("{ x , y }")) == "{x,y}"


def test_options():
    o = ToxOptions.parse("{a,b,c}")
    assert o.options == ("a", "b", "c")
    assert tuple(o) == ("a", "b", "c")
    assert not o.startswith("a")
    assert o.common_prefix() == ""


def test_options2():
    o = ToxOptions.parse("{301,302}")
    assert o.startswith("3")
    assert o.startswith("30")
    assert not o.startswith("301")
    assert o.common_prefix() == "30"
    assert str(o) == "{301,302}"

    o2 = o.removeprefix("3")
    assert tuple(o2) == ("01", "02")
    assert str(o2) == "{01,02}"


def test_options3():
    o = ToxOptions.parse("{py37-tests,py38-tests}")
    with pytest.raises(AssertionError):
        o.removeprefix("x")
    with pytest.raises(AssertionError):
        o.removesuffix("x")
    assert tuple(o.removeprefix("py")) == ("37-tests", "38-tests")
    assert tuple(o.removesuffix("-tests")) == ("py37", "py38")
