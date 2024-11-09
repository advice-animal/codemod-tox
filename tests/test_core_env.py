import pytest
from codemod_tox.core import HoistError, ToxEnv, ToxOptions


def test_env():
    e = ToxEnv.parse("py3{8,9,10}")
    assert tuple(e.all()) == ("py38", "py39", "py310")
    assert str(e) == "py3{8,9,10}"


def test_multi_factor_env():
    e = ToxEnv.parse("{py27,py36}-django{15,16}")
    assert tuple(e.all()) == (
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


def test_only():
    e = ToxEnv.parse("py27")
    assert e.only("py27")
    assert not e.only("py2")
    assert not e.only("py271")


def test_add_env():
    e = ToxEnv.parse("py38")
    e = e.add("py39")
    assert str(e) == "py3{8,9}"
    e = e.add("py310")
    assert str(e) == "py3{8,9,10}"
    e = e.add("py")
    assert str(e) == "py{38,39,310,}"
    e = e.add("z")
    assert str(e) == "{py38,py39,py310,py,z}"


def test_add_env2():
    e = ToxEnv.parse("py38")
    # assert str(e) == "{py,}38"
    assert str(e.add("38")) == "{py38,38}"  # sub-optimal


def test_add_env3():
    e = ToxEnv.parse("py{38,39}-foo")
    assert str(e.add("py310-foo")) == "py{38,39,310}-foo"


def test_add_env4():
    e = ToxEnv.parse("py{38,39}-foo")
    assert str(e.add("py310-bar")) == "py{38-foo,39-foo,310-bar}"


def test_bucket():
    e = ToxEnv.parse("py38")
    assert e._bucket() == ("py38", None, "")
    e = ToxEnv.parse("py{38,39}")
    assert e._bucket() == ("py", ToxOptions(("38", "39")), "")
    e = ToxEnv.parse("pyx{38,39}{x}foo")
    assert e._bucket() == ("pyx", ToxOptions(("38", "39")), "xfoo")
