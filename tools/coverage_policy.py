"""
Coverage policy gate for utils modules.

Policy:
- Core modules must meet a minimum coverage threshold.
- UI-heavy modules must not regress below the stored baseline.
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Tuple


def _normalize_module_name(raw_filename: str) -> str:
    normalized = raw_filename.replace("\\", "/")
    if not normalized.startswith("utils/"):
        normalized = f"utils/{normalized}"
    return normalized


def load_module_coverage(coverage_xml: Path) -> Dict[str, float]:
    root = ET.parse(coverage_xml).getroot()
    module_coverage: Dict[str, float] = {}
    for class_node in root.findall(".//class"):
        filename = class_node.attrib.get("filename", "")
        module_name = _normalize_module_name(filename)
        line_rate = float(class_node.attrib.get("line-rate", "0"))
        module_coverage[module_name] = line_rate * 100.0
    return module_coverage


def evaluate_policy(policy: dict, module_coverage: Dict[str, float]) -> Tuple[list[str], list[str], list[str]]:
    core_threshold = float(policy["core_threshold_percent"])
    core_modules = list(policy.get("core_modules", []))
    ui_baseline = dict(policy.get("ui_baseline_percent", {}))

    missing_modules: list[str] = []
    core_failures: list[str] = []
    ui_regressions: list[str] = []

    for module in core_modules:
        if module not in module_coverage:
            missing_modules.append(module)
            continue
        current = module_coverage[module]
        if current + 1e-9 < core_threshold:
            core_failures.append(f"{module}: {current:.2f}% < {core_threshold:.2f}%")

    for module, baseline in ui_baseline.items():
        if module not in module_coverage:
            missing_modules.append(module)
            continue
        current = module_coverage[module]
        if current + 1e-9 < float(baseline):
            ui_regressions.append(f"{module}: {current:.2f}% < baseline {float(baseline):.2f}%")

    return missing_modules, core_failures, ui_regressions


def update_ui_baseline(policy: dict, module_coverage: Dict[str, float]) -> dict:
    updated = dict(policy)
    current_baseline = dict(updated.get("ui_baseline_percent", {}))
    for module in current_baseline.keys():
        if module in module_coverage:
            current_baseline[module] = round(module_coverage[module], 2)
    updated["ui_baseline_percent"] = current_baseline
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Enforce coverage policy for core and UI modules.")
    parser.add_argument("--coverage-xml", default="coverage.xml", help="Path to coverage.xml")
    parser.add_argument("--policy-file", default="coverage_policy.json", help="Path to policy JSON file")
    parser.add_argument(
        "--update-ui-baseline",
        action="store_true",
        help="Refresh ui_baseline_percent values in the policy file from current coverage",
    )
    args = parser.parse_args()

    coverage_path = Path(args.coverage_xml)
    policy_path = Path(args.policy_file)

    if not coverage_path.exists():
        print(f"[coverage-policy] Missing coverage XML: {coverage_path}")
        return 2
    if not policy_path.exists():
        print(f"[coverage-policy] Missing policy file: {policy_path}")
        return 2

    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    module_coverage = load_module_coverage(coverage_path)

    if args.update_ui_baseline:
        updated = update_ui_baseline(policy, module_coverage)
        policy_path.write_text(json.dumps(updated, indent=2) + "\n", encoding="utf-8")
        print(f"[coverage-policy] Updated UI baseline values in {policy_path}")
        return 0

    missing_modules, core_failures, ui_regressions = evaluate_policy(policy, module_coverage)

    print("[coverage-policy] Core threshold:", policy["core_threshold_percent"])
    print("[coverage-policy] Core modules checked:", len(policy.get("core_modules", [])))
    print("[coverage-policy] UI modules checked:", len(policy.get("ui_baseline_percent", {})))

    if missing_modules:
        print("[coverage-policy] Missing modules in coverage report:")
        for item in sorted(set(missing_modules)):
            print(" -", item)

    if core_failures:
        print("[coverage-policy] Core threshold failures:")
        for item in core_failures:
            print(" -", item)

    if ui_regressions:
        print("[coverage-policy] UI coverage regressions:")
        for item in ui_regressions:
            print(" -", item)

    if missing_modules or core_failures or ui_regressions:
        return 1

    print("[coverage-policy] PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
