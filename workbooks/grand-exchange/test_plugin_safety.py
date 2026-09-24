#!/usr/bin/env python3
"""Plugin elements must survive retheming untouched.

Run: python3 workbooks/grand-exchange/test_plugin_safety.py
"""

from __future__ import annotations

import copy
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import runescape_theme as rt


def sample_document() -> dict:
    return {
        "elements": [
            {"id": "tbl", "kind": "table",
             "columns": [{"id": "c1", "name": "A"}],
             "style": {"backgroundColor": "#ffffff"}},
            {"id": "plug", "kind": "plugin", "pluginId": "abc-123",
             "displayName": "Map-Lite",
             "config": {"source": {"kind": "element", "elementId": "tbl"},
                        "config": "{\"stateFillColor\": \"#fbfbfb\"}"}},
            {"id": "box", "kind": "container", "elements": [
                {"id": "plug-nested", "kind": "plugin", "pluginId": "def-456",
                 "config": {"config": "{\"a\": 1}"}},
                {"id": "kpi", "kind": "kpi-chart"},
            ]},
        ]
    }


def plugins(document: dict) -> str:
    found = [e for e in rt.iter_elements(document) if e.get("kind") == "plugin"]
    found.sort(key=lambda e: e["id"])
    return json.dumps(found, sort_keys=True)


def test_plugins_survive_untouched() -> None:
    original = sample_document()
    source = copy.deepcopy(original)
    themed, restyled, skipped = rt.retheme_document(source)

    assert plugins(themed) == plugins(original), "a plugin element was modified"
    assert skipped == 2, f"expected 2 plugins skipped, got {skipped}"
    assert restyled >= 1, "nothing was restyled"
    assert source == original, "the live document was mutated in place"


def test_nested_plugins_are_found() -> None:
    ids = [e["id"] for e in rt.iter_elements(sample_document())
           if e.get("kind") == "plugin"]
    assert ids == ["plug", "plug-nested"], ids


def test_guard_detects_a_tampered_plugin() -> None:
    """The publish guard compares fingerprints; prove it is sensitive."""
    before = sample_document()
    after = sample_document()
    for element in rt.iter_elements(after):
        if element.get("kind") == "plugin":
            element["config"] = "tampered"
            break
    assert rt.plugin_fingerprint(before) != rt.plugin_fingerprint(after), (
        "fingerprint did not notice a changed plugin config"
    )


def test_non_plugin_elements_are_restyled() -> None:
    themed, _, _ = rt.retheme_document(sample_document())
    table = next(e for e in rt.iter_elements(themed) if e["id"] == "tbl")
    assert table["style"]["backgroundColor"] == rt.PARCHMENT
    assert table["tableStyle"]["banding"] == "hidden"


if __name__ == "__main__":
    for name, test in sorted(globals().items()):
        if name.startswith("test_") and callable(test):
            test()
            print(f"ok  {name}")
    print("\nplugin safety verified")
