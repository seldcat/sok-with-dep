# DEP comparison experiment

This experiment compares Crawljax state equivalence as used in the original
State of the Krawlers setup with the same run guarded by an additional DEP
signature comparison.

DEP means data entry point: visible forms, inputs, selects, textareas, buttons,
and contenteditable elements. With `--compare-deps`, two states are considered
the same only when the selected state abstraction says they are equal and their
DEP signatures are equal.

The experiment also has a standalone `dep_only` state abstraction. It ignores
DOM, URL, visual, and structural similarity and treats two states as equal when
their DEP signatures are equal. This is intentionally narrow: it is useful as a
negative-control method for checking whether DEP alone loses too much page
context.

## Arachnarium batch

Run the Docker Compose based baseline from the repository root:

```sh
arachnarium batch -w 1 experiments/dep/crawljax_dep_comparison.yml
```

## Kubernetes smoke experiment

The Kubernetes manifest uses the single-container WackoPicko app to keep the
first experiment small. Build images into Minikube, apply the manifest, and copy
the results out of the `dep-results` PVC.

```sh
eval "$(minikube docker-env)"
docker build -t sotk-crawljax-dep:local crawlers/crawljax
docker build -t sotk-wackopicko:local apps/wackopicko/web
kubectl apply -f experiments/dep/k8s/wackopicko-crawljax-dep-comparison.yaml
kubectl -n sotk-dep wait --for=condition=complete job/crawljax-dep-comparison --timeout=20m
```

Summarize two CrawlOverview outputs:

```sh
python3 experiments/dep/scripts/dep_report.py /path/to/baseline /path/to/dep --csv dep-summary.csv
```

## Full-method metrics

The large method run stores one summary CSV per method in:

```text
experiments/dep/results/method-full/
```

To rebuild the paper-like metrics table from saved CrawlOverview `result.json`
files:

```sh
python3 experiments/dep/scripts/paper_metrics_report.py \
  experiments/dep/results/method-full \
  --csv experiments/dep/results/method-full-paper-metrics.csv \
  --aggregate-csv experiments/dep/results/method-full-paper-metrics-by-method.csv
```

The report includes paper-style metrics and DEP-specific metrics:

- `code_coverage_pct`, `code_coverage_union_pct`
- `link_coverage_pct`
- `js_source_coverage_pct`
- `states`, `edges`, `crawl_paths`, `duration_seconds`
- `states_with_dep`, `dep_state_coverage_pct`, `unique_dep`,
  `unique_dep_per_state`, `dep_coverage_pct`

The `*_coverage_pct` metrics use an experiment-local denominator: the union of
all units found for the same app across all methods and variants in the result
directory. This makes the methods comparable within one controlled experiment
even when a separate ground-truth inventory is unavailable.

`dep_state_coverage_pct` answers "what share of visited states contains at least
one DEP?", while `dep_coverage_pct` answers "what share of all DEP signatures
known from this experiment did this run find?"

## Full metrics suite

Use this runner for the high-quality experiment that compares paper methods,
paper methods plus DEP, and `dep_only`:

```sh
python3 experiments/dep/scripts/run_metrics_suite.py \
  --apps addressbook hotcrp joomla owncloud phpbb2 scarf vanilla wackopicko \
  --methods url_full general_paths widgets rted simhash procrawl dep_only \
  --timeout 5 \
  --parallel 2 \
  --job-timeout 30m \
  --output-dir experiments/dep/results/metrics-full
```

For every paper method the suite runs:

- `baseline`: the original method from the paper
- `dep`: the same method with `--compare-deps`

For `dep_only`, the suite runs only `baseline`, because the method itself is
already pure DEP equivalence.

The suite enables resource capture for JS/link metrics and stores Xdebug
coverage artifacts for code coverage. Final CSV files are written next to the
output directory:

```text
experiments/dep/results/metrics-full-paper-metrics.csv
experiments/dep/results/metrics-full-paper-metrics-by-method.csv
```

## DEP-only run

After rebuilding and loading `sotk-crawljax-dep:local`, run the standalone DEP
abstraction like any other method:

```sh
python3 experiments/dep/scripts/run_crawljax_all_k8s.py \
  --apps addressbook hotcrp joomla owncloud phpbb2 scarf vanilla wackopicko \
  --timeout 5 \
  --parallel 2 \
  --job-timeout 30m \
  --algorithm dep_only \
  --navigation bfs \
  --variants baseline \
  --collect-resources \
  --output-dir experiments/dep/results/method-full/dep_only
```

For `dep_only`, use only the `baseline` variant because the base abstraction
already compares only DEP signatures.
