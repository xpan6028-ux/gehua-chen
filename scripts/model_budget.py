"""Count the model workload implied by the inspected OneClick 6.0 source; no Stata execution."""
import argparse
import json
import math
import sys


def budget(k, threshold=None):
    if k < 2:
        raise ValueError("OneClick 6.0 requires y plus at least two candidate controls")
    if k > 1000:
        raise ValueError("Candidate count exceeds this calculator's supported range (1000)")
    if threshold is not None and threshold < 1:
        raise ValueError("threshold must be a positive integer")
    slots = 2 ** k
    calls = slots if threshold is None else sum(math.comb(k, j) for j in range(threshold, k + 1))
    return {
        "candidate_controls": k,
        "threshold": threshold,
        "combination_slots_and_minimum_working_rows": slots,
        "estimated_regression_calls_from_source": calls,
        "screen_displayed_count_from_source": slots - 1 if threshold is None else calls,
        "maximum_nonempty_candidate_subsets_before_screening": slots - 1 if threshold is None else calls,
        "includes_fixed_only_empty_subset_call": threshold is None,
        "executed_stata": False,
        "note": "Static source-based count, not a runtime or memory benchmark; threshold does not remove exponential combination generation.",
    }


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("k", type=int)
    ap.add_argument("--threshold", type=int)
    args = ap.parse_args()
    try:
        result = budget(args.k, args.threshold)
    except ValueError as exc:
        ap.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
