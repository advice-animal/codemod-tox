import pytest
from codemod_tox.env import HoistError, ToxEnv
from codemod_tox.exceptions import NoFactorMatch
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
    assert str(ToxEnv.parse("acd") | "cd") == "{a,}cd"


def test_add_numeric_option():
    assert (
        str(ToxEnv.parse("py{39,310}").add_numeric_option("py311")) == "py{39,310,311}"
    )
    assert str(ToxEnv.parse("py3{9,10}").add_numeric_option("py311")) == "py3{9,10,11}"
    assert str(ToxEnv("py{39,310}").add_numeric_option("py310")) == "py{39,310}"
    assert (
        str(ToxEnv.parse("py3{9,10}-foo{3,4}").add_numeric_option("py311"))
        == "py3{9,10,11}-foo{3,4}"
    )
    assert (
        str(ToxEnv.parse("py3{9,10}-foo{3,4}-bar").add_numeric_option("py311"))
        == "py3{9,10,11}-foo{3,4}-bar"
    )
    assert (
        str(ToxEnv.parse("py3{9,10}t-foo{3,4}-bar").add_numeric_option("py311t"))
        == "py3{9,10,11}t-foo{3,4}-bar"
    )
    assert (
        str(ToxEnv.parse("py3{9,10}-foo{3,4}").add_numeric_option("foo5"))
        == "py3{9,10}-foo{3,4,5}"
    )
    assert (
        str(ToxEnv.parse("py3{9,10}-foo{34,35}").add_numeric_option("foo36"))
        == "py3{9,10}-foo{34,35,36}"
    )
    assert (
        str(ToxEnv.parse("py3{10,11,12}").add_numeric_option("py313"))
        == "py3{10,11,12,13}"
    )
    assert (
        str(ToxEnv.parse("py310-b-c").add_numeric_option("py311")) == "py{310,311}-b-c"
    )
    assert (
        str(ToxEnv.parse("a-py310-b-c").add_numeric_option("py311"))
        == "a-py{310,311}-b-c"
    )
    assert (
        str(ToxEnv.parse("py3{10,11}-py3{10,11}-py311").add_numeric_option("py312"))
        == "py3{10,11,12}-py3{10,11}-py311"
    )


def test_add_numeric_option_errors():
    with pytest.raises(NoFactorMatch):
        ToxEnv.parse("abc").add_numeric_option("xyz")
    with pytest.raises(NoFactorMatch):
        ToxEnv.parse("py{a,b}").add_numeric_option("py3")
    # Value remaining after prefix is not numeric
    with pytest.raises(NoFactorMatch):
        ToxEnv.parse("py{39,310}").add_numeric_option("pyabc")
    # Literal factor, value suffix not numeric
    with pytest.raises(NoFactorMatch):
        ToxEnv.parse("py310").add_numeric_option("pyabc")
    # Literal factor, different prefix
    with pytest.raises(NoFactorMatch):
        ToxEnv.parse("py310").add_numeric_option("foo311")
    # Suffix on new value finds no match
    with pytest.raises(NoFactorMatch):
        ToxEnv.parse("py3{9,10}-foo{3,4}-bar").add_numeric_option("py311t")
    # Original values have non-numeric options
    with pytest.raises(NoFactorMatch):
        ToxEnv.parse("p{y39,x39}").add_numeric_option("py310")
    # The environment must have a prefix
    with pytest.raises(NoFactorMatch):
        ToxEnv.parse("py310").add_numeric_option("311")
    with pytest.raises(NoFactorMatch):
        ToxEnv.parse("310").add_numeric_option("311")


def test_one():
    with pytest.raises(ValueError):
        ToxEnv.parse("py{37,38}").one()
    assert ToxEnv.parse("py{37}").one() == "py37"
    assert ToxEnv.parse("py{37,37}").one() == "py37"


def test_endswith():
    assert ToxEnv.parse("py37").endswith("37")
    assert ToxEnv.parse("py{37}").endswith("37")
    assert not ToxEnv.parse("py{37}").endswith("38")
    assert ToxEnv.parse("{py,zz}{37,37}").endswith("37")
    assert not ToxEnv.parse("{py,zz}{37,37}").endswith("38")


def test_only():
    assert ToxEnv.parse("py37").only("py37")
    assert not ToxEnv.parse("py37").only("py38")
    assert not ToxEnv.parse("py37").only("py")

    assert ToxEnv.parse("py{37,37}").only("py37")
    assert not ToxEnv.parse("py{37,38}").only("py37")
