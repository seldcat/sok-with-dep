#!/usr/bin/env python3

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_METHODS = ["url_full", "general_paths", "widgets", "rted", "simhash", "procrawl", "dep_only"]
DEFAULT_APPS = ["addressbook", "hotcrp", "joomla", "owncloud", "phpbb2", "scarf", "vanilla", "wackopicko"]


def run(cmd):
    print("+", " ".join(str(part) for part in cmd), flush=True)
    subprocess.run(cmd, check=True)


def main():
    parser = argparse.ArgumentParser(description="Run the full DEP metrics experiment suite.")
    parser.add_argument("--methods", nargs="+", default=DEFAULT_METHODS)
    parser.add_argument("--apps", nargs="+", default=DEFAULT_APPS)
    parser.add_argument("--timeout", type=int, default=5)
    parser.add_argument("--parallel", type=int, default=2)
    parser.add_argument("--job-timeout", default="30m")
    parser.add_argument("--navigation", default="bfs")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "experiments/dep/results/metrics-full")
    parser.add_argument("--crawler-image", default="sotk-crawljax-dep:local")
    parser.add_argument("--keep-going", action="store_true")
    args = parser.parse_args()

    runner = ROOT / "experiments/dep/scripts/run_crawljax_all_k8s.py"
    report = ROOT / "experiments/dep/scripts/paper_metrics_report.py"
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for method in args.methods:
        variants = ["baseline"] if method == "dep_only" else ["baseline", "dep"]
        cmd = [
            sys.executable,
            str(runner),
            "--apps",
            *args.apps,
            "--timeout",
            str(args.timeout),
            "--parallel",
            str(args.parallel),
            "--job-timeout",
            args.job_timeout,
            "--algorithm",
            method,
            "--navigation",
            args.navigation,
            "--variants",
            *variants,
            "--collect-resources",
            "--crawler-image",
            args.crawler_image,
            "--output-dir",
            str(args.output_dir / method),
        ]
        try:
            run(cmd)
        except subprocess.CalledProcessError:
            if not args.keep_going:
                raise
            print(f"method {method} failed; continuing because --keep-going is set", file=sys.stderr)

    run([
        sys.executable,
        str(report),
        str(args.output_dir),
        "--csv",
        str(args.output_dir.parent / f"{args.output_dir.name}-paper-metrics.csv"),
        "--aggregate-csv",
        str(args.output_dir.parent / f"{args.output_dir.name}-paper-metrics-by-method.csv"),
    ])


if __name__ == "__main__":
    main()
