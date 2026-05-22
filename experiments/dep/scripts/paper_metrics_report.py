#!/usr/bin/env python3

import argparse
import csv
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse


DEP_TAGS = {"form", "input", "textarea", "select", "button"}
RUN_LABELS = {"baseline", "dep"}


class PageParser(HTMLParser):
    def __init__(self, base_url=""):
        super().__init__()
        self.base_url = base_url
        self.deps = set()
        self.links = set()
        self.js_sources = set()
        self.form_stack = []

    def handle_starttag(self, tag, attrs):
        attrs = {name.lower(): (value or "").strip() for name, value in attrs}
        lower_attrs = {name: value.lower() for name, value in attrs.items()}
        tag = tag.lower()

        if tag == "a":
            self.add_link(attrs.get("href", ""))
        elif tag == "form":
            action = attrs.get("action", "")
            method = lower_attrs.get("method", "")
            self.add_link(action)
            form = (method, normalize_url(action, self.base_url))
            self.form_stack.append(form)
            self.deps.add(("form", "", "", form[0], form[1]))
        elif tag == "script":
            src = attrs.get("src", "")
            if src:
                self.js_sources.add(normalize_url(src, self.base_url))
        elif tag in {"iframe", "frame"}:
            self.add_link(attrs.get("src", ""))

        if tag in DEP_TAGS or lower_attrs.get("contenteditable") in {"", "true"}:
            form_method, form_action = self.form_stack[-1] if self.form_stack else ("", "")
            action = normalize_url(attrs.get("formaction", ""), self.base_url) or form_action
            method = lower_attrs.get("formmethod", "") or form_method
            self.deps.add(
                (
                    tag,
                    lower_attrs.get("type", ""),
                    lower_attrs.get("name", ""),
                    method,
                    action,
                )
            )

    def handle_endtag(self, tag):
        if tag.lower() == "form" and self.form_stack:
            self.form_stack.pop()

    def add_link(self, value):
        url = normalize_url(value, self.base_url)
        if url:
            self.links.add(url)


class PhpUnserializer:
    def __init__(self, data):
        self.data = data
        self.index = 0

    def parse(self):
        return self.parse_value()

    def parse_value(self):
        kind = chr(self.data[self.index])
        self.index += 2
        if kind == "N":
            self.index -= 1
            self.expect(b"N;")
            return None
        if kind == "i":
            return self.parse_int()
        if kind == "d":
            return self.parse_float()
        if kind == "b":
            return bool(self.parse_int())
        if kind == "s":
            return self.parse_string()
        if kind == "a":
            return self.parse_array()
        raise ValueError(f"unsupported PHP serialize token {kind!r} at {self.index}")

    def parse_int(self):
        end = self.data.index(b";", self.index)
        value = int(self.data[self.index:end])
        self.index = end + 1
        return value

    def parse_float(self):
        end = self.data.index(b";", self.index)
        value = float(self.data[self.index:end])
        self.index = end + 1
        return value

    def parse_string(self):
        colon = self.data.index(b":", self.index)
        length = int(self.data[self.index:colon])
        self.index = colon + 2
        raw = self.data[self.index:self.index + length]
        self.index += length + 2
        return raw.decode("utf-8", errors="replace")

    def parse_array(self):
        colon = self.data.index(b":", self.index)
        count = int(self.data[self.index:colon])
        self.index = colon + 2
        result = {}
        for _ in range(count):
            key = self.parse_value()
            result[key] = self.parse_value()
        self.expect(b"}")
        return result

    def expect(self, token):
        if self.data[self.index:self.index + len(token)] != token:
            raise ValueError(f"expected {token!r} at {self.index}")
        self.index += len(token)


def parse_duration_seconds(value):
    if not value:
        return ""
    total = 0
    units = {
        "hour": 3600,
        "hours": 3600,
        "minute": 60,
        "minutes": 60,
        "second": 1,
        "seconds": 1,
    }
    for amount, unit in re.findall(r"(\d+)\s+([A-Za-z]+)", value):
        total += int(amount) * units.get(unit.lower(), 0)
    return total


