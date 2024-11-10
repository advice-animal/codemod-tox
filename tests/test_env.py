import pytest
from codemod_tox.env import HoistError, ToxEnv
from codemod_tox.options import ToxOptions


def test_env():
    e = ToxEnv.parse("py3{8,9,10}")
    assert tuple(e) == ("py38", "py39", "py310")
    assert str(e) == "py3{8,9,10}"


def test_multi_factor_env():
    e = ToxEnv.parse("{py27,py36}-django{15,16}")
    assert tuple(e) == (
        "py27-django15",
        "py27-django16",
        "py36-django15",
        "py36-django16",
    )
    assert e.common_factors() == set()


def test_hoist_entire():
    assert str(ToxEnv.parse("x").hoist("x")) == "x"
    assert str(ToxEnv.parse("{x}").hoist("x")) == "x"
    assert str(ToxEnv.parse("{x,x2}").hoist("x")) == "x{,2}"


def test_hoist_errors():
    with pytest.raises(HoistError):
        ToxEnv.parse("abc").hoist("abcd")

    with pytest.raises(HoistError):
        ToxEnv.parse("abc").hoist("abx")

    with pytest.raises(HoistError):
        ToxEnv.parse("a{b,c}").hoist("ab")

    with pytest.raises(HoistError):
        ToxEnv.parse("{b}").hoist("a")


def test_hoist_env_starts_with_literal():
    e = ToxEnv.parse("p{y}{37,38}")
    e2 = e.hoist("py3")
    assert str(e2) == "py3{7,8}"


def test_hoist_env():
    e = ToxEnv.parse("{py27,py36}-django{15,16}")
    e2 = e.hoist("py")
    assert str(e2) == "py{27,36}-django{15,16}"


def test_bucket():
    assert ToxEnv.parse("abc")._bucket() == ("abc", ToxOptions(("",)), "")
    assert ToxEnv.parse("a{b}")._bucket() == ("ab", ToxOptions(("",)), "")
    assert ToxEnv.parse("{a,b}{c}d")._bucket() == ("", ToxOptions(("a", "b")), "cd")
    assert ToxEnv.parse("{a,b,c}")._bucket() == ("", ToxOptions(("a", "b", "c")), "")
    assert ToxEnv.parse("x{a,b,c}y")._bucket() == (
        "x",
        ToxOptions(("a", "b", "c")),
        "y",
    )
    with pytest.raises(HoistError):
        ToxEnv.parse("{a,b}-{c,d}")._bucket()


def test_or():
    assert str(ToxEnv.parse("py37") | "py38") == "py3{7,8}"
    assert str(ToxEnv.parse("py37") | "py38" | "py39") == "py3{7,8,9}"
    assert str(ToxEnv.parse("py37") | "py38" | "py27") == "py{37,38,27}"
    assert str(ToxEnv.parse("py37") | "py") == "py{37,}"
    assert str(ToxEnv.parse("{a,b}cd") | "cd") == "{a,b,}cd"
    assert str(ToxEnv.parse("{a,b}cd") | "xd") == "{ac,bc,x}d"
    # TODO requires trying with remaining left -> right if no right
    # This currently works but isn't minimal
    # assert str(ToxEnv.parse("acd") | "cd") == "{a,}cd"
