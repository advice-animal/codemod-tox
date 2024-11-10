from codemod_tox.utils import common_prefix, marklast


def test_marklast():
    assert list(marklast("abc")) == [("a", False), ("b", False), ("c", True)]


def test_common_prefix():
    assert common_prefix("", "") == ""
    assert common_prefix("a", "") == ""
    assert common_prefix("", "a") == ""
    assert common_prefix("a", "a") == "a"
    assert common_prefix("goal", "golf") == "go"