def parse_size_kb(value):
    if not value:
        return ""
    match = re.match(r"\s*([0-9.]+)\s*([kmgt]?b)\s*$", value, re.I)
    if not match:
        return ""
    amount = float(match.group(1))
    unit = match.group(2).lower()
    factor = {"b": 1 / 1024, "kb": 1, "mb": 1024, "gb": 1024 * 1024, "tb": 1024 * 1024 * 1024}
    return round(amount * factor[unit], 3)


def normalize_url(value, base_url=""):
    if not value:
        return ""
    value = value.strip()
    if value.startswith(("javascript:", "mailto:", "tel:", "#")):
        return ""
    url = urljoin(base_url, value)
    parsed = urlparse(url)
    if not parsed.scheme and not parsed.netloc and not parsed.path:
        return ""
    parsed = parsed._replace(fragment="")
    return urlunparse(parsed)


def pct(numerator, denominator):
    if not denominator:
        return ""
    return round(numerator * 100.0 / denominator, 2)


def crawl_dirs(root):
    return sorted(path.parent for path in root.rglob("result.json"))


def path_parts(crawl_dir):
    parts = crawl_dir.parts
    for index, part in enumerate(parts):
        if part in RUN_LABELS and index >= 2:
            return parts[index - 2], parts[index - 1], part
    try:
        idx = parts.index("method-full")
        return parts[idx + 1], parts[idx + 2], parts[idx + 3]
    except (ValueError, IndexError):
        return "", "", crawl_dir.parent.name


def run_root(crawl_dir):
    # .../<run>/web/crawl0 -> .../<run>
    return crawl_dir.parent.parent


def parse_dom_features(crawl_dir):
    result = json.loads((crawl_dir / "result.json").read_text())
    states = result.get("states", {})
    dom_dir = crawl_dir / "doms"
    deps_by_state = {}
    deps = set()
    links = set()
    js_sources = set()

    if dom_dir.exists():
        for dom_file in sorted(dom_dir.glob("*.html")):
            state = states.get(dom_file.stem, {})
            parser = PageParser(state.get("url", ""))
            parser.feed(dom_file.read_text(errors="ignore"))
            deps_by_state[dom_file.stem] = len(parser.deps)
            deps.update(parser.deps)
            links.update(parser.links)
            js_sources.update(parser.js_sources)

    for state in states.values():
        links.add(normalize_url(state.get("url", "")))

    for edge in result.get("edges", []):
        edge_id = edge.get("id", "")
        if edge_id.startswith("href "):
            links.add(normalize_url(edge_id[5:]))

    return deps_by_state, deps, links, js_sources


def parse_resources(crawl_dir):
    resources = set()
    js_sources = set()
    resources_file = crawl_dir / "mhtml/resources.txt"
    if resources_file.exists():
        for line in resources_file.read_text(errors="ignore").splitlines():
            if not line.strip():
                continue
            url = line.rsplit(" ", 1)[0]
            normalized = normalize_url(url)
            if not normalized:
                continue
            resources.add(normalized)
            path = urlparse(normalized).path.lower()
            if path.endswith(".js"):
                js_sources.add(normalized)
    return resources, js_sources


def parse_code_coverage(crawl_dir):
    coverage_dir = run_root(crawl_dir) / "coverage"
    covered = set()
    coverable = set()
    files_seen = 0
    parse_errors = 0
    if not coverage_dir.exists():
        return covered, coverable, files_seen, parse_errors

    for coverage_file in sorted(coverage_dir.glob("*.serialized")):
        files_seen += 1
        try:
            data = PhpUnserializer(coverage_file.read_bytes()).parse()
        except Exception:
            parse_errors += 1
            continue
        if not isinstance(data, dict):
            continue
        for filename, lines in data.items():
            if not isinstance(filename, str) or not isinstance(lines, dict):
                continue
            if filename.endswith("/xdebug.php") or filename.endswith("\\xdebug.php"):
                continue
            for line, status in lines.items():
                if not isinstance(line, int) or not isinstance(status, int):
                    continue
                unit = f"{filename}:{line}"
                if status != -2:
                    coverable.add(unit)
                if status > 0:
                    covered.add(unit)
    return covered, coverable, files_seen, parse_errors


