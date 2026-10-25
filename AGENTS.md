# MORI repository rules

- The repository has two independently versioned projects: `robot/` is the formal STM32 product; `test_rig/` is the Raspberry Pi feasibility rig. Read `projects.json`, each project's version manifest and status before work. Never transfer qualification or component adoption between them.
- For formal robot work read `robot/AGENTS.md`, `robot/docs/REQUIREMENTS.md` and `robot/config/project_baseline.json`. Paths in the chronological robot decisions are relative to `robot/` unless explicitly marked as historical source paths.
- Current project paths and commands are documented in the root README, VERSIONING.md and HANDOFF.md. Current files use stable names; source revision numbers belong in manifests. Do not relabel software or models as upgraded merely because the documentation version changes.
- Preserve original vendor files, manufacturing sources, measurements and frozen evidence. Move them with byte preservation; document any path-only metadata changes. CAD and offline checks are not physical qualification.
- Do not change electrical design, mechanical geometry or control behavior during repository organization. Structural uncertainty requires user confirmation. Only send instructions to the hardware conversation when an actual hardware design change is needed.
- Keep local, ignored experiment folders and other active worktrees intact. `hardware/bringup`, `hardware/test_rig` and `mechanical/test_rig` in older workspaces are local source locations, not additional published projects. Never delete them just because their tracked counterparts moved.
- Never run motors, flash firmware, SSH/deploy to the rig, or resume a paused physical experiment as part of publication or offline validation.
- Use PRs for publication. This organization task authorizes creating a PR, not merging it or changing another conversation's branch.
