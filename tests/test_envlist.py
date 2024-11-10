from codemod_tox.envlist import ToxEnvlist


def test_envlist():
    e = ToxEnvlist.parse("a , b{c,d},")
    assert tuple(e.all()) == ("a", "bc", "bd")


def test_trailing_comma():
    e = ToxEnvlist.parse("a,b")
    assert tuple(e.all()) == ("a", "b")
    e = ToxEnvlist.parse("a,b,")
    assert tuple(e.all()) == ("a", "b")
    assert str(e) == "a\nb"

    e = ToxEnvlist.parse("a , b , ")
    assert tuple(e.all()) == ("a", "b")
    assert str(e) == "a\nb"

    e = ToxEnvlist.parse("a\nb\n")
    assert tuple(e.all()) == ("a", "b")
    assert str(e) == "a\nb"

    e = ToxEnvlist.parse("a,b\nc")
    assert tuple(e.all()) == ("a", "b", "c")
    assert str(e) == "a\nb\nc"
