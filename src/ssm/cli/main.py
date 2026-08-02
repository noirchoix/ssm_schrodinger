from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ssm.agents.embeddings import embedding_response_to_json, make_embedding_provider
from ssm.agents.intent_agent import IntentAgent
from ssm.agents.online import OnlineDraftService
from ssm.agents.repair_agent import RepairAgent
from ssm.agents.settings import OnlineAgentSettings
from ssm.agents.sml_agent import SMLGeneratorAgent
from ssm.errors import SSMError
from ssm.evidence import validate_evidence_directory
from ssm.foundation.builder import OnlineBuildService
from ssm.foundation.negotiator import CapabilityNegotiator
from ssm.foundation.planner import AppFoundationPlanner
from ssm.foundation.renderer import FoundationSMLRenderer
from ssm.pipeline import SSMCompiler
from ssm.product.compiler import SchrodingerProductCompiler
from ssm.requirements.extractor import IntentRequirementsCompiler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="smlc", description="Semantic Software Markup Compiler")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="Parse, analyze, and run logic validation.")
    validate.add_argument("file")

    inspect = sub.add_parser("inspect", help="Inspect compiler intermediate representations.")
    inspect.add_argument("file")
    inspect.add_argument("--stage", choices=["ast", "sir", "facts", "resolution"], default="sir")

    compile_cmd = sub.add_parser("compile", help="Compile SML into a target source tree.")
    compile_cmd.add_argument("file")
    compile_cmd.add_argument("--out", required=True)

    draft_cmd = sub.add_parser(
        "draft",
        help="Draft SML from a natural-language prompt. Offline by default; online is explicit and gated.",
    )
    draft_cmd.add_argument("--prompt", required=True)
    draft_cmd.add_argument("--out")
    draft_cmd.add_argument("--agent-mode", choices=["offline", "online"])
    draft_cmd.add_argument("--provider", choices=["openai", "deepseek", "gemini", "mock"])
    draft_cmd.add_argument("--model")
    draft_cmd.add_argument("--temperature", type=float)
    draft_cmd.add_argument("--timeout-seconds", type=int)
    draft_cmd.add_argument("--max-retries", type=int)
    draft_cmd.add_argument("--max-output-tokens", type=int)

    embed_cmd = sub.add_parser(
        "embed-text",
        help="Create embeddings through the configured embedding provider. Explicit online utility.",
    )
    embed_cmd.add_argument("--text", action="append", required=True)
    embed_cmd.add_argument("--provider", choices=["gemini", "voyageai", "mock"])
    embed_cmd.add_argument("--model")
    embed_cmd.add_argument("--out")

    plan_cmd = sub.add_parser(
        "plan",
        help="Create a deterministic AppFoundationPlan from a natural-language app idea.",
    )
    plan_cmd.add_argument("--prompt", required=True)
    plan_cmd.add_argument("--out")
    plan_cmd.add_argument("--emit-sml", action="store_true")

    negotiate_cmd = sub.add_parser(
        "negotiate",
        help="Negotiate an SML document or prompt against domain-pack/compiler capabilities.",
    )
    negotiate_source = negotiate_cmd.add_mutually_exclusive_group(required=True)
    negotiate_source.add_argument("--file")
    negotiate_source.add_argument("--prompt")

    online_build_cmd = sub.add_parser(
        "online-build",
        help="Run online draft -> capability negotiation -> deterministic compile -> optional gates.",
    )
    online_build_cmd.add_argument("--prompt", required=True)
    online_build_cmd.add_argument("--out", required=True)
    online_build_cmd.add_argument("--agent-mode", choices=["offline", "online"])
    online_build_cmd.add_argument("--provider", choices=["openai", "deepseek", "gemini", "mock"])
    online_build_cmd.add_argument("--model")
    online_build_cmd.add_argument("--temperature", type=float)
    online_build_cmd.add_argument("--timeout-seconds", type=int)
    online_build_cmd.add_argument("--max-retries", type=int)
    online_build_cmd.add_argument("--max-output-tokens", type=int)
    online_build_cmd.add_argument("--quality-gates", action="store_true")
    online_build_cmd.add_argument("--repair-attempts", type=int)
    online_build_cmd.add_argument(
        "--initial-draft",
        help="Seed attempt one from an SML file, then use the provider for bounded repair.",
    )

    evidence_cmd = sub.add_parser(
        "evidence-check",
        help="Validate generated app evidence records and app contract files.",
    )
    evidence_cmd.add_argument("app_dir")

    repair_cmd = sub.add_parser(
        "repair-missing-schema",
        help="Emit an SML semantic patch for a missing schema diagnostic.",
    )
    repair_cmd.add_argument("schema")

    requirements_cmd = sub.add_parser(
        "requirements",
        help="Normalize a README or prompt into a typed RequirementsIR with ambiguities and contradictions.",
    )
    requirements_source = requirements_cmd.add_mutually_exclusive_group(required=True)
    requirements_source.add_argument("--file")
    requirements_source.add_argument("--prompt")
    requirements_cmd.add_argument("--out")

    collapse_cmd = sub.add_parser(
        "collapse-plan",
        help="Resolve intent through RequirementsIR, FoundationPlan, ArchitectureIR, capabilities, and SML.",
    )
    collapse_source = collapse_cmd.add_mutually_exclusive_group(required=True)
    collapse_source.add_argument("--file")
    collapse_source.add_argument("--prompt")
    collapse_cmd.add_argument("--out")

    compile_intent_cmd = sub.add_parser(
        "compile-intent",
        help="Compile README/product intent through the full Schrödinger collapse pipeline.",
    )
    compile_intent_source = compile_intent_cmd.add_mutually_exclusive_group(required=True)
    compile_intent_source.add_argument("--file")
    compile_intent_source.add_argument("--prompt")
    compile_intent_cmd.add_argument("--out", required=True)
    compile_intent_cmd.add_argument("--allow-partial", action="store_true")
    compile_intent_cmd.add_argument("--certification-runs", type=int, default=3)

    certify_cmd = sub.add_parser(
        "certify-intent",
        help="Compile and emit the V2.5 variability/senior-grade certification report.",
    )
    certify_source = certify_cmd.add_mutually_exclusive_group(required=True)
    certify_source.add_argument("--file")
    certify_source.add_argument("--prompt")
    certify_cmd.add_argument("--out")
    certify_cmd.add_argument("--allow-partial", action="store_true")
    certify_cmd.add_argument("--certification-runs", type=int, default=3)

    args = parser.parse_args(argv)
    compiler = SSMCompiler()
    try:
        if args.command == "validate":
            result = compiler.compile_file(args.file)
            print(
                json.dumps(
                    {
                        "success": True,
                        "files": len(result.files),
                        "proofs": len(result.proof_trace),
                    },
                    indent=2,
                )
            )
            return 0
        if args.command == "inspect":
            if args.stage == "ast":
                doc = compiler.parse_file(args.file)
                print(doc.model_dump_json(indent=2))
                return 0
            result = compiler.compile_file(args.file)
            if result.sir is None or result.resolution is None:
                raise RuntimeError("Compilation result is missing inspection data.")
            if args.stage == "sir":
                print(result.sir.model_dump_json(indent=2))
            elif args.stage == "facts":
                print("\n".join(str(f) for f in result.resolution.facts))
            elif args.stage == "resolution":
                print(result.resolution.model_dump_json(indent=2))
            return 0
        if args.command == "compile":
            result = compiler.compile_file(args.file)
            compiler.write_result(result, args.out)
            print(
                json.dumps(
                    {"success": True, "out": str(Path(args.out)), "files": len(result.files)},
                    indent=2,
                )
            )
            return 0
        if args.command == "draft":
            # Keep `draft` offline by default even when the shell still contains
            # online-build environment variables from a live E2E run.
            effective_agent_mode = args.agent_mode or "offline"
            settings = OnlineAgentSettings.from_env().with_overrides(
                agent_mode=effective_agent_mode,
                provider=args.provider,
                model=args.model,
                temperature=args.temperature,
                timeout_seconds=args.timeout_seconds,
                max_retries=args.max_retries,
                max_output_tokens=args.max_output_tokens,
            )
            if settings.agent_mode == "online":
                draft = OnlineDraftService(settings).draft(args.prompt)
            else:
                requirements = IntentAgent().extract(args.prompt)
                draft = SMLGeneratorAgent().draft(requirements)
            if args.out:
                out = Path(args.out)
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(draft.text, encoding="utf-8")
                print(
                    json.dumps(
                        {
                            "success": True,
                            "out": str(out),
                            "assumptions": draft.assumptions,
                            "unresolved_questions": draft.unresolved_questions,
                            "provenance": draft.provenance,
                        },
                        indent=2,
                    )
                )
            else:
                print(draft.text)
            return 0
        if args.command == "embed-text":
            settings = OnlineAgentSettings.from_env()
            values = settings.model_dump()
            if args.provider:
                values["embed_provider"] = args.provider
            if args.model:
                values["embed_model"] = args.model
            settings = OnlineAgentSettings.model_validate(values)
            provider = make_embedding_provider(settings)
            response = provider.embed_texts(args.text)
            output = embedding_response_to_json(response)
            if args.out:
                out = Path(args.out)
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(output, encoding="utf-8")
                print(json.dumps({"success": True, "out": str(out)}, indent=2))
            else:
                print(output)
            return 0
        if args.command == "plan":
            plan = AppFoundationPlanner().plan(args.prompt)
            output = (
                FoundationSMLRenderer().render(plan)
                if args.emit_sml
                else plan.model_dump_json(indent=2)
            )
            if args.out:
                out = Path(args.out)
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(output, encoding="utf-8")
                print(json.dumps({"success": True, "out": str(out)}, indent=2))
            else:
                print(output)
            return 0
        if args.command == "negotiate":
            negotiator = CapabilityNegotiator()
            if args.file:
                payload = negotiator.negotiate_sml_text(
                    Path(args.file).read_text(encoding="utf-8"),
                    source_file=args.file,
                )
            else:
                plan = AppFoundationPlanner().plan(args.prompt)
                payload = negotiator.negotiate_plan(plan)
            print(payload.model_dump_json(indent=2))
            return 0
        if args.command == "online-build":
            settings = OnlineAgentSettings.from_env().with_overrides(
                agent_mode=args.agent_mode,
                provider=args.provider,
                model=args.model,
                temperature=args.temperature,
                timeout_seconds=args.timeout_seconds,
                max_retries=args.max_retries,
                max_output_tokens=args.max_output_tokens,
            )
            build_result = OnlineBuildService(settings).build(
                prompt=args.prompt,
                out_dir=args.out,
                quality_gates=args.quality_gates,
                repair_attempts=args.repair_attempts,
                initial_draft_text=(
                    Path(args.initial_draft).read_text(encoding="utf-8")
                    if args.initial_draft
                    else None
                ),
            )
            print(OnlineBuildService.to_json(build_result))
            return 0
        if args.command == "evidence-check":
            evidence_result = validate_evidence_directory(args.app_dir)
            print(evidence_result.model_dump_json(indent=2))
            return 0 if evidence_result.ok else 2
        if args.command == "repair-missing-schema":
            patch = RepairAgent().patch_missing_schema(args.schema)
            print(patch.model_dump_json(indent=2))
            return 0
        if args.command == "requirements":
            if args.file:
                requirements_ir = IntentRequirementsCompiler().compile_file(args.file)
            else:
                requirements_ir = IntentRequirementsCompiler().compile_text(
                    args.prompt, source_name="<prompt>"
                )
            output = requirements_ir.model_dump_json(indent=2)
            if args.out:
                out = Path(args.out)
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(output + "\n", encoding="utf-8")
                print(json.dumps({"success": True, "out": str(out)}, indent=2))
            else:
                print(output)
            return 0
        if args.command == "collapse-plan":
            product = SchrodingerProductCompiler()
            collapse_plan = (
                product.collapse_file(args.file)
                if args.file
                else product.collapse_text(args.prompt, source_name="<prompt>")
            )
            output = collapse_plan.model_dump_json(indent=2)
            if args.out:
                out = Path(args.out)
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(output + "\n", encoding="utf-8")
                print(json.dumps({"success": True, "out": str(out)}, indent=2))
            else:
                print(output)
            return 0
        if args.command in {"compile-intent", "certify-intent"}:
            product = SchrodingerProductCompiler()
            source_text = Path(args.file).read_text(encoding="utf-8") if args.file else args.prompt
            source_name = args.file or "<prompt>"
            build_out = (
                Path(args.out)
                if args.command == "compile-intent"
                else Path(args.out)
                if args.out
                else None
            )
            product_result = product.build_text(
                source_text,
                source_name=source_name,
                out_dir=build_out,
                allow_partial=args.allow_partial,
                certification_repetitions=args.certification_runs,
            )
            if args.command == "certify-intent":
                if product_result.certification is None:
                    raise RuntimeError("Certification report was not produced.")
                output = product_result.certification.model_dump_json(indent=2)
                if args.out:
                    out = Path(args.out)
                    out.mkdir(parents=True, exist_ok=True)
                    report_path = out / "certification_report.json"
                    report_path.write_text(output + "\n", encoding="utf-8")
                    print(json.dumps({"success": True, "out": str(report_path)}, indent=2))
                else:
                    print(output)
            else:
                print(
                    json.dumps(
                        {
                            "success": product_result.status != "REJECTED",
                            "status": product_result.status,
                            "out": product_result.out_dir,
                            "generated_app": product_result.generated_app_dir,
                            "generated_files": product_result.generated_file_count,
                            "selected_architecture": product_result.selected_architecture,
                            "negotiation_status": product_result.negotiation_status,
                            "capability_status": product_result.capability_status,
                            "certification_status": (
                                product_result.certification.status
                                if product_result.certification is not None
                                else None
                            ),
                            "semantic_variance_score": (
                                product_result.certification.variability.semantic_variance_score
                                if product_result.certification is not None
                                else None
                            ),
                            "artifact_diff": (
                                {
                                    "added": product_result.artifact_diff.added,
                                    "modified": product_result.artifact_diff.modified,
                                    "removed": product_result.artifact_diff.removed,
                                    "unchanged": product_result.artifact_diff.unchanged,
                                }
                                if product_result.artifact_diff is not None
                                else None
                            ),
                            "warnings": product_result.warnings,
                            "blocking_reasons": product_result.blocking_reasons,
                        },
                        indent=2,
                    )
                )
            return 0 if product_result.status != "REJECTED" else 2
    except SSMError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"UNEXPECTED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