def summarize(crawl_dir):
    method, app, run = path_parts(crawl_dir)
    result = json.loads((crawl_dir / "result.json").read_text())
    states = result.get("states", {})
    edges = result.get("edges", [])
    statistics = result.get("statistics", {})
    deps_by_state, deps, links, dom_js_sources = parse_dom_features(crawl_dir)
    resources, resource_js_sources = parse_resources(crawl_dir)
    covered_code, coverable_code, coverage_files, coverage_parse_errors = parse_code_coverage(crawl_dir)

    candidate_elements = sum(len(state.get("candidateElements", [])) for state in states.values())
    failed_events = sum(len(state.get("failedEvents", [])) for state in states.values())
    near_duplicates = sum(1 for state in states.values() if state.get("hasNearDuplicate"))
    states_with_dep = sum(1 for count in deps_by_state.values() if count > 0)

    return {
        "method": method,
        "app": app,
        "run": run,
        "crawl_dir": str(crawl_dir),
        "exit_status": result.get("exitStatus", ""),
        "duration_seconds": parse_duration_seconds(statistics.get("duration", "")),
        "states": len(states),
        "edges": len(edges),
        "crawl_paths": statistics.get("crawlPaths", ""),
        "average_dom_kb": parse_size_kb(statistics.get("averageDomSize", "")),
        "candidate_elements": candidate_elements,
        "candidate_elements_per_state": round(candidate_elements / len(states), 3) if states else "",
        "failed_events": failed_events,
        "near_duplicates": near_duplicates,
        "states_with_dep": states_with_dep,
        "dep_state_coverage_pct": pct(states_with_dep, len(states)),
        "unique_dep": len(deps),
        "unique_dep_per_state": round(len(deps) / len(states), 3) if states else "",
        "unique_links": len(links),
        "unique_resources": len(resources),
        "unique_js_sources": len(dom_js_sources | resource_js_sources),
        "code_coverage_files": coverage_files,
        "code_coverage_parse_errors": coverage_parse_errors,
        "code_covered_lines": len(covered_code),
        "code_coverable_lines": len(coverable_code),
        "code_coverage_pct": pct(len(covered_code), len(coverable_code)),
        "_dep_set": deps,
        "_link_set": links,
        "_js_set": dom_js_sources | resource_js_sources,
        "_code_covered_set": covered_code,
        "_code_coverable_set": coverable_code,
    }


def add_union_coverages(rows):
    universes = {}
    for row in rows:
        universe = universes.setdefault(
            row["app"],
            {"deps": set(), "links": set(), "js": set(), "code": set()},
        )
        universe["deps"].update(row["_dep_set"])
        universe["links"].update(row["_link_set"])
        universe["js"].update(row["_js_set"])
        universe["code"].update(row["_code_coverable_set"])

    for row in rows:
        universe = universes[row["app"]]
        row["total_known_dep"] = len(universe["deps"])
        row["dep_coverage_pct"] = pct(len(row["_dep_set"]), len(universe["deps"]))
        row["total_known_links"] = len(universe["links"])
        row["link_coverage_pct"] = pct(len(row["_link_set"]), len(universe["links"]))
        row["total_known_js_sources"] = len(universe["js"])
        row["js_source_coverage_pct"] = pct(len(row["_js_set"]), len(universe["js"]))
        row["total_known_code_lines"] = len(universe["code"])
        row["code_coverage_union_pct"] = pct(len(row["_code_covered_set"]), len(universe["code"]))
        for key in ["_dep_set", "_link_set", "_js_set", "_code_covered_set", "_code_coverable_set"]:
            del row[key]
    return rows


def add_deltas(rows):
    by_key = {(row["method"], row["app"], row["run"]): row for row in rows}
    numeric_fields = [
        "duration_seconds",
        "states",
        "edges",
        "crawl_paths",
        "average_dom_kb",
        "candidate_elements",
        "failed_events",
        "near_duplicates",
        "states_with_dep",
        "dep_state_coverage_pct",
        "unique_dep",
        "unique_links",
        "unique_resources",
        "unique_js_sources",
        "code_covered_lines",
        "code_coverable_lines",
        "code_coverage_pct",
        "dep_coverage_pct",
        "link_coverage_pct",
        "js_source_coverage_pct",
        "code_coverage_union_pct",
    ]
    for row in rows:
        baseline = by_key.get((row["method"], row["app"], "baseline"))
        for field in numeric_fields:
            delta_field = f"delta_{field}_vs_baseline"
            if row["run"] != "dep" or not baseline:
                row[delta_field] = ""
                continue
            left = row.get(field)
            right = baseline.get(field)
            if left == "" or right == "":
                row[delta_field] = ""
            else:
                row[delta_field] = round(float(left) - float(right), 3)
    return rows


