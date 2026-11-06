# M03｜Conservative Recovery：可审计的 LaTeX 源码恢复

> 2026-11-06 · 实现范围为**显式启用、单次受限修复**。M03 不试图重写 TeX 宏包或修复数学语义。成功生成 HTML 的统一标记为 `RECOVERED_UNVERIFIED / quality_status=NOT_EVALUATED`，科学内容仍待 M05 门禁审查。

## 一、提供的两条修复路径

### A. 已知主文件：先原样转换，再判断是否追加结束标记

~~~bash
nano-ar5iv --output ./run-data recover ./paper --entry manuscript.tex
# 可禁用所有修复，只运行一次并记录基线
nano-ar5iv --output ./run-data recover ./paper --entry manuscript.tex --max-repairs 0
~~~

执行流程：

1. 通过 M01 的 SnapshotStore 获取不可变源码快照；
2. 使用原始 `manuscript.tex` 在隔离副本转换一次，并保存 `EngineAttempt`、stderr、LaTeXML log 与 manifest；
3. 如果基线成功：返回 `BASELINE_SUCCEEDED`，**不修改任何文件**；
4. 如果失败：`diagnose_attempt` 分类首个有用错误。遇到缺少宏包/类、未知宏、数学/引用/资产、运行时超时或引擎不可用，直接返回 `REVIEW_REQUIRED`；
5. 如果静态 TeX 源码确有 `\documentclass` 和 `\begin{document}`，但没有有效 `\end{document}`，且上一步无拒绝原因，才允许生成 `APPEND_END_DOCUMENT`；
6. 对*新创建的临时副本*进行源哈希确认，追加且仅追加准确的 `\end{document}`；最多重跑一次；
7. 无论转换是否成功，保存补丁差异、修改前/后哈希及 baseline 关联；成功仅返回 `RECOVERED_UNVERIFIED`。

**限制：** 静态规则无法证明源码截断就是唯一根因，修复后内容保真尚未验证；此路径是“显式同意的保守恢复”，不是默认自动重写。

### B. 完整入口不存在：使用调用者指定的有序片段生成包装入口

~~~bash
# 不需要 Docker：先审阅将要执行的计划
nano-ar5iv --output ./run-data recover ./examples/trusted-fragments \
  --fragments intro.tex method.tex --plan-only

# 需要预先拉取的可信 ar5ivist Docker 镜像
nano-ar5iv --output ./run-data recover ./examples/trusted-fragments \
  --fragments intro.tex method.tex --document-class article

# 若有必须在 begin{document} 前加载的自定义命令
nano-ar5iv --output ./run-data recover ./examples/trusted-fragments \
  --fragments intro.tex method.tex --preamble macros.tex
~~~

只有调用者提供 `--fragments` 的**顺序、路径**和受支持的 `--document-class=article|report|book` 才能生成 `__nano_ar5iv_entry.tex`。本阶段不会从“几个不完整文件”凭空推断唯一正确拼接顺序。显式 `--preamble` 可提供一个无 `documentclass/begin/end` 的宏片段，编译头前被 `\input`。

计划只允许 1–32 个唯一、实际存在的、安全相对路径的 TeX/LaTeX 片段；拒绝完整文档、非法 TeX 目录穿越、已存在的生成文件、重复文件或无证据的任意宏包修复。

### C. 其余常见错误的处理

| 故障类型 | M03 当前处理 |
|---|---|
| 缺失 `.sty/.cls` | 诊断 + `REVIEW_REQUIRED`，不自动安装/伪造 |
| 未定义数学宏 / MathML 异常 | 诊断 + `REVIEW_REQUIRED`，不吞宏 |
| 缺失图像/文献 | 保留诊断，等待后续质量与资源层 |
| 自定义 catcode、动态 `\input` | 不尝试宏展开猜测 |
| 输入路径不安全 / 补丁目标不匹配 | 拒绝修复，原始文件保持不变 |
| 失败修复 / 超出预算 | 停止重试，输出原始与尝试记录 |
| 没有任何 TeX、仅有 PDF | 不在 M03 伪造 TeX，留给 M04 |

## 二、M03 的实际模块

