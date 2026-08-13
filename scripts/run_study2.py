from __future__ import annotations

import argparse
import json

from ssm.auto_research.study1b import settings_from_cli
from ssm.auto_research.study2 import (
    compare_online_mutant_to_noise_floor,
    qualify_deterministic_mutant,
    qualify_online_mutant,
    require_source_provenance,
    run_deterministic_mutant_arm,
    run_online_mutant_arm,
)


def _add_provenance_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--mutant-id", required=True)
    parser.add_argument("--module", action="append", required=True, dest="modules")
    parser.add_argument("--expected-branch")
    parser.add_argument("--expected-commit")
    parser.add_argument("--allow-dirty", action="store_true")


def _add_provider_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--provider", default="deepseek")
    parser.add_argument("--model")
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--timeout-seconds", type=int)
    parser.add_argument("--max-retries", type=int)
    parser.add_argument("--max-output-tokens", type=int)
    parser.add_argument("--repair-attempts", type=int)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="SSM Study 2 provenance-locked source-mutant experiment harness"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    provenance = sub.add_parser("provenance")
    provenance.add_argument("benchmark")
    provenance.add_argument("out")
    _add_provenance_args(provenance)

    qualify = sub.add_parser("qualify")
    qualify.add_argument("benchmark")
    qualify.add_argument("out")
    qualify.add_argument("--baseline", required=True)
    qualify.add_argument("--expected-first-stage", required=True)
    qualify.add_argument("--expected-changed-count", type=int)
    qualify.add_argument("--expected-verdict", default="REGRESSION")
    _add_provenance_args(qualify)

    run_arm = sub.add_parser("run-arm")
    run_arm.add_argument("benchmark")
    run_arm.add_argument("out")
    run_arm.add_argument("--replicates", type=int, default=10)
    _add_provenance_args(run_arm)

    online_qualify = sub.add_parser("online-qualify")
    online_qualify.add_argument("benchmark")
    online_qualify.add_argument("out")
    online_qualify.add_argument("--no-quality-gates", action="store_true")
    _add_provenance_args(online_qualify)
    _add_provider_args(online_qualify)

    online_run = sub.add_parser("online-run")
    online_run.add_argument("benchmark")
    online_run.add_argument("out")
    online_run.add_argument("--qualification", required=True)
    online_run.add_argument("--arm", required=True)
    online_run.add_argument("--replicates", type=int, default=10)
    online_run.add_argument("--quality-gates", action="store_true")
    online_run.add_argument("--delay-seconds", type=float, default=0.0)
    online_run.add_argument("--no-resume", action="store_true")
    _add_provenance_args(online_run)
    _add_provider_args(online_run)

    compare = sub.add_parser("compare-online")
    compare.add_argument("study1b_online")
    compare.add_argument("mutant_online")
    compare.add_argument("out")
    compare.add_argument("--expected-first-stage", required=True)
    compare.add_argument("--expected-affected-case", action="append", default=[])

    return parser


def _settings(args: argparse.Namespace):
    return settings_from_cli(
        provider=args.provider,
        model=args.model,
        temperature=args.temperature,
        timeout_seconds=args.timeout_seconds,
        max_retries=args.max_retries,
        max_output_tokens=args.max_output_tokens,
    )


def _provenance_kwargs(args: argparse.Namespace) -> dict[str, object]:
    return {
        "mutant_id": args.mutant_id,
        "module_names": args.modules,
        "expected_branch": args.expected_branch,
        "expected_commit": args.expected_commit,
        "require_clean": not args.allow_dirty,
    }


def main() -> int:
    args = _parser().parse_args()
    if args.command == "provenance":
        result = require_source_provenance(
            args.benchmark,
            out_path=args.out,
            **_provenance_kwargs(args),
        )
    elif args.command == "qualify":
        result = qualify_deterministic_mutant(
            args.benchmark,
            args.out,
            baseline_dir=args.baseline,
            expected_first_stage=args.expected_first_stage,
            expected_changed_count=args.expected_changed_count,
            expected_verdict=args.expected_verdict,
            **_provenance_kwargs(args),
        )
    elif args.command == "run-arm":
        result = run_deterministic_mutant_arm(
            args.benchmark,
            args.out,
            replicates=args.replicates,
            **_provenance_kwargs(args),
        )
    elif args.command == "online-qualify":
        result = qualify_online_mutant(
            args.benchmark,
            args.out,
            settings=_settings(args),
            quality_gates=not args.no_quality_gates,
            repair_attempts=args.repair_attempts,
            **_provenance_kwargs(args),
        )
    elif args.command == "online-run":
        result = run_online_mutant_arm(
            args.benchmark,
            args.out,
            settings=_settings(args),
            qualification_path=args.qualification,
            arm=args.arm,
            replicates=args.replicates,
            quality_gates=args.quality_gates,
            repair_attempts=args.repair_attempts,
            delay_seconds=args.delay_seconds,
            resume=not args.no_resume,
            **_provenance_kwargs(args),
        )
    else:
        result = compare_online_mutant_to_noise_floor(
            args.study1b_online,
            args.mutant_online,
            args.out,
            expected_first_stage=args.expected_first_stage,
            expected_affected_cases=args.expected_affected_case,
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
