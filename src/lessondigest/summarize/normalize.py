from __future__ import annotations

import re

_SYMBOLS = {
    r"\cdot": "·",
    r"\times": "×",
    r"\pm": "±",
    r"\leq": "≤",
    r"\le": "≤",
    r"\geq": "≥",
    r"\ge": "≥",
    r"\neq": "≠",
    r"\ne": "≠",
    r"\approx": "≈",
    r"\rightarrow": "→",
    r"\to": "→",
    r"\alpha": "α",
    r"\beta": "β",
    r"\gamma": "γ",
    r"\delta": "δ",
    r"\Delta": "Δ",
    r"\pi": "π",
    r"\lambda": "λ",
    r"\mu": "μ",
    r"\sigma": "σ",
    r"\omega": "ω",
    r"\phi": "φ",
    r"\varphi": "φ",
}
_SYMBOLS_SORTED = sorted(_SYMBOLS.items(), key=lambda item: -len(item[0]))

_FRAC = re.compile(r"\\[dt]?frac\{([^{}]*)\}\{([^{}]*)\}")
_SQRT = re.compile(r"\\sqrt\{([^{}]*)\}")
_SUP_BRACE = re.compile(r"\^\{([^{}]*)\}")
_SUP = re.compile(r"\^([0-9n])")
_SUB_BRACE = re.compile(r"_\{([^{}]*)\}")
_SUB = re.compile(r"_([0-9])")
_BRACES = re.compile(r"\{([^{}]*)\}")
_DROP = re.compile(r"\\(?:left|right|quad|qquad|,|;|!|\s)")

_SUPERSCRIPTS = {"0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵"}
_SUBSCRIPTS = {
    "0": "₀",
    "1": "₁",
    "2": "₂",
    "3": "₃",
    "4": "₄",
    "5": "₅",
    "6": "₆",
    "7": "₇",
    "8": "₈",
    "9": "₉",
}

_BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")
_MULTISPACE = re.compile(r"[ \t\u00a0]+")


def normalize_math(text: str) -> str:
    if not text:
        return text
    result = text
    for latex, symbol in _SYMBOLS_SORTED:
        result = result.replace(latex, symbol)
    result = _DROP.sub("", result)

    for _ in range(4):
        result, changed = _FRAC.subn(r"\1 / \2", result)
        if not changed:
            break
    for _ in range(4):
        result, changed = _SQRT.subn(r"√(\1)", result)
        if not changed:
            break

    result = _SUP_BRACE.sub(_replace_superscript, result)
    result = _SUP.sub(lambda m: _SUPERSCRIPTS.get(m.group(1), "^" + m.group(1)), result)
    result = _SUB_BRACE.sub(_replace_subscript, result)
    result = _SUB.sub(lambda m: _SUBSCRIPTS.get(m.group(1), "_" + m.group(1)), result)
    result = _BRACES.sub(r"\1", result)

    result = result.replace("$", "")
    result = result.replace("\u2212", "-")
    result = _MULTISPACE.sub(" ", result)
    return result.strip()


def normalize_text(text: str) -> str:
    if not text:
        return text
    result = text.replace("`", "").replace("**", "").replace("__", "")
    result = _BULLET.sub("", result)
    result = _MULTISPACE.sub(" ", result)
    return result.strip()


def normalize_field(text: str) -> str:
    return normalize_text(normalize_math(text))


def _replace_superscript(match: re.Match[str]) -> str:
    content = match.group(1).strip()
    if len(content) == 1:
        return _SUPERSCRIPTS.get(content, "^" + content)
    return "^" + content


def _replace_subscript(match: re.Match[str]) -> str:
    parts = [part.strip() for part in match.group(1).split(",")]
    rendered: list[str] = []
    for part in parts:
        if part and all(ch in _SUBSCRIPTS for ch in part):
            rendered.append("".join(_SUBSCRIPTS[ch] for ch in part))
        else:
            rendered.append("_" + part)
    return ",".join(rendered)
