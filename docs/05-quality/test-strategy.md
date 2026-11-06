# 14｜测试矩阵与自我验证要求（设计稿）

当前尚无业务代码或测试运行。本文件定义未来每批工程 PR 的证据标准。

## Unit / Contract / Integration / E2E

| 层级 | 测试对象 | 核心断言 |
|---|---|---|
| unit | 路径规范、manifest parser、图遍历、评分 | deterministic、无越界 |
| contract | EngineAdapter、PaperDocument、RecoveryPlan | 稳定字段、错误分支 |
| integration | 已固定版本的 LaTeXML/沙箱 | 真实日志与产物 |
| E2E | bundle→HTML/IR→质量报告 | 多模式、多入口、失败恢复 |
| security | 归档、TeX、HTML/SVG 恶意输入 | 限额和隔离有效 |
| regression | 外部 issue 最小复现样本 | 原问题未回归 |

## 入口检测 fixtures

`F01` single `main.tex`；`F02` main renamed `ms.tex`；`F03` nested root；`F04` two valid root documents；`F05` arXiv `00README.json` top-level；`F06` legacy `00README.XXX`；`F07` files only with `\\input` fragments；`F08` cycle；`F09` comment/verbatim contains fake `\\input`；`F10` duplicate names；`F11` no TeX / PDF only；`F12` dynamic `\\csname`/macro path。

每例记录**期望 root 列表、候选理由及未解析边**；无法确定时正确 `AMBIGUOUS` 是“成功拒判”，不是失败。

## 恢复 fixtures

`R01` missing documentclass（允许合成且标记 synthetic）；`R02` missing sty（不静默删除宏）；`R03` wrong graphics path；`R04` missing bbl / bib；`R05` truncated TeX；`R06` repeated error cascade；`R07` timeout；`R08` multi-root incorrectly merged；`R09` invalid MathML；`R10` LLM suggested patch changes equation（必须拒绝）。

## 科学内容 fidelity fixtures

`Q01` 数学字体/希腊符号（对照 [#7007](https://github.com/arXiv/html_feedback/issues/7007)）；`Q02` 参考文献/化学式（[#6475](https://github.com/arXiv/html_feedback/issues/6475)）；`Q03` 图表重叠（[#6317](https://github.com/arXiv/html_feedback/issues/6317)）；`Q04` 引用目标缺失；`Q05` 带括号跨行公式；`Q06` 复杂表头跨度；`Q07` 图片缺失但含图注；`Q08` 仅 CSS 导航可发现性（[#6544](https://github.com/arXiv/html_feedback/issues/6544) 更正后的定位）。

## Golden 产物

每个 fixture 至少包含：`README.md`（来源/许可/最小复现）、`input/`、`expected-entry.json`、`expected-issues.json`、`golden-assertions.json`。对真实论文不盲目提交全部原件：必要时只存 ID、版本、下载说明和可分发的最小片段。

## PR 验收模板

- 固定引擎和工作环境版本；
- 记录基线 vs 改动后的成功数、保真变化和资源成本；
- 单独列出新增失败及“未验证”范围；
- 确保原件不变、修复 diff 可审阅；
- 运行涉及模块的单元、契约、集成、E2E、沙箱测试（若尚未实现，明确标 `not_run`）；
- 决定是否需要人工科学内容复核。
