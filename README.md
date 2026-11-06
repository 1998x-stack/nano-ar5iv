# nano-ar5iv

**Recoverable · Reproducible · Auditable LaTeX → XML → HTML5/MathML → PaperDocument**

**项目状态：v0.6 M04 Canonical PaperDocument — M01–M03 已合并；M04 实现从已核验 LaTeXML XML / ar5ivist HTML 中生成版本化论文 IR、公式、表格、引用、来源和派生哈希。M04 正在 PR #10 验证；PDF-only fallback、M05–M07 未实现，科学保真度尚未验收。**  
最后更新：2026-11-06 · 语言：中文 / English terminology

> nano-ar5iv 不是 LaTeXML / ar5iv 的替代品，也不是其官方项目。我们设计的是**围绕成熟转换引擎**的论文源码发现、规范化、异常恢复、质量验证、批量处理和结构化输出系统。当前仓库已实现 M01 基线、M02 入口发现、M03 保守恢复，并新增 M04 的 PaperDocument 归一化；科学质量门禁、PDF-only fallback 和后台服务仍是占位。输出 HTML 不代表论文科学内容保真。

## 目录

- [一、为什么需要 nano-ar5iv](#一为什么需要-nano-ar5iv)
- [二、总体原理与处理流水线](#二总体原理与处理流水线)
- [三、当前状态与边界](#三当前状态与边界)
- [四、如何先复现上游转换原理](#四如何先复现上游转换原理)
- [五、九大代码 Category 与仓库结构](#五九大代码-category-与仓库结构)
- [六、核心逻辑与恢复状态机](#六核心逻辑与恢复状态机)
- [七、设计中的接口与产物](#七设计中的接口与产物)
- [八、测试、指标与安全](#八测试指标与安全)
- [九、完整文档导航](#九完整文档导航)
- [十、阶段路线图](#十阶段路线图)
- [十一、贡献与参考](#十一贡献与参考)

## 一、为什么需要 nano-ar5iv

ar5iv/LaTeXML 让许多 LaTeX 论文拥有网页可读的 HTML5/MathML：它从**作者提供的 TeX 源码**推导 XML 结构，通过交叉引用、参考文献、数学、图形及 XSLT 等步骤生成 HTML，而不是先生成 PDF 再做 OCR。

真实世界的论文源码却有长尾复杂性：

| 场景 | 输入例子 | nano-ar5iv 的**目标处理方式** |
|---|---|---|
| 主文件不叫 main.tex | `paper.tex` / `ms.ltx` | 元数据优先 + 入口候选排序 |
| 多文件/多层级 | `chapters/*.tex` + `\\input` | 依赖图与文件角色判断 |
| 多个顶层论文 | 正文 + 独立 supplement | `DocumentSet`，不盲目拼接 |
| 不完整源码 | 缺 preamble/闭合环境 | 隔离工作区生成有限修复副本 |
| 不认识的宏包/类 | `.sty` / `.cls` 兼容问题 | 日志根因分类 + 保守降级 |
| 数学/引用/图表错误 | MathML 缺符号 / cite 断链 | 内容层质量门禁，不以 HTML 存在即成功 |
| 只有 PDF | 无 TeX | 独立 PDF fallback，标明低可信内容来源 |

**价值目标：可转换时尽量保真；不能保真时明确说明，并保留来源和修复证据。**

## 二、总体原理与处理流水线

~~~text
                USER SOURCE / arXiv SOURCE / LOCAL ARCHIVE
                                  |
                       01  Archive & Inventory
                       02  Manifest (00README)
                       03  TeX Dependency Graph
                       04  Entry Decision / DocumentSet
                                  |
                        baseline conversion
                                  |
             +--------------------+------------------+
             |                                       |
       LaTeXML / ar5ivist                   Conversion Failure
       TeX -> XML -> HTML                    Diagnostic Classifier
             |                                       |
             |                              Bounded Repair Planner
             |                              Immutable Patch Workspace
             |                              Retry in sandbox (max N)
             |                                       |
             +--------------------+------------------+
                                  |
                       05  Normalization to IR
                                  |
                         Canonical PaperDocument
                         Sections / Equations
                         Figures / Tables / Refs
                                  |
                       06  Quality & Provenance
                 structure | math | bibliography | assets
                         visual | source-alignment
                                  |
                 ACCEPTED / PARTIAL / REVIEW / FALLBACK / FAILED
                                  |
                      HTML / JSON / report / logs
~~~

上游事实：[LaTeXML Architecture](https://math.nist.gov/~BMiller/LaTeXML/manual/architecture/)、
[latexmlpost](https://math.nist.gov/~BMiller/LaTeXML/manual/architecture/latexmlpost/)、
[ar5ivist](https://github.com/dginev/ar5ivist)。

从源码到产物的**函数级复现流程**见 [Reproduction Blueprint](docs/04-architecture/reproduction-blueprint.md)，
调用时序和事件见 [Sequence & State Machine](docs/07-reproduction/interface-sequence.md)。

## 三、当前状态与边界

| 项目 | 当前状态 | 说明 |
|---|---|---|
| 技术原理与外部调研 | **已有文档** | [技术文档](docs/README.md)、[参考来源](docs/REFERENCES.md) |
| README 与复现计划 | **已有设计** | 本文及 `docs/07-reproduction/` |
| `src/nano_ar5iv` 代码层次 | **M01–M04 核心模块已实现** | snapshot、root 发现、受限恢复、XML/HTML→PaperDocument；M05+ 仍占位 |
| `tests/`、`configs/`、`deployment/` | **已有单元测试** | 本地 15 通过/1 条条件跳过；GitHub CI 的独立真实 Docker/CLI 测试通过；configs/deployment 仍占位 |
| LaTeXML 转换/源码恢复/质量检查 | **M01–M04 CLI 与归一化已实现** | 引擎、恢复、版本化结构提取；科学质量门禁/API 尚未实现 |
| 官方上游手动转换演示 | **外部命令可参考** | 不等于本项目测试通过 |
| Docker 镜像、部署、性能 | **调用参数已设计/实现** | 没有提供镜像，也未实际验证运行或完成安全审计 |

**严格约束**：不擅自修改原始论文、不根据模型猜测补写科学结论；未通过公式/引用质量门禁的结果不得标记 VERIFIED；不自动连接互联网安装不可信 TeX 宏包。

## 四、如何先复现上游转换原理

以下是**上游 LaTeXML/ar5ivist 的手动实验**，不是 nano-ar5iv 自带命令。仅对你信任的本地源码运行；处理互联网来源的任意 TeX 需要先建设 [安全沙箱](docs/05-quality/security.md)。假设你有目录 `paper/`，其中主入口叫 `manuscript.tex` 而非 `main.tex`：

~~~bash
# Linux/macOS + Docker；在仅含可信论文素材的工作区执行
cd paper
mkdir -p html
docker run --rm -v "$(pwd)":/docdir -w /docdir \
  --user "$(id -u):$(id -g)" \
  latexml/ar5ivist:2512.17 \
  --source=manuscript.tex --destination=html/manuscript.html
~~~

`--source` 接受实际入口文件名，不要求叫 `main.tex`。上游文档列出的日志通常为 `manuscript.latexml.log`。命令能否运行还取决于 Docker、镜像、文件权限、网络与宏包环境。[上游命令原文](https://github.com/dginev/ar5ivist)。

为了理解转换机理，可以在**已安装 LaTeXML** 的受控环境中分别执行两阶段：

~~~bash
latexml --destination=manuscript.xml manuscript.tex
latexmlpost --format=html5 --destination=manuscript.html manuscript.xml
~~~

上游工具文档：[latexml](https://math.nist.gov/~BMiller/LaTeXML/manual/commands/latexml.html) / [latexmlpost](https://math.nist.gov/~BMiller/LaTeXML/manual/commands/latexmlpost.html)。片段恢复还可研究 `latexml --preamble=... --postamble=...`，但这不是随意修复源文件的通用保证。

**预期采集而非臆测的产物**：源码包哈希、入口选择证据、XML/HTML、图像、转换日志、引擎版本、配置、计时、公式/引用/图表计数、人工差分结论。完整可复现记录模板见 [Upstream Reproduction](docs/07-reproduction/README.md)。

### 已实现的 M01/M02 CLI（discover 不需要 Docker；convert 需要 Docker）

~~~bash
python -m pip install -e .
nano-ar5iv --output ./run-data inspect ./examples/trusted-minimal
nano-ar5iv --output ./run-data discover ./examples/trusted-minimal
# 仅可信本地源码；先手动 docker pull latexml/ar5ivist:2512.17
nano-ar5iv --output ./run-data convert ./examples/trusted-minimal --timeout 300
# 仍可显式 --entry manuscript.tex，或用 --all-roots 对多个主文档逐篇转换
~~~

输出包括 SourceBundle 哈希、显式 root、EngineAttempt、图像 ID、日志和 artifact manifest；所有结果仍标记 `quality_status=NOT_EVALUATED`。本地执行环境没有 Docker；GitHub-hosted runner 已完成**真实转换及正式 CLI 产物 SHA-256 验证**。证据：[GitHub Actions M01 real CLI verification](https://github.com/1998x-stack/nano-ar5iv/actions/runs/42189149532)。完整操作步骤与测试证据见 [M01 Baseline](docs/07-reproduction/m01-baseline.md)。

**M02 已实现**：`discover`、省略 `--entry` 自动转换唯一入口、`--all-roots`、可选 `discover --probe --top-k 2`。歧义与无效清单会拒绝自动选择。仍未实现 `evaluate`、`replay`、`.tar.gz` 归档输入和科学内容质量门禁；除 M03 两条显式启用的有限策略外，不会进行源码修复。详见 [M02 入口自动发现](docs/07-reproduction/m02-entry-discovery.md)。

### M03：保守式源码恢复（需要显式授权）

~~~bash
# 先只预览包装方案，无须 Docker
nano-ar5iv --output ./run-data recover ./examples/trusted-fragments \
  --fragments intro.tex method.tex --plan-only

# 可信本地 TeX：生成临时入口，调用预先拉取的 Docker 镜像
nano-ar5iv --output ./run-data recover ./examples/trusted-fragments \
  --fragments intro.tex method.tex --document-class article

# 主文件已知但缺失结束标记：先跑原始转换，失败后才可能限额修复
nano-ar5iv --output ./run-data recover ./paper --entry manuscript.tex
~~~

**M03 仅允许**追加缺失 `\end{document}`（需要日志与源码证据）或按明确顺序生成片段包装入口；不自动修补自定义宏包、公式或参考文献。所有成功恢复输出仍是 `RECOVERED_UNVERIFIED / quality_status=NOT_EVALUATED`。详见 [M03 Recovery](docs/07-reproduction/m03-conservative-recovery.md)。

### M04：从真实转换 run 生成结构化 PaperDocument

~~~bash
# 先对可信本地论文完成转换并保留 manifest_path
nano-ar5iv --output ./run-data convert ./examples/trusted-minimal \
  --entry manuscript.tex > ./convert-result.json

# 从返回 JSON 中取得 manifest_path，然后无需 Docker 进行归一化
nano-ar5iv --output ./run-data normalize \
  ./run-data/runs/<run-id>/manifest.json --format auto
~~~

M04 从有 SHA256 证据的 XML（优先）或 HTML（回退）提取层级节点、公式 TeX/MathML、表格单元格、图像引用及文献连边，保存到独立 `normalizations/<run_id>/<derivation_id>/paper-document.json`。原始 `sources/` 和 `runs/` 不更改。HTML 回退为有损来源，不能伪造 LaTeX 源码行号；`quality_status` **仍为 NOT_EVALUATED**。完整说明见 [M04 PaperDocument](docs/07-reproduction/m04-paper-document.md)。

## 五、九大代码 Category 与仓库结构

仓库遵循**领域模型 → 用例编排 → Ports → Adapters** 的依赖倒置。先用模块化单体与隔离转换 Worker，暂不引入分布式微服务。

~~~text
nano-ar5iv/
├── README.md
├── CONTRIBUTING.md
├── docs/                         # 技术研究、恢复、架构、复现、测试路线
├── src/
│   └── nano_ar5iv/
│       ├── domain/               # 01 文档/来源/状态/诊断/事件模型
│       ├── application/          # 02 ingest/discover/convert/recover/evaluate/replay
│       ├── source/               # 03 压缩包/manifest/TeX 扫描/依赖图
│       ├── recovery/             # 04 根因诊断/计划/包装入口/补丁
│       ├── adapters/             # 05 LaTeXML、ar5ivist、PDF、arXiv
│       ├── normalization/        # 06 XML/HTML/PDF -> PaperDocument
│       ├── quality/              # 07 结构/公式/引用/视觉/保真
│       ├── infrastructure/       # 08 沙箱/缓存/存储/任务状态
│       ├── interfaces/           # 09 CLI/API（尚未实现）
│       └── ports/                # 协议边界（无实现）
├── tests/                        # M01 单元/模拟测试 + 未来 fixture 类别占位
├── configs/                      # 配置计划占位
├── deployment/                   # Docker/运行编排占位（无镜像）
├── examples/                     # M01 自编 minimal TeX + 后续样本占位
└── scripts/                      # 未来工具占位，无可执行文件
~~~

具体到每一个占位模块的**职责、输入、输出、失败行为、后继阶段**，参见 [模块清单](docs/04-architecture/module-catalog.md) 与 [文件分层规范](docs/04-architecture/code-categories.md)。

## 六、核心逻辑与恢复状态机

**入口发现：** `00README.json` / legacy metadata → 静态图构建 → 唯一根优先 → 多根集合 / 候选排序 → 受控试转换 → 记录置信度及歧义。动态 `\\input` 不可静态推断时应返回 `unknown`，不能冒充成功。

**诊断与修复：** 基线转换 → 按根因分类首个有效错误 → 在拷贝中生成有限修复方案（路径 / 包装入口 / 兼容包）→ 白名单校验 → 受限重试 → 比较结果 → 超预算则停止。禁止丢弃不认识的数学宏、公式与文献。

**质量验证：** 解析有效性、章节结构、公式数和符号、图表资源、bib/cite 关系、可能的 PDF 交叉验证、未知项显式上报。转换进程退出码为 0 **不代表论文内容保真**。

~~~text
QUEUED -> INGESTING -> ANALYZING -> CONVERTING
                                  |           |
                                  |           +-> RECOVERY_PLANNED
                                  |                    |
                                  |              PATCH_SANDBOX
                                  |                    |
                                  |              CONVERTING (bounded)
                                  |
                                  +-> NORMALIZING -> EVALUATING
                                                       |
                     +---------------+-----------------+-------------+
                     |               |                 |             |
                  ACCEPTED        PARTIAL        REVIEW_REQUIRED  REJECTED
                                                 (PDF fallback tracked)
~~~

严格的输入、输出、错误枚举、状态转换参见 [函数级蓝图](docs/04-architecture/reproduction-blueprint.md) 与 [时序图](docs/07-reproduction/interface-sequence.md)。

## 七、设计中的接口与产物

输入：`SourceBundle` / `EntryDecision` / `ConversionRequest`。输出：`EngineAttempt` / `RecoveryPlan` / `PaperDocument` / `QualityReport` / `ArtifactManifest`。

建议 `PaperDocument` 保留 `nodes`、`equations`（原 TeX + MathML）、`tables`、`assets`、`citations`、`relations`、`source_spans`、`provenance` 和 `warnings`。**内容 ID 与引用不允许在修复中被静默篡改**。

~~~text
out/<job_id>/
  manifest.json                 # 输入hash、工具版本、配置和 artifact hash
  inventory.json                # 源文件及作用
  entry-decision.json           # root、候选及证据
  attempts/<n>/                 # 每次引擎调用的日志/XML/HTML
  repair-plan.json              # 修复说明与差异
  paper-document.json           # Canonical IR
  quality-report.json           # 维度结果及拒收理由
  html/                         # 可信/降级产物（依策略发布）
~~~

上述为**规划产物目录**，并未实际生成。示例 Schema 见 [Data Contracts](docs/04-architecture/data-contracts.md)。

## 八、测试、指标与安全

**验证不能只看 conversion rate**：同时跟踪入口定位准确率、公式符号保留率、引用连通率、资产完整率、修复的净收益、错误接受率、CPU/内存/超时和恢复可追溯性。

测试层次：`unit`、`contract`、`integration`、`e2e`、`security`、`performance`；真实 arXiv 论文须记录 ID、版本、许可和独立判断。M01 有 16 个 unittest：本地/普通 CI 15 通过、1 个真实 Docker 测试条件跳过；独立 GitHub CI 已运行并通过该真实测试及正式 CLI artifact hash E2E。**科学内容保真仍未验收**，后续 M02–M07 黄金集仍为占位。

TeX 包、图片、档案和输出 HTML 均视为**不可信输入**。未来执行层必须提供 archive path traversal 保护、no-network、无宿主凭据挂载、非 root、禁用 shell escape、CPU/内存/时间限额、HTML/SVG 隔离呈现；官方演示命令不等于生产隔离配置。

详见：[质量评估](docs/05-quality/evaluation.md)、[安全模型](docs/05-quality/security.md)、[测试策略](docs/05-quality/test-strategy.md)、[实验矩阵](docs/07-reproduction/experiment-matrix.md)。

## 九、完整文档导航

| 专题 | 文档 |
|---|---|
| ar5iv 工作原理 | [ar5iv overview](docs/01-foundations/ar5iv-overview.md) |
| LaTeXML 编译与后处理 | [latexml pipeline](docs/01-foundations/latexml-pipeline.md) |
| MathML/引用/图表 | [semantic elements](docs/01-foundations/semantic-elements.md) |
| 无 main.tex 如何找入口 | [entry discovery](docs/02-source-recovery/entry-discovery.md) |
| 宏包/源码损坏如何修复 | [recovery playbook](docs/02-source-recovery/recovery-playbook.md) |
| 官方资料、论文与社区评论 | [landscape](docs/03-research/landscape.md) / [issues](docs/03-research/issue-analysis.md) |
| 总架构 | [system architecture](docs/04-architecture/system-architecture.md) |
| **M04 结构化论文 IR 与来源审计** | [M04 PaperDocument](docs/07-reproduction/m04-paper-document.md) |
| **M03 可审计修复与一次重试** | [M03 Conservative Recovery](docs/07-reproduction/m03-conservative-recovery.md) |
| **M02 主文件自动发现、依赖图与测试** | [M02 entry discovery](docs/07-reproduction/m02-entry-discovery.md) |
| **M01 实现与测试证据** | [M01 baseline](docs/07-reproduction/m01-baseline.md) |
| **端到端函数级复现蓝图** | [reproduction blueprint](docs/04-architecture/reproduction-blueprint.md) |
| **实际占位文件目录与模块契约** | [module catalog](docs/04-architecture/module-catalog.md) |
| Category 与依赖规则 | [code categories](docs/04-architecture/code-categories.md) |
| JSON/领域数据契约 | [data contracts](docs/04-architecture/data-contracts.md) |
| ADR | [architecture decisions](docs/04-architecture/decisions.md) |
| **上游最小复现实验** | [upstream reproduction](docs/07-reproduction/README.md) |
| **转换时序 / API / 状态机** | [sequence](docs/07-reproduction/interface-sequence.md) |
| **测试用例、对照评估** | [experiment matrix](docs/07-reproduction/experiment-matrix.md) |
| **故障诊断流程** | [failure triage](docs/07-reproduction/failure-triage.md) |
| **逐文件实施顺序** | [implementation slices](docs/07-reproduction/implementation-slices.md) |
| M00-M07 路线图 | [roadmap](docs/06-planning/roadmap.md) |
| 研究来源全集 | [references](docs/REFERENCES.md) |

## 十、阶段路线图

| 阶段 | 目标 | 当前状态 |
|---|---|---|
| M00 | 技术研究、代码体系和真实占位结构 | 已提交 PR #2、尚待合并 |
| M01 | 源码快照、CLI、固定镜像适配、provenance | **M01 基线与真实 Docker/CLI 端到端验收通过；科学保真不在 M01 范围** |
| M02 | 元数据优先的 root 发现、依赖图与多入口 CLI | **自编样本真实 Docker 自动入口与 Python 3.11/3.13 CI 已通过；大规模准确率待评测** |
| M03 | 显式片段包装、结束标记补全、错误归类和不可变修复审计 | **已合并 main，真实最小转换验收通过** |
| M04 | 原生 XML / HTML→PaperDocument、公式/表格/引用、稳定 ID 和派生校验 | **M04.1 PR #10 已实现，自动化测试验收中；PDF-only fallback 未实现** |
| M05 | 公式/引用/图表的质量门禁 | 仅设计 |
| M06 | 队列、缓存、API、UI、部署 | 仅设计 |
| M07 | 可选、受控 LLM 辅助和科研 RAG | 仅设计 |

详见 [roadmap](docs/06-planning/roadmap.md)。阶段验收必须有实际运行证据，不能把占位模块当作已完成代码。

## 十一、贡献与参考

[CONTRIBUTING.md](CONTRIBUTING.md) 约定逐阶段小 PR、复现证据、科学事实保护、版权许可和可回滚要求。项目尚未选定仓库整体开源许可证；不要把上游 MIT 许可证默认延伸到本项目或论文源文件。

主要上游：[LaTeXML](https://github.com/brucemiller/LaTeXML) · [ar5iv](https://github.com/dginev/ar5iv) · [ar5ivist](https://github.com/dginev/ar5ivist) · [arXiv 00README](https://github.com/arXiv/arxiv-docs/blob/develop/source/help/00README.md)。问题研究见 [REFERENCES.md](docs/REFERENCES.md)。
