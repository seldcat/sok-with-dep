#!/usr/bin/env python3

import argparse
import csv
import json
from html.parser import HTMLParser
from pathlib import Path


DEP_TAGS = {"form", "input", "textarea", "select", "button"}


class DepParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.entries = set()
        self.form_stack = []

    def handle_starttag(self, tag, attrs):
        attrs = {name.lower(): (value or "").strip().lower() for name, value in attrs}
        tag = tag.lower()
        if tag == "form":
            form = (attrs.get("method", ""), attrs.get("action", ""))
            self.form_stack.append(form)
            self.entries.add(("form", "", "", form[0], form[1]))
        if tag in DEP_TAGS or attrs.get("contenteditable") in {"", "true"}:
            form_method, form_action = self.form_stack[-1] if self.form_stack else ("", "")
            self.entries.add(
                (
                    tag,
                    attrs.get("type", ""),
                    attrs.get("name", ""),
                    attrs.get("formmethod", form_method),
                    attrs.get("formaction", form_action),
                )
            )

    def handle_endtag(self, tag):
        if tag.lower() == "form" and self.form_stack:
            self.form_stack.pop()


def count_deps(dom_file):
    parser = DepParser()
    parser.feed(dom_file.read_text(errors="ignore"))
    return parser.entries


def find_crawl_dirs(run_dir):
    if (run_dir / "result.json").exists():
        return [run_dir]
    return sorted(path.parent for path in run_dir.rglob("result.json"))


def summarize_crawl(crawl_dir, label):
    result_path = crawl_dir / "result.json"
    result = json.loads(result_path.read_text()) if result_path.exists() else {}
    dom_dir = crawl_dir / "doms"
    deps_by_state = {}
    all_deps = set()
    if dom_dir.exists():
        for dom_file in sorted(dom_dir.glob("*.html")):
            deps = count_deps(dom_file)
            deps_by_state[dom_file.stem] = len(deps)
            all_deps.update(deps)
    states = result.get("states", {})
    edges = result.get("edges", [])
    return {
        "run": label,
        "crawl_dir": str(crawl_dir),
        "states": len(states),
        "edges": len(edges),
        "states_with_dep": sum(1 for count in deps_by_state.values() if count > 0),
        "unique_dep": len(all_deps),
        "exit_status": result.get("exitStatus", ""),
    }


def summarize_run(run_dir):
    crawl_dirs = find_crawl_dirs(run_dir)
    if not crawl_dirs:
        return [summarize_crawl(run_dir, run_dir.name)]
    if len(crawl_dirs) == 1:
        return [summarize_crawl(crawl_dirs[0], run_dir.name)]
    return [
        summarize_crawl(crawl_dir, f"{run_dir.name}/{crawl_dir.relative_to(run_dir)}")
        for crawl_dir in crawl_dirs
    ]


def main():
    parser = argparse.ArgumentParser(description="Summarize DEP coverage in Crawljax CrawlOverview outputs.")
    parser.add_argument("runs", nargs="+", type=Path, help="CrawlOverview output directories")
    parser.add_argument("--csv", type=Path, help="Optional CSV output path")
    args = parser.parse_args()

    rows = [row for path in args.runs for row in summarize_run(path)]
    if args.csv:
        with args.csv.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
    print(json.dumps(rows, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
