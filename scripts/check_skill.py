#!/usr/bin/env python3
"""Codex 技能目录静态检查器。

脚本默认只读，报告客观结构和卫生问题；完整技能评估仍需结合
references/rubric.md 做人工判断。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - fallback exists for minimal Python envs.
    yaml = None


NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
ALLOWED_TOP_LEVEL = {
    "SKILL.md",
    "agents",
    "scripts",
    "references",
    "assets",
    ".gitattributes",
    ".gitignore",
}
REFERENCE_EXTS = {".md", ".txt", ".json", ".yaml", ".yml", ".csv"}
SCRIPT_EXTS = {".py", ".ps1", ".sh", ".mjs", ".js", ".ts", ".rb", ".pl"}


@dataclass
class Finding:
    priority: str
    category: str
    message: str
    path: str | None = None


@dataclass
class CheckResult:
    skill_dir: str
    verdict: str
    score: int
    findings: list[Finding]
    metadata: dict[str, object]
    validation_commands: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="只读静态检查 Codex 技能目录，并输出中文评估报告。",
        add_help=False,
    )
    parser.add_argument("-h", "--help", action="help", help="显示帮助信息并退出")
    parser.add_argument("skill_dir", help="要检查的技能目录路径")
    parser.add_argument("--json", dest="json_path", help="把 JSON 结果写入指定路径")
    return parser.parse_args()


def normalize_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_simple_frontmatter(raw_frontmatter: str) -> tuple[dict[str, str], str | None]:
    metadata: dict[str, str] = {}
    for lineno, line in enumerate(raw_frontmatter.splitlines(), start=2):
        stripped = line.strip()
        if not stripped:
            continue
        if ":" not in stripped:
            return metadata, f"frontmatter 第 {lineno} 行不是简单的 key: value；当前环境缺少 PyYAML，fallback 只支持单行标量。"
        key, value = stripped.split(":", 1)
        key = key.strip()
        if key in metadata:
            return metadata, f"frontmatter 中存在重复键：{key}"
        metadata[key] = normalize_scalar(value)
    return metadata, None


def coerce_frontmatter_value(value: Any, key: str) -> tuple[str, str | None]:
    if value is None:
        return "", None
    if isinstance(value, (str, int, float, bool)):
        return str(value), None
    return "", f"frontmatter 字段 `{key}` 必须是可转为字符串的标量值。"


def parse_frontmatter(text: str) -> tuple[dict[str, str], str, str | None]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text, "SKILL.md 必须以 --- 分隔的 YAML frontmatter 开头。"

    raw_frontmatter, body = match.groups()
    if yaml is None:
        metadata, error = parse_simple_frontmatter(raw_frontmatter)
        return metadata, body, error

    try:
        loaded = yaml.safe_load(raw_frontmatter) or {}
    except Exception as exc:
        return {}, body, f"frontmatter 不是有效 YAML：{exc}"

    if not isinstance(loaded, dict):
        return {}, body, "frontmatter 必须是 YAML mapping。"

    metadata: dict[str, str] = {}
    for key, value in loaded.items():
        if not isinstance(key, str):
            return metadata, body, "frontmatter 的所有键都必须是字符串。"
        coerced, error = coerce_frontmatter_value(value, key)
        if error:
            return metadata, body, error
        metadata[key] = coerced

    return metadata, body, None


def line_count(text: str) -> int:
    return len(text.splitlines())


def contains_any(text: str, needles: Iterable[str]) -> bool:
    lower = text.lower()
    return any(needle.lower() in lower for needle in needles)


def relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def add(
    findings: list[Finding],
    priority: str,
    category: str,
    message: str,
    path: Path | None = None,
    root: Path | None = None,
) -> None:
    findings.append(
        Finding(
            priority=priority,
            category=category,
            message=message,
            path=relative(path, root)
            if path is not None and root is not None
            else str(path)
            if path
            else None,
        )
    )


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def list_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return [
        item
        for item in path.rglob("*")
        if item.is_file() and "__pycache__" not in item.parts
    ]


def inspect_agents_yaml(skill_dir: Path, skill_name: str, findings: list[Finding]) -> None:
    agents_path = skill_dir / "agents" / "openai.yaml"
    if not agents_path.exists():
        add(
            findings,
            "P2",
            "hygiene",
            "缺少 agents/openai.yaml；如果希望技能在 UI 列表中清晰展示，应补充该文件。",
            agents_path,
            skill_dir,
        )
        return

    try:
        text = read_text(agents_path)
    except UnicodeDecodeError:
        add(findings, "P1", "hygiene", "agents/openai.yaml 不是可读取的 UTF-8 文件。", agents_path, skill_dir)
        return

    for field in ("display_name", "short_description", "default_prompt"):
        if f"{field}:" not in text:
            add(findings, "P2", "hygiene", f"agents/openai.yaml 缺少 interface.{field}。", agents_path, skill_dir)

    if "default_prompt:" in text and f"${skill_name}" not in text:
        add(
            findings,
            "P1",
            "hygiene",
            f"interface.default_prompt 应显式包含 ${skill_name}。",
            agents_path,
            skill_dir,
        )


def inspect_resources(skill_dir: Path, body: str, findings: list[Finding]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for dirname in ("scripts", "references", "assets"):
        dir_path = skill_dir / dirname
        files = list_files(dir_path)
        counts[dirname] = len(files)
        if not dir_path.exists():
            continue

        if files and dirname not in body:
            add(
                findings,
                "P2",
                "progressive-disclosure",
                f"{dirname}/ 中有文件，但 SKILL.md 没有说明何时使用它们。",
                dir_path,
                skill_dir,
            )

        if not files and dirname in body:
            add(
                findings,
                "P3",
                "resource-design",
                f"SKILL.md 提到了 {dirname}/，但该目录没有文件。",
                dir_path,
                skill_dir,
            )

    for script in list_files(skill_dir / "scripts"):
        if script.suffix.lower() not in SCRIPT_EXTS:
            add(
                findings,
                "P3",
                "resource-design",
                f"scripts/ 中包含不常见的文件类型：{script.name}。",
                script,
                skill_dir,
            )

    for ref in list_files(skill_dir / "references"):
        if ref.suffix.lower() not in REFERENCE_EXTS:
            add(
                findings,
                "P3",
                "resource-design",
                f"references/ 中包含不常见的文件类型：{ref.name}。",
                ref,
                skill_dir,
            )

    return counts


def inspect_skill(skill_dir: Path) -> CheckResult:
    skill_dir = skill_dir.resolve()
    findings: list[Finding] = []
    metadata: dict[str, object] = {
        "exists": skill_dir.exists(),
        "resource_counts": {},
        "skill_md_lines": 0,
        "score_type": "static_check_score",
    }

    if not skill_dir.exists() or not skill_dir.is_dir():
        add(findings, "P0", "structure", "目标路径不是现有目录。", skill_dir)
        return finalize(skill_dir, findings, metadata)

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        add(findings, "P0", "structure", "缺少 SKILL.md。", skill_md, skill_dir)
        return finalize(skill_dir, findings, metadata)

    try:
        text = read_text(skill_md)
    except UnicodeDecodeError:
        add(findings, "P0", "structure", "SKILL.md 不是可读取的 UTF-8 文件。", skill_md, skill_dir)
        return finalize(skill_dir, findings, metadata)

    metadata["skill_md_lines"] = line_count(text)
    frontmatter, body, fm_error = parse_frontmatter(text)
    metadata["frontmatter_keys"] = sorted(frontmatter.keys())
    metadata["yaml_parser"] = "PyYAML" if yaml is not None else "simple-fallback"
    skill_name = frontmatter.get("name", "")
    description = frontmatter.get("description", "")

    if fm_error:
        add(findings, "P0", "structure", fm_error, skill_md, skill_dir)

    extra_keys = sorted(set(frontmatter) - {"name", "description"})
    if extra_keys:
        add(
            findings,
            "P2",
            "trigger-metadata",
            f"frontmatter 只应包含 name 和 description；当前多出：{', '.join(extra_keys)}。",
            skill_md,
            skill_dir,
        )

    if not skill_name:
        add(findings, "P0", "trigger-metadata", "frontmatter 缺少 name。", skill_md, skill_dir)
    elif not NAME_RE.match(skill_name):
        add(findings, "P1", "trigger-metadata", f"技能名不是小写 hyphen-case：{skill_name}。", skill_md, skill_dir)
    elif len(skill_name) >= 64:
        add(findings, "P2", "trigger-metadata", "技能名应少于 64 个字符。", skill_md, skill_dir)

    if skill_name and skill_dir.name != skill_name:
        add(
            findings,
            "P1",
            "trigger-metadata",
            f"技能名 `{skill_name}` 与目录名 `{skill_dir.name}` 不一致。",
            skill_md,
            skill_dir,
        )

    if not description:
        add(findings, "P0", "trigger-metadata", "frontmatter 缺少 description。", skill_md, skill_dir)
    else:
        if "TODO" in description or "[" in description and "]" in description:
            add(findings, "P1", "trigger-metadata", "description 似乎仍包含模板占位文本。", skill_md, skill_dir)
        if len(description) < 80:
            add(findings, "P1", "trigger-metadata", "description 过短，难以支持可靠的隐式触发。", skill_md, skill_dir)
        if len(description) > 700:
            add(findings, "P2", "trigger-metadata", "description 很长；触发 metadata 应保持精简。", skill_md, skill_dir)
        if not contains_any(description, ("Use when", "Use for", "when Codex", "trigger", "asked to")):
            add(
                findings,
                "P1",
                "trigger-metadata",
                "description 应包含具体的使用或触发场景。",
                skill_md,
                skill_dir,
            )

    if not body.strip():
        add(findings, "P0", "workflow", "SKILL.md 正文为空。", skill_md, skill_dir)
    else:
        if "TODO" in body:
            add(findings, "P1", "workflow", "SKILL.md 仍包含 TODO 或模板残留。", skill_md, skill_dir)
        if line_count(body) > 500:
            add(findings, "P2", "progressive-disclosure", "SKILL.md 正文超过 500 行；应将详细材料移入 references/。", skill_md, skill_dir)
        elif line_count(body) > 300:
            add(findings, "P3", "progressive-disclosure", "SKILL.md 正文偏长；可考虑将细节移入 references/。", skill_md, skill_dir)
        if not contains_any(body, ("## Workflow", "## Quick Start", "## Core", "## Process", "## Procedure", "## 工作流", "## 流程")):
            add(findings, "P2", "workflow", "SKILL.md 缺少明显的 workflow/process 章节。", skill_md, skill_dir)
        if not contains_any(body, ("validate", "verify", "test", "check", "inspect", "run", "验证", "检查", "测试")):
            add(findings, "P2", "validation", "SKILL.md 没有说明如何验证或检查结果。", skill_md, skill_dir)
        if not contains_any(body, ("do not", "unless", "ask", "confirm", "safe", "destructive", "不要", "除非", "确认", "安全", "破坏")):
            add(findings, "P3", "safety-scope", "SKILL.md 缺少明确的安全或范围约束。", skill_md, skill_dir)

    metadata["resource_counts"] = inspect_resources(skill_dir, body, findings)
    inspect_agents_yaml(skill_dir, skill_name or skill_dir.name, findings)

    for item in skill_dir.iterdir():
        if item.name == ".git":
            continue
        if item.name not in ALLOWED_TOP_LEVEL:
            add(
                findings,
                "P3",
                "hygiene",
                f"发现非预期的顶层文件或目录：{item.name}。",
                item,
                skill_dir,
            )

    for clutter_name in ("README.md", "CHANGELOG.md", "INSTALLATION_GUIDE.md", "QUICK_REFERENCE.md"):
        clutter = skill_dir / clutter_name
        if clutter.exists():
            add(
                findings,
                "P2",
                "hygiene",
                f"{clutter_name} 通常不应放在 Codex 技能目录内。",
                clutter,
                skill_dir,
            )

    return finalize(skill_dir, findings, metadata)


def find_skill_evaluator_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def find_quick_validate(skill_evaluator_dir: Path) -> Path | None:
    skills_root = skill_evaluator_dir.parent
    candidate = skills_root / ".system" / "skill-creator" / "scripts" / "quick_validate.py"
    return candidate if candidate.exists() else None


def finalize(skill_dir: Path, findings: list[Finding], metadata: dict[str, object]) -> CheckResult:
    penalty = {"P0": 35, "P1": 15, "P2": 7, "P3": 2}
    score = 100
    for finding in findings:
        score -= penalty.get(finding.priority, 0)
    score = max(0, min(100, score))

    if any(f.priority == "P0" for f in findings):
        verdict = "存在关键问题，修复前不建议使用"
    elif score >= 90:
        verdict = "优秀，可直接使用，最多需要少量润色"
    elif score >= 75:
        verdict = "良好，可用，但建议做针对性改进"
    elif score >= 60:
        verdict = "需要修订后再用于重要工作"
    elif score >= 40:
        verdict = "存在较大缺口，建议大幅重写"
    else:
        verdict = "暂不可作为 Codex 技能使用"

    skill_evaluator_dir = find_skill_evaluator_dir()
    checker_path = skill_evaluator_dir / "scripts" / "check_skill.py"
    quick_validate = find_quick_validate(skill_evaluator_dir)
    validation_commands: list[str] = []
    if quick_validate is not None:
        validation_commands.append(f'python "{quick_validate}" "{skill_dir}"')
    else:
        metadata["quick_validate_note"] = "未在当前 skills 根目录找到 .system/skill-creator/scripts/quick_validate.py；请在本机安装位置另行运行 quick_validate.py。"
    validation_commands.append(f'python "{checker_path}" "{skill_dir}"')

    return CheckResult(str(skill_dir), verdict, score, findings, metadata, validation_commands)


def resource_profile_name(scripts: int, references: int, assets: int) -> str:
    if scripts and references:
        return "脚本+参考资料型技能"
    if scripts:
        return "脚本型技能"
    if references:
        return "参考资料型技能"
    if assets:
        return "资产型技能"
    return "单文件技能"


def print_text(result: CheckResult) -> None:
    grouped: dict[str, list[Finding]] = {priority: [] for priority in ("P0", "P1", "P2", "P3")}
    for finding in result.findings:
        grouped.setdefault(finding.priority, []).append(finding)

    resource_counts = result.metadata.get("resource_counts", {})
    if not isinstance(resource_counts, dict):
        resource_counts = {}
    scripts = int(resource_counts.get("scripts", 0) or 0)
    references = int(resource_counts.get("references", 0) or 0)
    assets = int(resource_counts.get("assets", 0) or 0)
    profile = resource_profile_name(scripts, references, assets)

    print("结论")
    print(result.verdict)
    print(f"资源画像：{profile}（{scripts} 个脚本，{references} 个参考文件，{assets} 个资产文件）")
    print()
    print("静态检查分")
    print(f"{result.score}/100")
    print("提示：静态检查分只来自确定性脚本，不是最终 rubric 综合分；完整评估需按 references/rubric.md 另行判断。")
    print("提示：本脚本不会生成 rubric 分项；完整评估必须人工补充 8 个分项小分和扣分理由。")
    print()
    for priority in ("P0", "P1", "P2", "P3"):
        print(f"{priority} 问题")
        if not grouped.get(priority):
            print("未发现。")
        else:
            for finding in grouped[priority]:
                location = f" [{finding.path}]" if finding.path else ""
                print(f"- {finding.category}: {finding.message}{location}")
        print()

    print("实践差异风险")
    print("- 静态检查器只能提醒人工检查，不能判定目标技能的跨实践结果差异；完整评估需检查被评估技能的输入边界、输出契约、环境依赖、外部状态、可选流程、副作用路径、输出或评分锚点，以及验证或 forward-test 证据。")
    print()
    print("建议修复")
    if not result.findings:
        print("- 静态检查未发现必须修复的问题。依赖该分数前，仍应结合 rubric 综合分和实践差异风险做人工判断，尤其检查目标技能在不同实践中是否可能产生不同输出、文件修改、外部动作或结论。")
    else:
        for finding in result.findings[:8]:
            location = f"（{finding.path}）" if finding.path else ""
            print(f"- 修复 {finding.priority} {finding.category}{location}：{finding.message}")
    print()
    print("验证命令")
    for command in result.validation_commands:
        print(f"- {command}")
    note = result.metadata.get("quick_validate_note")
    if isinstance(note, str):
        print(f"- 提示：{note}")


def main() -> int:
    args = parse_args()
    result = inspect_skill(Path(args.skill_dir))
    print_text(result)

    if args.json_path:
        output_path = Path(args.json_path)
        output_path.write_text(
            json.dumps(asdict(result), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    return 1 if any(f.priority == "P0" for f in result.findings) else 0


if __name__ == "__main__":
    sys.exit(main())
