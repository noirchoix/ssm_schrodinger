from __future__ import annotations

import argparse
import json

from ssm.auto_research.study1 import (
    analyze_study,
    qualify_benchmark,
    run_repeated_arm,
    validate_benchmark,
    write_mutation_arm,
)

_MUTATIONS = [
    "requirements_drop",
    "sml_rule_drop",
    "generated_tree_drop",
    "intended_evolution",
]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SSM Research Study 1 harness")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate")
    validate.add_argument("benchmark")

    qualify = sub.add_parser("qualify")
    qualify.add_argument("benchmark")
    qualify.add_argument("out")

    run_arm = sub.add_parser("run-arm")
    run_arm.add_argument("benchmark")
    run_arm.add_argument("out")
    run_arm.add_argument("--arm", required=True)
    run_arm.add_argument("--replicates", type=int, default=10)

    mutate = sub.add_parser("mutate")
    mutate.add_argument("baseline")
    mutate.add_argument("out")
    mutate.add_argument("--mutation", required=True, choices=_MUTATIONS)

    analyze = sub.add_parser("analyze")
    analyze.add_argument("baseline")
    analyze.add_argument("control")
    analyze.add_argument("perturbations")
    analyze.add_argument("out")

    return parser


def main() -> int:
    args = _parser().parse_args()

    if args.command == "validate":
        result = validate_benchmark(args.benchmark)
    elif args.command == "qualify":
        result = qualify_benchmark(args.benchmark, args.out)
    elif args.command == "run-arm":
        result = run_repeated_arm(
            args.benchmark,
            args.out,
            arm=args.arm,
            replicates=args.replicates,
        )
    elif args.command == "mutate":
        result = write_mutation_arm(args.baseline, args.out, args.mutation)
    else:
        result = analyze_study(
            args.baseline,
            args.control,
            args.perturbations,
            args.out,
        )

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
