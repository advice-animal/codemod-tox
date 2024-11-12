from codemod_tox.conditional import ToxConditional
from codemod_tox.env import ToxEnv
from codemod_tox.options import ToxOptions

DEPS_EXAMPLE = """\
-rrequirements.txt
flask: flask>0
fastapi: fastapi>0"""


def test_conditional():
    c = ToxConditional.parse(DEPS_EXAMPLE)
    assert c.lines == (
        (None, "-rrequirements.txt"),
        (ToxEnv(("flask",)), "flask>0"),
        (ToxEnv(("fastapi",)), "fastapi>0"),
    )
    assert str(c) == DEPS_EXAMPLE
    assert c.evaluate("py38") == "-rrequirements.txt"
    # Don't accidentally substring match, only full factors
    assert c.evaluate("py38-zflask-zfastapi") == "-rrequirements.txt"
    assert c.evaluate("py38-flask") == "-rrequirements.txt\nflask>0"
    assert c.evaluate("py38-flask-fastapi") == "-rrequirements.txt\nflask>0\nfastapi>0"


def test_conditional_expands():
    c = ToxConditional.parse("{lint, tests}: x")
    assert str(c) == "{lint,tests}: x"
    assert c.lines == (
        # (force line break)
        (ToxEnv((ToxOptions(("lint", "tests")),)), "x"),
    )
    assert c.evaluate("foo") == ""
    assert c.evaluate("foo-tests") == "x"