| Module | 责任 |
|---|---|
| `recovery/classifier.py` | 用 runtime state 与日志首因归类错误 |
| `recovery/strategies.py` | `RecoveryPolicy`、`PatchOperation`、`RecoveryPlan` 和严格白名单 |
| `recovery/wrapper.py` | 用户提供明确顺序时，生成合成入口的单操作计划 |
| `recovery/planner.py` | 只对可证明结构缺失的失败基线提出 append-end |
| `recovery/patch_policy.py` | 路径、原始 SHA256、payload、操作类型校验与 copy-only 应用 |
| `application/recover.py` | baseline → classify → plan → retry → result |
| `application/convert.py` | 将修复审计信息与 engine output 一起持久化 |
| `interfaces/cli.py` | `recover --entry` / `recover --fragments` / `--plan-only` |

**无新增自动联网下载或 shell 拼接。** 转换仍经 M01 的固定本地 Docker adapter；命令注入不能通过恢复 API 打开新的执行能力。

## 三、产物与状态

~~~text
run-data/
  sources/<bundle-id>/manifest.json                 # immutable original
  sources/<bundle-id>/files/...
  runs/<baseline-run>/manifest.json                  # original attempt
  runs/<baseline-run>/artifacts/logs/...
  runs/<repaired-run>/manifest.json                  # second attempt
  runs/<repaired-run>/artifacts/repair.diff           # reproducible patch summary
  runs/<repaired-run>/artifacts/repair-audit.json     # plan + before/after sha256
  runs/<repaired-run>/artifacts/html/index.html      # only when engine produced it
~~~

恢复后的 manifest 新增 `repair_audit`、`parent_run`；不会篡改 baseline manifest。恢复结果的 `attempts[]` 顺序记录原始运行和修复后运行，均独立可定位；每项保存 `entry/status/manifest_path/image_id`。

- `BASELINE_SUCCEEDED`：没有发生修复；不代表论文科学内容无损。
- `RECOVERED_UNVERIFIED`：有限修复后 HTML 可以生成，但无科学内容保真认证。
- `REVIEW_REQUIRED`：策略不适用、超时、缺包或修复失败，保留诊断与所有已有产物。
- `PLAN_ONLY`：未执行转换的包装入口方案，只能与 `--fragments` 使用。

## 四、安全与限制

- 目前仅处理**用户信任且获授权的本地源码**；上传的任意 TeX 不应直接运行。
- TeX 执行在 M01 Docker 隔离参数下进行，但并未完成生产级多租户沙箱审计。
- 补丁执行只发生在 `attempt_workspace(bundle)` 的独立副本；`apply_plan` 检查原始 SHA256、路径与允许的精确 patch 操作。
- 包装计划拒绝未授权的任意 TeX 指令拼接（只支持固定 `documentclass`、`input`、`begin/end{document}`）；作者提供的具体 fragment 仍视为不可信代码，必须经沙箱。
- 注释、catcode、自定义命令等边界可能让静态扫描产生误判，M03 禁止以“已生成 HTML”来覆盖未知证据。
- 1 个失败 baseline + 最多 1 次 patched retry；不实现并发批量任务（M06）或 LLM 自动修改（M07）。

## 五、验证和阶段验收

测试：`tests/test_m03_recovery.py`（独立副本、哈希防篡改、补丁白名单、一次重试、缺包拒判）；`tests/test_m03_cli.py`（预览计划、成功/拒绝状态、保留原件）；`tests/test_real_m03_opt_in.py`（自编有序片段在真实 ar5ivist Docker 中包装成 HTML）。

**CI 结果必须以 PR #8 的实际作业为准**；合并前要求 Python 3.11/3.13 通过、历史 M01/M02 真实转换回归通过及 M03 最小真实包装入口测试通过。源码丢失的数学语义、批量宏包长尾兼容、PDF 对比、生产安全审查和修复有效性大样本统计均**不属于本轮已验收内容**。

## 六、下一阶段

M04 实现 LaTeXML XML/HTML → `PaperDocument` 的结构化归一化，并保留公式 TeX、MathML、章节、引用关系和源 provenance。M05 才进行科学符号/引用/图表质量门禁；在此之前所有恢复输出始终标记 `NOT_EVALUATED`。
