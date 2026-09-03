#!/usr/bin/env python3
"""Repair functional defects in the live OneMedNet Sigma workbook.

The script fetches the current workbook before transforming it, so it preserves
unrelated UI edits. It is dry-run by default; pass --publish to PUT the repaired
document after a version-safety check.
"""

from __future__ import annotations

import argparse
import base64
import copy
import json
import pathlib
import re
import urllib.error
import urllib.parse
import urllib.request


WORKBOOK_ID = "7d65161f-037e-4ea9-a156-32d6d0f63dde"
DEFAULT_EXPECTED_VERSION = 11

CARD_COLORS = {
    "a": "#1c244b",
    "b": "#22305c",
    "c": "#324a6d",
    "d": "#131a38",
    "e": "#1c244b",
    "f": "#22305c",
}

DEMO_SCOPE_COPY = (
    "This proof-of-value uses deterministic synthetic records generated in "
    "Snowflake; it does not contain production OneMedNet patient data. "
    "Pseudonymous identifiers, age capping, per-patient date shifting and "
    "small-cell handling demonstrate the intended policy design. Production "
    "license enforcement belongs in governed warehouse policies and inherited "
    "row-level security—not in a workbook filter. The controls on this page are "
    "analytical filters, not security boundaries."
)


def read_env(path: pathlib.Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


class SigmaApi:
    def __init__(self, env: dict[str, str]):
        self.base = (
            env.get("SIGMA_PAPERCRANE_API_BASE")
            or env.get("SIGMA_API_BASE")
            or env.get("SIGMA_BASE_URL")
        )
        client_id = (
            env.get("SIGMA_PAPERCRANE_CLIENT_ID") or env.get("SIGMA_CLIENT_ID")
        )
        client_secret = (
            env.get("SIGMA_PAPERCRANE_CLIENT_SECRET")
            or env.get("SIGMA_CLIENT_SECRET")
        )
        if not self.base or not client_id or not client_secret:
            raise RuntimeError("Sigma base URL, client id, and client secret are required")

        credentials = base64.b64encode(
            f"{client_id}:{client_secret}".encode()
        ).decode()
        request = urllib.request.Request(
            self.base + "/v2/auth/token",
            data=urllib.parse.urlencode({"grant_type": "client_credentials"}).encode(),
            headers={
                "Authorization": "Basic " + credentials,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=40) as response:
            self.token = json.load(response)["access_token"]

    def call(self, method: str, path: str, body=None):
        data = json.dumps(body).encode() if body is not None else None
        headers = {
            "Authorization": "Bearer " + self.token,
            "Accept": "application/json",
        }
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self.base + path, data=data, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=240) as response:
                raw = response.read().decode()
        except urllib.error.HTTPError as exc:
            raise RuntimeError(
                f"Sigma {method} {path} failed ({exc.code}): "
                + exc.read().decode()[:2000]
            ) from None
        if not raw:
            return None
        try:
            return json.loads(raw)
        except ValueError:
            return raw


def add_filter(control: dict, table_id: str, column_id: str) -> None:
    filters = control.setdefault("filters", [])
    candidate = {
        "source": {"kind": "table", "elementId": table_id},
        "columnId": column_id,
    }
    if candidate not in filters:
        filters.append(candidate)


def make_eligibility_formula(elements: dict[str, dict]) -> str:
    cohort_formula = elements["k-p4ac"]["columns"][0]["formula"]
    patient_cohort = elements["pt_elig"]
    prefix = "CountDistinct(If("
    suffix = ", [Patient Base/Patient Pseudo ID], Null))"
    if not cohort_formula.startswith(prefix) or not cohort_formula.endswith(suffix):
        raise RuntimeError("Projected-cohort formula shape changed; refusing unsafe edit")
    condition = cohort_formula[len(prefix) : -len(suffix)]
    raw_by_name = {
        column["name"]: column["formula"]
        for column in patient_cohort["columns"]
        if column.get("name") and column.get("formula", "").startswith("[Custom SQL/")
    }

    def raw_reference(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in raw_by_name:
            raise RuntimeError(f"Patient Cohort is missing required field: {name}")
        return raw_by_name[name]

    condition = re.sub(r"\[Patient Base/([^\]]+)\]", raw_reference, condition)
    return f'If({condition}, "Yes", "No")'


def place_hidden_control(layout: str) -> str:
    if 'elementId="elig-filter"' in layout:
        return layout
    page_match = re.search(
        r'(<Page\b[^>]*\bid="util"[^>]*>)(.*?)(</Page>)', layout, flags=re.DOTALL
    )
    if not page_match:
        raise RuntimeError("Hidden Model plumbing page is missing from layout")
    body = page_match.group(2)
    rows = [int(value) for value in re.findall(r'gridRow="\d+ / (\d+)"', body)]
    start = max(rows or [1]) + 1
    placement = (
        f'\n  <Element elementId="elig-filter" gridColumn="1 / 7" '
        f'gridRow="{start} / {start + 3}"/>\n'
    )
    return (
        layout[: page_match.start(3)]
        + placement
        + layout[page_match.start(3) :]
    )


def transform(live_spec: dict) -> dict:
    document = copy.deepcopy(live_spec["document"])
    element_list = document["elements"]
    elements = {element["id"]: element for element in element_list}

    # Make every KPI card self-contained and high contrast. The previous KPI
    # tiles inherited a white surface while their labels and values were white.
    for page in range(1, 5):
        for letter, color in CARD_COLORS.items():
            container = elements.get(f"c-p{page}{letter}")
            if not container:
                continue
            container.pop("backgroundImage", None)
            container.setdefault("style", {}).update(
                {"backgroundColor": color, "borderRadius": "round"}
            )
            for suffix in ("c", "p"):
                kpi = elements.get(f"k-p{page}{letter}{suffix}")
                if kpi:
                    kpi.setdefault("style", {}).update(
                        {"backgroundColor": color, "padding": "none"}
                    )
                    kpi.setdefault("value", {})["color"] = "#ffffff"
                    kpi.setdefault("name", {})["color"] = (
                        "#ffffff" if suffix == "c" else "#c8deff"
                    )
            spark = elements.get(f"ln-p{page}{letter}")
            if spark:
                spark.setdefault("style", {}).update(
                    {"backgroundColor": color, "padding": "none"}
                )

    # Replace the no-op customer selector with an honest, non-interactive scope
    # label. Production identity/RLS cannot be emulated securely by a UI filter.
    customer = elements["ctrl-cust"]
    customer.clear()
    customer.update(
        {
            "id": "ctrl-cust",
            "kind": "text",
            "body": (
                "**Demo audience:** Quantitative investment fund  \n"
                "Aggregate synthetic data · no patient-level rows or DICOM pixels"
            ),
            "verticalAlign": "middle",
        }
    )

    # Page 1 filters now reach all compatible source marts, not only one tab.
    for table_id, column_id in (
        ("mart_prescriber", "px-ta"),
        ("mart_signal", "sg-ta"),
        ("mart_ae", "ae-ta"),
        ("mart_bodymap", "bm-ta"),
    ):
        add_filter(elements["ctrl-ta"], table_id, column_id)
    for table_id, column_id in (
        ("mart_signal", "sg-cls"),
        ("mart_ae", "ae-cls"),
    ):
        add_filter(elements["ctrl-cls"], table_id, column_id)

    # Site names and IDs were mixed in one filter. Use the shared site ID across
    # all three source marts so a selection cannot silently empty one tab.
    site = elements["ctrl-site"]
    site["name"] = "Contributing site ID"
    site["source"] = {
        "kind": "source",
        "source": {"kind": "table", "elementId": "mart_util"},
        "columnId": "ut-site",
    }
    site["filters"] = [
        {
            "source": {"kind": "table", "elementId": "mart_util"},
            "columnId": "ut-site",
        },
        {
            "source": {"kind": "table", "elementId": "mart_ops"},
            "columnId": "op-site",
        },
        {
            "source": {"kind": "table", "elementId": "mart_contrib"},
            "columnId": "ct-site",
        },
    ]

    # Encounter class was a no-op "All" segmented control. A source-backed list
    # has a true unfiltered state and filters both Throughput visualizations.
    encounter = elements["ctrl-enc"]
    encounter.update(
        {
            "controlType": "list",
            "mode": "include",
            "selectionMode": "multiple",
            "values": [],
            "source": {
                "kind": "source",
                "source": {"kind": "table", "elementId": "mart_util"},
                "columnId": "ut-cls",
            },
            "filters": [
                {
                    "source": {"kind": "table", "elementId": "mart_util"},
                    "columnId": "ut-cls",
                }
            ],
        }
    )
    encounter.pop("value", None)

    # Life-sciences filters now cover therapy journeys and implant/PRO outcomes.
    add_filter(elements["ctrl-ta3"], "mart_prom", "pm-ta")
    add_filter(elements["ctrl-dx3"], "mart_prom", "pm-dxl")
    line_step = elements["ctrl-line"]
    line_step["filters"] = [
        {
            "source": {"kind": "table", "elementId": "mart_journey"},
            "columnId": "jn-fl",
        }
    ]

    # Start the trial modeler in a coherent, non-zero oncology scenario.
    elements["c4-ta"]["value"] = "Oncology"
    elements["c4-dx"]["value"] = "C34.90"
    elements["k-p4bc"]["columns"][0]["format"] = {
        "kind": "number",
        "formatString": ".1%",
    }

    # Scope Cohort Detail to the same criteria used by the headline KPI. A
    # hidden "Yes" filter on the calculated eligibility column cascades to the
    # child detail table and also narrows the Focus site choices.
    patient_cohort = elements["pt_elig"]
    eligibility_formula = make_eligibility_formula(elements)
    existing_eligibility = next(
        (column for column in patient_cohort["columns"] if column["id"] == "pe-ok"),
        None,
    )
    eligibility_column = {
        "id": "pe-ok",
        "formula": eligibility_formula,
        "name": "Eligible under current protocol",
    }
    if existing_eligibility:
        existing_eligibility.update(eligibility_column)
    else:
        patient_cohort["columns"].append(eligibility_column)
        patient_cohort.setdefault("order", []).append("pe-ok")

    if "elig-filter" not in elements:
        eligibility_control = {
            "id": "elig-filter",
            "kind": "control",
            "controlId": "EligibilityScope",
            "name": "Eligibility scope",
            "controlType": "segmented",
            "source": {
                "kind": "manual",
                "valueType": "text",
                "values": ["Yes"],
            },
            "value": "Yes",
            "filters": [
                {
                    "source": {"kind": "table", "elementId": "pt_elig"},
                    "columnId": "pe-ok",
                }
            ],
        }
        element_list.append(eligibility_control)
        elements["elig-filter"] = eligibility_control
    document["layout"] = place_hidden_control(document["layout"])

    # Make writeback language match what the action actually persists.
    save_button = elements["b4-save"]
    save_button["text"] = "Save protocol settings"
    save_effect = save_button["actions"][0]["effects"][0]
    save_effect["values"].setdefault(
        "pl-pr",
        {
            "type": "constant",
            "value": {"type": "text", "value": "Ad hoc feasibility scenario"},
        },
    )

    # Replace claims of already-enforced production RLS with accurate POV scope.
    for page in range(1, 5):
        elements[f"gov-hd{page}"]["body"] = "**Data safeguards & demo scope**"
        elements[f"gov-tx{page}"]["body"] = DEMO_SCOPE_COPY
    license_table = elements["lictab"]
    license_table["name"]["text"] = (
        "Illustrative license policy matrix — production enforcement occurs upstream"
    )

    validate(document)
    return {"document": document}


def validate(document: dict) -> None:
    elements = {element["id"]: element for element in document["elements"]}
    assert elements["ctrl-cust"]["kind"] == "text"
    assert elements["c4-ta"]["value"] == "Oncology"
    assert elements["c4-dx"]["value"] == "C34.90"
    assert elements["ctrl-enc"]["filters"]
    assert elements["ctrl-line"]["filters"]
    assert any(column["id"] == "pe-ok" for column in elements["pt_elig"]["columns"])
    assert elements["elig-filter"]["value"] == "Yes"
    assert 'elementId="elig-filter"' in document["layout"]
    assert "Scope is enforced by an inner join" not in json.dumps(document)
    assert "CustomerScope" not in json.dumps(document)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--env-file",
        type=pathlib.Path,
        default=pathlib.Path("/workspace/.env"),
    )
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--expected-version", type=int, default=DEFAULT_EXPECTED_VERSION)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()

    api = SigmaApi(read_env(args.env_file))
    meta = api.call("GET", f"/v2/workbooks/{WORKBOOK_ID}")
    live_spec = api.call("GET", f"/v2/workbooks/{WORKBOOK_ID}/spec")
    payload = transform(live_spec)

    if args.output:
        args.output.write_text(json.dumps(payload, indent=2) + "\n")
        print(f"Wrote transformed spec to {args.output}")

    print(
        f"Prepared {live_spec['name']} from live version "
        f"{meta['latestVersion']} ({len(payload['document']['elements'])} elements)"
    )
    if not args.publish:
        print("Dry run complete; no workbook changes were made.")
        return
    if meta["latestVersion"] != args.expected_version:
        raise RuntimeError(
            f"Live version is {meta['latestVersion']}, expected "
            f"{args.expected_version}; refusing to overwrite newer edits"
        )

    result = api.call(
        "PUT", f"/v2/workbooks/{WORKBOOK_ID}/spec", payload
    )
    updated = api.call("GET", f"/v2/workbooks/{WORKBOOK_ID}")
    print("PUT result:", json.dumps(result, default=str)[:1000])
    print("Published version:", updated["latestVersion"])


if __name__ == "__main__":
    main()
