# codemod-tox

Handles parsing and modifying some basic `tox.ini` configuration strings.

```ini
# ToxEnvlist.parse("py{37,38}, style")
envlist = py{37,38}, style

# ToxEnv.parse("foo")
[toxenv:foo]

# ToxConditional.parse("-rrequirements.txt\nflask: flask>0")
deps = -rrequirements.txt
       flask: flask>0
```

You can then do basic modifications on them, or expand by iterating.

```pycon
>>> str(ToxEnv.parse("py37") | "py38")
"py3{7,8}"
>>> (ToxEnv.parse("py37") | "py38").startswith("py")
True
>>> list(ToxEnv.parse("py37") | "py38")
["py37", "py38"]
>>> str(ToxEnvlist.parse("py37, style").transform_matching(
...     (lambda x: x.startswith("py3")),
...     (lambda y: y | "py38"),
... ))
"py3{7,8}, style"
```

# Version Compat

Usage of this library should work back to 3.7, but development (and mypy
compatibility) only on 3.10-3.12.  Linting requires 3.12 for full fidelity.

# Versioning

This library follows [meanver](https://meanver.org/) which basically means
[semver](https://semver.org/) along with a promise to rename when the major
version changes.

# License

codemod-tox is copyright [Tim Hatch](https://timhatch.com/), and licensed under
the MIT license.  See the `LICENSE` file for details.
