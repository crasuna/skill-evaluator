---
name: skill-evaluator
description: Evaluate Codex skill folders and produce Chinese reports for structure, trigger quality, workflow clarity, progressive disclosure, bundled resource design, validation coverage, safe scope, and result-variance risks in the target skill's real use. Use when Codex is asked to review, score, QA, audit, improve, or compare a Codex skill. 也用于中文请求，例如评估该技能、审查这个技能、给技能打分、检查 Codex 技能、检查实践差异、检查目标技能在不同实践中是否可能产生不同结果、改进技能评估报告。
---

# Skill Evaluator

## Workflow

1. 定位目标技能目录。
   - 优先使用用户明确给出的路径。
   - 如果用户给出的是 `SKILL.md` 文件路径，目标技能目录为该文件的父目录；传给 `scripts/check_skill.py` 前必须归一化为目录路径。
   - 如果用户只给技能名，先在 `$CODEX_HOME/skills`，再在 `~/.codex/skills` 下解析成技能目录路径。
   - `scripts/check_skill.py` 只接受技能目录路径，不直接解析技能名。
   - 除非用户明确要求修复，否则不要修改被评估技能。
   - 本文中的 `目标技能` 或 `被评估技能` 始终指用户要求评估的技能目录，不是 `skill-evaluator` 自己，除非用户明确要求自评。

2. 运行确定性静态检查器。
   - 从本技能目录运行：

```powershell
python .\scripts\check_skill.py "C:\path\to\skill"
```

   - 只有用户需要机器可读结果时才使用 `--json <path>`。
   - 将脚本输出视为证据和静态检查分，不要把它当作最终 rubric 综合分。

3. 读取 `references/rubric.md` 并应用完整 rubric。
   - 给出 `静态检查分`：直接引用检查器输出。
   - 给出 `rubric 综合分`：按 100 分 rubric 人工判断。
   - 给出 `rubric 分项`：列出 8 个分类的小分，格式为 `分类名：x/y - 一句扣分理由`；满分项写 `无扣分。`
   - 确保 `rubric 综合分` 等于 8 个分项小分之和，不要只给总分。
   - 使用检查器 findings 锚定客观问题。
   - 补充脚本无法判断的问题，例如流程含混、上下文臃肿、缺少真实验证、默认行为不安全、结果一致性风险。

4. 检查实践差异风险。
   - 先识别目标技能的核心任务和预期产物，例如生成文件、修改代码、调用外部服务、输出分析报告、给出评分或执行验证。
   - 将实践差异定义为：同一目标技能在不同执行者、线程、输入选择、环境、工具状态或多次运行中，是否可能产生不同输出、分数、文件修改、外部动作或结论。
   - 检查风险来源：输入边界、文件选择、执行顺序、可选分支、环境依赖、外部服务、时间/网络状态、模型主观判断、输出契约、验证方式和副作用路径。
   - 将说明与实现一致性作为风险诱因之一：对比目标技能的 `SKILL.md` 承诺、引用材料、脚本实际 CLI/输出、`agents/openai.yaml` 默认提示与真实工作流。
   - 将这些内容写入 `实践差异风险`，即使静态检查器没有报错。
   - 必须在以下任一情况运行重复评估或 forward-test：用户要求深度评估或比较多个技能；目标技能会生成/修改文件、调用外部服务或产生远程副作用；存在多个候选目标且无法仅凭路径稳定选择；发现 `P0`/`P1`、rubric 任一分项扣分且原因无法通过静态阅读确认、或高实践差异风险；目标技能本身要求 forward-test。
   - 重复评估或 forward-test 必须使用安全 fixture、临时副本或用户明确授权的目标环境，避免扩大文件、外部服务或远程状态副作用。
   - 其他情况默认静态评估，并说明未运行重复评估或 forward-test。

5. 直接审阅技能内容。
   - 完整阅读 `SKILL.md`。
   - 检查 `agents/openai.yaml`。
   - 列出 `scripts/`、`references/`、`assets/`；只读取判断资源可发现性和有效性所需的文件。
   - 如果脚本是技能核心，检查其 CLI/help 文案和明显副作用。

6. 用中文按以下顺序输出报告：
   - `结论`
   - `静态检查分`
   - `rubric 综合分`
   - `rubric 分项`
   - `P0 问题`
   - `P1 问题`
   - `P2 问题`
   - `P3 问题`
   - `实践差异风险`
   - `建议修复`
   - `验证命令`

## 问题优先级

- `P0`：技能无法加载、无法发现，或默认行为可能造成破坏性/高风险后果。
- `P1`：技能可加载，但很可能触发不准、误导 Codex、遗漏关键流程，或重要验证缺失。
- `P2`：技能可用，但存在维护性、清晰度、资源组织、验证覆盖或实践差异风险。
- `P3`：措辞、格式、示例、卫生或可选增强问题。

## Output Rules

- 默认用中文写人类可读报告。
- 命令、路径、代码标识符、JSON 字段名、category ID 和 `P0` 等优先级标签保持原样。
- 先列可执行问题，不要先写表扬。
- 尽量给出文件路径和行号。
- 修复建议保持聚焦；除非用户要求，不要重写整个技能。
- 某个优先级没有问题时写 `未发现。`
- `rubric 分项` 必须包含 8 个分类的小分和一句扣分理由；满分项写 `无扣分。`
- `实践差异风险` 没有发现时写 `未发现。`，但仍说明本次是否运行了重复评估或 forward-test。
- 明确说明本次评估是否只是静态评估，是否运行了 forward-test。
- 如果用户要求“自评无问题”或持续修复闭环，结束条件为：静态检查 `100/100` 且无 `P0`-`P3`，`rubric 综合分` 为 `100/100`，8 个分项均满分，`实践差异风险` 为 `未发现。`，并且验证命令通过。
- 结尾给出用户可运行的验证命令。

## References

读取 `references/rubric.md` 获取评分 rubric、实践差异风险检查项和报告示例。
