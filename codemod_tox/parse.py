import re

TOX_ENV_TOKEN_RE = re.compile(
    r"(?P<comma>,[ \t]*)|(?P<newline>\n)|(?P<space>[ \t]+)|(?P<literal>[A-Za-z0-9_-]+)|(?P<options>\{[^{}]+\})"
)
TOX_CONDITIONAL_RE = re.compile(
    r"\s*(?P<condition>(?:,|[A-Za-z0-9_-]+|\{[^{}]+\})+)\s*:\s*(?P<line>.*)"
)
PY_FACTOR_RE = re.compile(r"^py(3\d+)")
