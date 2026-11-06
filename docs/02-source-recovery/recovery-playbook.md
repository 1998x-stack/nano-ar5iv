# 05｜不规范源码恢复与降级手册

## 总体策略：只修复有证据的地方 [D]

`unpack → inventory → entry discovery → baseline conversion → first-cause diagnostics → limited repair → rerun → quality gate → fallback`。

### S0：直接转换

当入口、依赖、资源完整，优先直接调用 LaTeXML/ar5ivist。`ar5ivist --source` 参数**接收实际主文件名**，无需强行改名 `main.tex`。[ar5ivist README](https://github.com/dginev/ar5ivist)

### S1：元数据/路径修复

恢复相对目录、识别附带的旧 `00README.XXX`、确认大小写、用等价的工作目录路径构造；**不要将引用文件移入或覆写作者源码**。如可确定唯一入口，保持文件名不变。

### S2：合成包装入口

对于仅有章节片段的归档，在独立工作空间生成 `__generated_main.tex`。必要条件：能够确定加载顺序；能够确定或合理假设 `documentclass`；合成的 `\\input` 指向实际文件；有完整修复清单。**不能仅因缺 `\\documentclass` 就随意假设 `article` 必然正确**；生成结果标为 `synthetic_root=true`、`quality=review_required`。

### S3：依赖兼容

- 优先寻找原始 .sty/.cls 与已安装的合法宏包；
- 确认宏包选项、绑定支持与 LaTeXML 日志的关联；
- 基于最小复现识别“根因触发的连锁错误”，例如 [ar5iv #437](https://github.com/dginev/ar5iv/issues/437)；
- 对不认识的符号/定理**禁止以空宏吞掉内容**。允许做保留原始源码的占位标记，输出质量降级。
- 不擅自在线下载任意第三方宏包到运行环境。

### S4：有限 LLM 辅助（可选、默认关闭）

输入限于最小失败片段、诊断、已知相关上下文、白名单可修改范围。模型只可给出**候选补丁**；先检查语法差异及作用域，再在隔离副本重试。不得修改数学常数、公式意义、参考文献事实。单作业最多有限次数（建议 2 次为初始默认，后由评测决定），超限终止；存储补丁、模型版本、审查信息。任何未能通过差分验证的补丁均拒绝应用。

### S5：PDF / HTML 兜底

如果没有 TeX 或恢复仍失败：优先可验证的官方 HTML（若许可、版本、获取条件允许），否则 PDF 结构分析；PDF-only 结果必须标 `source_type=pdf`，公式/引用的推断标记较低可信度。**不能把 OCR 还原的 LaTeX 冒充作者源码**。

## 诊断分类矩阵

| 诊断族 | 观察 | 建议动作 | 不允许 |
|---|---|---|---|
| `ENTRY_NOT_FOUND` | 无唯一入口 | metadata、图、排序、多候选试转 | 猜测 `main.tex` |
| `DEPENDENCY_MISSING` | .sty/.cls/.tex 找不到 | 包清单、路径核对、兼容 binding | 网络随意安装 |
| `UNKNOWN_MACRO` | 未定义控制序列 | 最小复现与 binding 策略 | 无声删宏 |
| `MATH_PARSE` | 数学结构异常 | 保留原 TeX、记录差异 | 编造公式 |
| `ASSET_MISSING` | 图找不到 | 本地资源映射、占位 | 默默删图 |
| `BIB_MISSING` | 文献/编号缺失 | 检查 .bib/.bbl 与 cite 图 | 捏造条目 |
| `TIMEOUT` | 资源耗尽 | 限额、热点识别、降级 | 无限重试 |
| `IR_INVALID` | XML/IR 不可验证 | 记录并回退上一版本 | 标为成功 |

LaTeXML 错误类别参见[官方错误码](https://math.nist.gov/~BMiller/LaTeXML/manual/errorcodes/index.html)。其错误也可能是**转换器缺陷**而非作者错误。

## 状态机

`DISCOVERED → ANALYZED → BASELINE_ATTEMPTED → (REPAIR_PLANNED → REPAIR_ATTEMPTED)* → VALIDATED → {ACCEPTED, PARTIAL, PDF_FALLBACK, REVIEW_REQUIRED, REJECTED}`。严格限制循环次数与资源；异常路径同样应生成报告。

## 不变式

原始文件只读；修复补丁可 diff；同样的输入/配置生成相同修复计划（LLM 启用则另记非确定性）；每个生成节点有原始来源或显式 synthetic 标记；拒绝“静默丢失公式/表格/参考文献”。
