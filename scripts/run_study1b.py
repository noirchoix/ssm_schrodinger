from __future__ import annotations

import argparse
import json

from ssm.auto_research.study1b import (
    analyze_online_study,
    qualify_online_benchmark,
    run_online_repeated_arm,
    settings_from_cli,
)


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
        description="SSM Research Study 1B online canonical-context synthesis harness"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    qualify = sub.add_parser("qualify")
    qualify.add_argument("benchmark")
    qualify.add_argument("out")
    qualify.add_argument("--no-quality-gates", action="store_true")
    _add_provider_args(qualify)

    run_arm = sub.add_parser("run-arm")
    run_arm.add_argument("benchmark")
    run_arm.add_argument("out")
    run_arm.add_argument("--qualification", required=True)
    run_arm.add_argument("--arm", default="deepseek_online")
    run_arm.add_argument("--replicates", type=int, default=10)
    run_arm.add_argument("--quality-gates", action="store_true")
    run_arm.add_argument("--delay-seconds", type=float, default=0.0)
    run_arm.add_argument("--no-resume", action="store_true")
    _add_provider_args(run_arm)

    analyze = sub.add_parser("analyze")
    analyze.add_argument("offline")
    analyze.add_argument("online")
    analyze.add_argument("out")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "analyze":
        result = analyze_online_study(args.offline, args.online, args.out)
    else:
        settings = settings_from_cli(
            provider=args.provider,
            model=args.model,
            temperature=args.temperature,
            timeout_seconds=args.timeout_seconds,
            max_retries=args.max_retries,
            max_output_tokens=args.max_output_tokens,
        )
        if args.command == "qualify":
            result = qualify_online_benchmark(
                args.benchmark,
                args.out,
                settings=settings,
                quality_gates=not args.no_quality_gates,
                repair_attempts=args.repair_attempts,
            )
        else:
            result = run_online_repeated_arm(
                args.benchmark,
                args.out,
                settings=settings,
                qualification_path=args.qualification,
                arm=args.arm,
                replicates=args.replicates,
                quality_gates=args.quality_gates,
                repair_attempts=args.repair_attempts,
                delay_seconds=args.delay_seconds,
                resume=not args.no_resume,
            )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
