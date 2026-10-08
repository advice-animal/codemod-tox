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

# Version Compatibility

Python 3.10+.

# Versioning

This library follows [meanver](https://meanver.org/) which basically means
[semver](https://semver.org/) along with a promise to rename when the major
version changes.

# Changelog

## Unreleased

A single-valued factor like `{py312}` used to cause an assert. This is now fixed.

## v0.5.5 – 2026-10-02

`add_numeric_option` will now put the new option after other numeric options
that have the same alphabetic prefix. This helps keep true test environments
in the same execution position relative to combining environments like "coverage".

# License

codemod-tox is copyright [Tim Hatch](https://timhatch.com/), and licensed under
the MIT license.  See the `LICENSE` file for details.

# Maintenance

## Running tests

Create a venv with `make venv`, then activate the venv and use `make test`.

## Publishing

The library is published to PyPI with Trusted Publishing. To release the latest code:

- Update the version and date in the changelog in README.md and commit the change.
- Create and push a tag in the pattern `vM.m.p` like `v1.2.3`.
- A GitHub action will publish to PyPI.
