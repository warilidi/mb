import json
from pathlib import Path

PACKAGE_DIR = Path(__file__).parent
LOCALES_DIR = PACKAGE_DIR / "data" / "locales"

_locales: dict[str, dict[str, str]] = {}


def load_locales(default_lang: str = "ru") -> dict[str, str]:
    if default_lang not in _locales:
        path = LOCALES_DIR / f"{default_lang}.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                _locales[default_lang] = json.load(f)
        else:
            _locales[default_lang] = {}
    return _locales[default_lang]


def t(key: str, lang: str = "ru", **kwargs) -> str:
    loc = load_locales(lang)
    template = loc.get(key, f"[{key}]")
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template
    return template