def aggregate_by_method(rows):
    numeric_sum_fields = [
        "duration_seconds",
        "states",
        "edges",
        "crawl_paths",
        "candidate_elements",
        "failed_events",
        "near_duplicates",
        "states_with_dep",
        "unique_dep",
        "unique_links",
        "unique_resources",
        "unique_js_sources",
        "code_covered_lines",
        "code_coverable_lines",
    ]
    numeric_avg_fields = [
        "average_dom_kb",
        "candidate_elements_per_state",
        "dep_state_coverage_pct",
        "unique_dep_per_state",
        "code_coverage_pct",
        "dep_coverage_pct",
        "link_coverage_pct",
        "js_source_coverage_pct",
        "code_coverage_union_pct",
    ]
    grouped = {}
    for row in rows:
        key = (row["method"], row["run"])
        group = grouped.setdefault(
            key,
            {
                "method": row["method"],
                "run": row["run"],
                "apps": set(),
                "complete_runs": 0,
                "max_time_runs": 0,
                "exhausted_runs": 0,
                **{field: 0.0 for field in numeric_sum_fields},
                **{f"avg_{field}": 0.0 for field in numeric_avg_fields},
            },
        )
        group["apps"].add(row["app"])
        group["complete_runs"] += 1
        group["max_time_runs"] += row["exit_status"] == "MAX_TIME"
        group["exhausted_runs"] += row["exit_status"] == "EXHAUSTED"
        for field in numeric_sum_fields:
            if row.get(field) != "":
                group[field] += float(row[field])
        for field in numeric_avg_fields:
            if row.get(field) != "":
                group[f"avg_{field}"] += float(row[field])

    output = []
    for group in grouped.values():
        count = group["complete_runs"] or 1
        group["apps"] = len(group["apps"])
        for field in numeric_sum_fields:
            group[field] = int(group[field]) if group[field].is_integer() else round(group[field], 3)
        for field in numeric_avg_fields:
            group[f"avg_{field}"] = round(group[f"avg_{field}"] / count, 3)
        output.append(group)

    baseline_by_method = {row["method"]: row for row in output if row["run"] == "baseline"}
    delta_fields = numeric_sum_fields + [f"avg_{field}" for field in numeric_avg_fields]
    for row in output:
        baseline = baseline_by_method.get(row["method"])
        for field in delta_fields:
            delta_field = f"delta_{field}_vs_baseline"
            if row["run"] != "dep" or not baseline:
                row[delta_field] = ""
            else:
                row[delta_field] = round(float(row[field]) - float(baseline[field]), 3)
    return sorted(output, key=lambda row: (row["method"], row["run"]))


def main():
    parser = argparse.ArgumentParser(
        description="Build paper-like metrics from Crawljax CrawlOverview outputs."
    )
    parser.add_argument("root", type=Path, help="Directory containing experiment result.json files")
    parser.add_argument("--csv", type=Path, required=True, help="CSV output path")
    parser.add_argument("--aggregate-csv", type=Path, help="Optional method-level aggregate CSV")
    args = parser.parse_args()

    rows = add_deltas(add_union_coverages([summarize(path) for path in crawl_dirs(args.root)]))
    if not rows:
        raise SystemExit(f"no result.json files found under {args.root}")

    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with args.csv.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    if args.aggregate_csv:
        aggregate_rows = aggregate_by_method(rows)
        args.aggregate_csv.parent.mkdir(parents=True, exist_ok=True)
        with args.aggregate_csv.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(aggregate_rows[0].keys()))
            writer.writeheader()
            writer.writerows(aggregate_rows)
    print(json.dumps(rows, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
