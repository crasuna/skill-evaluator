---
name: skill-evaluator
description: Evaluate Codex skill folders and produce Chinese reports for structure, trigger quality, workflow clarity, progressive disclosure, bundled resource design, validation coverage, and safe scope. Use when Codex is asked to review, score, QA, audit, improve, or compare a Codex skill, especially a folder containing SKILL.md, agents/openai.yaml, scripts, references, or assets. 也用于中文请求，例如评估该技能、审查这个技能、给技能打分、检查 Codex 技能、改进技能评估报告。
---

# Skill Evaluator

## Workflow

1. Identify the target skill directory.
   - Prefer the path explicitly provided by the user.
   - If the user gives only a skill name, look under `$CODEX_HOME/skills`, then `~/.codex/skills`.
   - Do not modify the target skill unless the user explicitly asks for edits.

2. Run the deterministic checker.
   - From this skill directory, run:

```powershell
python .\scripts\check_skill.py "C:\path\to\skill"
```

   - Use `--json <path>` only when the user needs machine-readable output.
   - Treat script output as evidence, not as a substitute for judgment.

3. Read `references/rubric.md` and apply the full rubric.
   - Score against the 100-point rubric.
   - Use the checker findings to anchor objective issues.
   - Add manual findings for unclear workflow, bloated context, missing examples, weak validation, or unsafe default behavior.

4. Review the skill contents directly.
   - Read `SKILL.md` completely.
   - Inspect `agents/openai.yaml` when present.
   - List `scripts/`, `references/`, and `assets/`; read only files needed to judge whether resources are discoverable and useful.
   - If a script is central to the skill, inspect its CLI/help text and obvious side effects before recommending it.

5. Produce the report in Chinese in this exact order:
   - `结论`
   - `评分`
   - `P0 问题`
   - `P1 问题`
   - `P2 问题`
   - `P3 问题`
   - `建议修复`
   - `验证命令`

## Finding Priorities

- `P0`: The skill cannot load, cannot be discovered, or would likely cause destructive or unsafe behavior.
- `P1`: The skill can load but is likely to trigger poorly, mislead Codex, omit essential workflow steps, or fail important validation.
- `P2`: The skill works but has maintainability, clarity, resource organization, or testing gaps.
- `P3`: Polish issues, wording improvements, minor hygiene, or optional enhancements.

## Output Rules

- Write the human-readable report in Chinese by default.
- Keep commands, paths, code identifiers, JSON field names, and priority labels such as `P0` unchanged.
- Lead with actionable findings, not praise.
- Include file paths and line numbers when practical.
- Keep suggested fixes focused; do not rewrite the whole skill unless asked.
- If no issues exist for a priority level, write `未发现。`
- End with commands the user can run to validate the reviewed skill.
- State clearly when the review was static-only and no forward-test was run.

## References

Read `references/rubric.md` for the scoring rubric and assessment checklist.
