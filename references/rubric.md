# Skill Evaluation Rubric

Use this rubric to score Codex skills out of 100. The deterministic checker covers objective hygiene; the evaluator should still apply judgment to workflow fit, context economy, and validation quality.

## Trigger Metadata - 20

- 5: `SKILL.md` exists and has valid YAML frontmatter.
- 5: `name` is lowercase hyphen-case, concise, and matches the skill folder.
- 7: `description` explains both what the skill does and when to use it.
- 3: `description` includes concrete trigger contexts without overbroad claims.

## Workflow Clarity - 20

- 6: The main workflow is ordered, executable, and easy to follow.
- 5: Instructions are imperative and specific enough for another Codex instance.
- 4: Important inputs, outputs, and stopping conditions are clear.
- 3: The skill avoids generic filler and TODO/template residue.
- 2: The output format or completion criteria are explicit when needed.

## Progressive Disclosure - 15

- 5: `SKILL.md` stays lean and contains only core routing/workflow instructions.
- 4: Detailed guidance is moved to `references/` when it would bloat context.
- 3: Referenced files are named from `SKILL.md` with clear load conditions.
- 3: The skill avoids deeply nested or duplicated reference material.

## Resource Design - 15

- 5: `scripts/`, `references/`, and `assets/` are used only when they add real value.
- 4: Scripts have clear CLIs, avoid hidden destructive side effects, and can be run independently.
- 3: Assets or templates are discoverable and tied to the workflow.
- 3: Resource names and directory structure match the skill's tasks.

## Validation - 15

- 5: The skill tells Codex how to validate the work it performs.
- 4: Included scripts or commands can be smoke-tested.
- 3: The skill covers common failure modes or residual-risk reporting.
- 3: Complex skills include guidance for forward-testing or realistic examples.

## Safety and Scope - 10

- 4: The skill has safe defaults around file edits, external systems, and destructive actions.
- 3: It respects user intent and avoids expanding scope without confirmation.
- 3: It states when to ask for clarification or stop.

## Hygiene - 5

- 2: `agents/openai.yaml` is present and consistent when UI metadata is expected.
- 1: No unnecessary README, CHANGELOG, or process notes are included.
- 1: File names, links, and paths are stable and resolve correctly.
- 1: Formatting is readable and compatible with Markdown.

## Verdict Bands

- 90-100: Excellent; ready to use with only minor polish.
- 75-89: Good; usable, with focused improvements recommended.
- 60-74: Needs revision before relying on it for important work.
- 40-59: Major gaps; rebuild or substantially rewrite.
- 0-39: Not usable as a Codex skill until critical issues are fixed.

## Chinese Report Example

Use this compact shape for human-readable reports:

```markdown
结论
可用，但需要修复一个触发描述问题。

评分
85/100

P0 问题
未发现。

P1 问题
- trigger-metadata: `description` 没有说明何时使用该技能。[SKILL.md]

建议修复
- 在 frontmatter `description` 中加入具体触发场景。

验证命令
- python path\to\quick_validate.py "path\to\skill"
- python path\to\check_skill.py "path\to\skill"
```

## Manual Review Checklist

- Does the description make implicit invocation likely to work?
- Could a fresh Codex instance use the skill without hidden context?
- Are long or variant-specific details loaded only when needed?
- Are scripts justified by repeatability or reliability?
- Are validation commands concrete and non-destructive by default?
- Are public OpenAI/Codex claims grounded in official docs or the local skill-creator guidance?
