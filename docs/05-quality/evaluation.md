# 12｜转换质量、可信度与评估体系

## 三套不能混淆的分数 [D]

1. **Runtime**：进程成功、耗时、内存、错误数、输出是否生成。
2. **Structural**：XML/HTML 合法、节点完整、章节顺序、公式/引用/资产计数。
3. **Scientific fidelity**：公式符号、表格单元、图表内容、文献关系是否和可信来源一致。

不要把任何一个分数简单合并为“质量 98%”；若必须汇总，需要公开样本、权重、评估器与阈值版本。

## 可观测指标

| 指标 | 分子 / 分母 | 注意 |
|---|---|---|
| Entry accuracy | 正确选择的顶层文件 / 有真值样本 | 多顶层按集合/顺序评分 |
| Conversion availability | 有可用 HTML 的任务 / 全部已请求任务 | 不代表内容无损 |
| Structural coverage | 与黄金结构一致的节点 / 真值节点 | 多维报告 |
| Formula retention | 保留的应有公式 / 真值公式 | 区分行内/陈列公式 |
| Symbol fidelity | 校验通过的目标数学符号 / 可比对符号 | 避免只看 MathML 存在 |
| Reference resolution | 有效可解析边 / 应有引用边 | 区分缺条目与错目标 |
| Asset completeness | 已解析资源 / 应有资源 | 需要资源清单 |
| Repair effectiveness | 修复后质量改善且无退化 / 修复尝试 | 要有未修复对照 |
| Honest abstention | 应判未知/失败且正确拒收 / 相关案例 | 防止静默“成功” |

## 质量门禁

- **Hard gate**：路径安全失败、输出不可解析、PDF/TeX 不一致但存在关键数学符号缺失证据、修复审计丢失，必须拒绝自动 ACCEPTED。
- **Soft gate**：无关视觉差异、无法验证的图片布局，进入 `PARTIAL/REVIEW_REQUIRED`。
- **Unknown**：未跑某项验证不能当作验证通过；不允许 LLM 自我打分来替代原文对齐。

## 黄金数据集（规划）

起步 40–60 个经审查的轻量 fixture，分来源类型、数学宏包、引用、图表和失败路径；再增加具合法使用权限的真实 arXiv 案例。黄金数据必须标明出处、许可、作者源码/官方 PDF 对应版本、人工断言、引擎版本。真实数据不要直接全量复制大规模 ar5iv HTML 数据集。[许可页](https://sigmathling.kwarc.info/resources/ar5iv-dataset-2024/)

## 对照实验

`Baseline: raw LaTeXML` vs `+ entry discovery` vs `+ safe recovery` vs `+ quality gate`；评估指标必须在同一语料、同一资源上限与相同引擎版本下计算。质量门禁本身不提高 raw conversion rate，但应提升“被标记为可信结果的准确率”。

## 危险反例

LaTeXML `Warn` 可能不会破坏可读性，`Error` 也可能有部分有用结果；不能粗暴把所有 warning 判作失败。相反，完全没有 fatal 也不代表公式语义正确。官方日志说明：[Error Codes](https://math.nist.gov/~BMiller/LaTeXML/manual/errorcodes/index.html)。

## 向用户报告

每篇提供：`input identification`、`selected entry`、`conversion engine/version`、`repairs`、`validation run/not_run`、`key discrepancies`、`final level`、`downloadable artifacts`。
