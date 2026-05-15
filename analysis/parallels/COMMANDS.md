# Parallel-passage CLI — quick reference

## Build

```bash
# Build (or rebuild) data/parallels.sqlite from data/dumps/*.json
python3 -m analysis.parallels build

# Custom paths
python3 -m analysis.parallels build --dumps data/dumps --db data/parallels.sqlite
```

## Explore spans

```bash
# Top formulas by occurrence count (default)
python3 -m analysis.parallels top-formulas

# Top formulas by token length
python3 -m analysis.parallels top-formulas --by tokens --limit 20

# List spans (min 5 occurrences, min 10 tokens)
python3 -m analysis.parallels list-spans --min-occurrences 5 --min-tokens 10 --limit 100

# All spans in a sutta
python3 -m analysis.parallels spans-in-sutta MN36
python3 -m analysis.parallels spans-in-sutta DN2 --min-tokens 10

# Inspect one span (get span_id from any listing command)
python3 -m analysis.parallels show-span 8b5e7ab11450
```

## Stats

```bash
python3 -m analysis.parallels stats
```

## JSON output

Every command accepts `--json` for scripting:

```bash
python3 -m analysis.parallels top-formulas --json
python3 -m analysis.parallels spans-in-sutta MN36 --json
python3 -m analysis.parallels show-span 8b5e7ab11450 --json
python3 -m analysis.parallels stats --json
```

## Help

```bash
python3 -m analysis.parallels --help
python3 -m analysis.parallels build --help
python3 -m analysis.parallels list-spans --help
```
