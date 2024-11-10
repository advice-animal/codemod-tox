from codemod_tox.conditional import ToxConditional
from codemod_tox.env import ToxEnv
from codemod_tox.options import ToxOptions


def test_conditional():
    c = ToxConditional.parse("x\ny: z")
    assert c.lines == (
        (None, "x"),
        (ToxEnv(("y",)), "z"),
    )
    assert str(c) == "x\ny: z"
    assert c.evaluate("foo") == "x"
    assert c.evaluate("yy") == "x"
    assert c.evaluate("y") == "x\nz"
    assert c.evaluate("foo-y") == "x\nz"


def test_conditional_expands():
    c = ToxConditional.parse("{lint, tests}: x")
    assert str(c) == "{lint,tests}: x"
    assert c.lines == (
        # (force line break)
        (ToxEnv((ToxOptions(("lint", "tests")),)), "x"),
    )
    assert c.evaluate("foo") == ""
    assert c.evaluate("foo-tests") == "x"
