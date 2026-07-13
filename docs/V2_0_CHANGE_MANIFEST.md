# V2.0.0-dev Changed-File Manifest

Compared with the uploaded baseline repository: `ssm_schrodinger-main`.

- Added files: 8 (including this manifest)
- Modified files: 19
- Deleted files: 0

## Added files

| File | Purpose | SHA-256 |
|---|---|---|
| `docs/RELEASE_CHECKLIST_V2_0_DEV.md` | Adds the V2 release checklist. | `5f91052789635ee16a41e520274f1dda0e45197dff30eab1c8e252ccda2d213c` |
| `docs/V2_0_ACCEPTANCE_MATRIX.md` | Maps every user-defined Phase A–E criterion to implementation and evidence. | `70cd535f958b471d8d58dd414913e08a74027470dda4a6282d2642faec58247d` |
| `docs/V2_0_LOCAL_VALIDATION.md` | Records the successful local release-gate results and unexecuted external gates. | `8f812f53dc2118ff2a98a6af3a199f049f2c2ce28b4aaa41433035ef9685bf2c` |
| `docs/V2_0_CHANGE_MANIFEST.md` | Records the exact baseline-to-V2 file delta. | Self-referential manifest; verify through the release ZIP checksum. |
| `docs/V2_0_PLATFORM.md` | Documents the V2 product-platform architecture and runtime contracts. | `ef6b1f1495bd4480cdd805aaba662dccf13cb22b6a4c73030a5cdef5e4f34ac4` |
| `scripts/test_v20_e2e.sh` | Adds the dedicated V2 deterministic, SaaS, workflow, UI, repair, evidence, and optional live-provider release gate. | `deb95019d0a797b02c0e771637e82f4f089de90a6b07970e714d604024286271` |
| `tests/test_evidence_validation.py` | Tests valid evidence and tamper rejection. | `28f43c5ba0dd54156c379a60b64be9a0e556f690e0e1fb16b5f4a9b7b53bce52` |
| `tests/test_online_repair_seed.py` | Tests rejected first attempt and accepted bounded repair. | `e74909dff57d52bb19a92332bf26569bfa893a2775fcabb794b8233b95465fb2` |

## Modified files

| File | Purpose | SHA-256 |
|---|---|---|
| `.github/workflows/ci.yml` | Adds the V2 product-platform CI job with Python and Node release gates. | `e12e06629357229dd642766270d2d369449095cd3de72837e9f201253cb64916` |
| `BUILD_REPORT.md` | Adds the cumulative V2 product-platform build status while retaining historical reports. | `c1c1441c305923fda3bce6789f22739dc573351b5b29737fc5f6b69b7f97f57d` |
| `CHANGELOG.md` | Documents V2 evidence, SaaS, workflow, repair, and admin-client capabilities. | `13a52ac882addd59609febfbacc15993e0a2f33ec96b6de9bef4be6c28693bdf` |
| `Makefile` | Adds V2 E2E and frontend build targets. | `35a62ca47f69bc30a2a31b44298d2a9dff74f902ccbeb6be8c53b0909540affa` |
| `PATCH_APPLY_NOTES.md` | Reframes the repository as a cumulative V2 candidate rather than a one-file patch. | `1be81d8c5865d51787eaa56ed0dfe7372593e4afa6ae9860c1f32074b681d792` |
| `PHASE_STATUS.md` | Adds current Phase A–E completion status and final live-gate condition. | `d0c1179825a530c0da7e67a73639e341f1711a999bb7b66e1cc95dd4ac1607c1` |
| `README.md` | Makes V2.0.0-dev the current product-platform entry point and links acceptance evidence. | `5a7f590302847d18df2285dc1e04e39aa1d16aa65d9b8d0bb22292bbc6816c5f` |
| `RELEASE_NOTES.md` | Adds V2 product-platform release notes and promotion conditions. | `9b7f28aba6e03a2fae46cb850b51d2d137e3dbeb4a75a28b5c6c10eeeae6eca5` |
| `VERSION_LOCK_REPORT.md` | Records the 2.0.0.dev0 version state and pending final certification. | `108028ab5cd93f288f9f792070f32b34aace122bed54640328a4eb7d3a8338f9` |
| `docs/CAPABILITY_MATRIX.md` | Replaces the historical V1.3 scope matrix with the current V2 capability boundary. | `f493633884fea42c74ab96efccc58c9e3b273ba6753fbe0316f01a1f88e443b7` |
| `docs/V1_5_PLATFORM_LAYER.md` | Marks V1.5 limitations as historical and superseded by V2. | `4a25aa9daeb568bb5b89769e36fbe1381a57fedad7343f4d488fb6359cea9ad5` |
| `pyproject.toml` | Bumps package metadata to 2.0.0.dev0. | `24fa5c19122117cc122e1825c48737aa563bdd964745dc66e12942068f7ff76e` |
| `scripts/test_v15_e2e.sh` | Keeps the V1.5 suite runnable as a compatibility gate under the V2 runtime. | `8956b05b481aea4df6af9b16114116efe02d6f8f0144e9a146d018442abf625f` |
| `src/ssm/__init__.py` | Bumps runtime metadata to 2.0.0.dev0. | `c165378ae2f06af17c5e4134fce15afa890c9379ddb64d9fc0bd1c5551f3cf5d` |
| `src/ssm/backends/python_fastapi/platform.py` | Generates schema-2.0 evidence, tenant/RBAC/audit/workflow runtimes, platform migrations, tests, and production React/Vite admin artifacts. | `523dd18770d238a22bd963aa4e2d2aa0326ba2302f74b57f041831aa10b261ba` |
| `src/ssm/backends/python_fastapi/target.py` | Integrates V2 platform generation while preserving R12–R20 fixes; enforces tenant-scoped CRUD/RBAC/audit/readiness/admin build contracts. | `ae9290a654e52296c375ea6ea24cc8002b35eb3816b45f48a154cc8ae6ed216c` |
| `src/ssm/cli/main.py` | Adds initial-draft support for forced online-build repair validation. | `7cef5324029d5ff16e2dda8d0f87f04c928edb2a5f97ad91218c2759681d65c0` |
| `src/ssm/evidence/schemas.py` | Validates evidence schema 2.0, generated-file hashes, paths, and bundle references. | `1daa7599b6d4c027ed0a481e7dbac59f77c4738f30841416860242d54204b26f` |
| `src/ssm/foundation/builder.py` | Adds seeded bounded repair, exact diagnostic feedback, and repair trace schema 2.0. | `d84f007ad2a804566103ae5e8d13f6c45961f9a26e71027791b837312456954f` |

## Deleted files

None.

## Regression boundary

The cumulative `target.py` fixes from the validated V1.5 line remain present. The V2 gate additionally exercises schema-2.0 evidence, tenant enforcement for SQLAlchemy and in-memory repositories, RBAC, persistent audit, persistent workflow/business-rule execution, frontend typecheck/build, and bounded repair.
