# 复现测试矩阵与对照实验（计划）

**状态：TESTS NOT IMPLEMENTED / RESULTS NOT RUN。** 所有如下测试都是计划的 fixture/期望断言，不是历史测试通过记录。

## A. 入口发现（E）

| ID | 输入情况 | 期望（可判断 / 正确拒判） |
|---|---|---|
| E01 | 单一 `main.tex` | root=main.tex |
| E02 | `manuscript.tex` | root=manuscript.tex |
| E03 | 子目录根 + 多段 input | root=subdir/paper.tex、完整依赖图 |
| E04 | 2 个合法顶层文档 | `DocumentSet` 且保持顺序 |
| E05 | 新 `00README.json` 指向正确 root | 尊重 manifest |
| E06 | 旧 `00README.XXX` 与多 root | 保留 toplevelfile 语义 |
| E07 | manifest 指向不存在文件 | 显式 missing |
| E08 | 动态生成 `\\input` 名称 | unresolved_dynamic |
| E09 | 注释/verbatim 含伪 `\\input` | 不错误产生边 |
| E10 | 软链接指向沙箱外 | 拒绝输入 |
| E11 | 仅片段无 documentclass | wrapper proposal / review |
| E12 | PDF-only | source_kind=pdf，未冒充 TeX |

## B. 恢复与兼容（R）

| ID | 输入/故障 | 期望 |
|---|---|---|
| R01 | 已识别但名称不是 main | 直接转换 |
| R02 | wrapper 模式可确定顺序 | 合成文件、diff/provenance |
| R03 | 无法确定片段顺序 | REVIEW_REQUIRED |
| R04 | 缺少自定义类文件 | 提供根因，不删除宏 |
| R05 | 引用文件大小写不一致 | 有证据的路径修复 |
| R06 | 宏引起错误级联 | first-cause 与子错误分离 |
| R07 | 缺少图片文件 | 保留 caption 和 unresolved ref |
| R08 | 不完整 .bib/.bbl | citation mismatch |
| R09 | 转换卡住 | timeout + bounded attempts |
| R10 | LLM 补丁删掉公式 | 拒绝补丁（M07 可选） |

## C. 内容保真（Q）

| ID | 重要对象 | 必须观察 |
|---|---|---|
| Q01 | Greek math symbols | 原 TeX 符号/MathML 对齐 |
| Q02 | 展示公式编号 | label、引用目标 |
| Q03 | 跨章节 cite 与 bib | citation graph 全连通 |
| Q04 | 图、图注、SVG | 资产、caption、资源 hash |
| Q05 | 单元格跨度和复杂表格 | span、文本内容 |
| Q06 | CSS 重叠但数据齐全 | 视觉错误不与结构混淆 |
| Q07 | HTML 缺符号但无 fatal | 质量硬门禁不得接受 |
| Q08 | 只有 PDF 无法恢复 TeX | provenance=pdf，未知维度保留 |

## D. 可重复和沙箱（S）

S01 archive traversal、S02 解压比例/总大小限制、S03 symlink、S04 无网络访问、S05 CPU/内存/超时、S06 禁止 shell-escape、S07 禁止读取宿主文件、S08 HTML/SVG 脚本隔离、S09 cache 配置分隔、S10 worker checkpoint/replay。每例都需**真实运行与可复制证据**，不能只写测试名称。

## E. 对照设计

- `B0`：上游手动直转（选择入口已知的样本）。
- `B1`：+ metadata/entry discovery（入口正确率、耗时）。
- `B2`：+ conservative recovery（新增保留内容、无回归比例）。
- `B3`：+ canonical IR（结构/引用覆盖率）。
- `B4`：+ quality gate（false-acceptance、unknown 判定）。

在同一真实语料、固定引擎版本和资源限制下评价。实际目标阈值必须由 pilot 样本建立，不能把本页示例当 SLA。

## F. 每次实验的完整证据

记录 `environment/engine-image-digest/source-id+version/source-sha256/root-entry/command/config/attempt-log/raw-XML/raw-HTML/quality-report/checksum/time/resources/test-assertions`。失败样本同样要保存；关键指标报告分母，不能只列漂亮案例。现实论文素材遵守内容许可。

参考：[详细测试策略](../05-quality/test-strategy.md)。
