# 08｜nano-ar5iv 系统架构（设计稿）

## 分层架构 [D]

~~~text
[CLI / HTTP API / batch import]   (planned)
          ↓
[Application: Job Orchestrator + State Machine]
          ↓
[Source Plane: Archive / Inventory / Metadata / Entry / Dependency]
          ↓
[Recovery Plane: Diagnostics / Repair Planner / Immutable Workspace]
          ↓
[Engine Adapters: LaTeXML/ar5ivist | Future Alternative | PDF fallback]
          ↓
[Normalization Plane: XML/HTML/PDF → PaperDocument + Provenance]
          ↓
[Quality Plane: Structure / Mathematics / Citations / Assets / Visual]
          ↓
[Artifacts: HTML+MathML, Document JSON, Repair Diff, Report]
          ↓
[Storage / Task Queue / Web Viewer]   (future phases)
~~~

### 优先采用模块化单体 + 隔离 worker

原型期用一个 Python package 管理领域对象与任务编排，TeX 转换在独立沙箱进程/容器。只有压测证明队列和吞吐问题后，才拆分独立 service。避免过早引入 Kafka、Kubernetes、分布式多语言微服务。未来 Rust 可以用于高性能扫描/图解析，但先以接口定义隔离实现。

## 两条关键控制链

**Recovery loop**：先基线转换；基于首个有效错误聚类选择有限策略；执行可审计补丁；同配置再跑；超过最大轮数或质量变差则中止并保存最佳已验证结果。

**Quality loop**：结构合法性→字段存在性→源/目标计数→引文连通性→数学符号校验→浏览器/PDF 视觉验证（可用时）→最终接收级别。两条链都用明确状态机而非“模型评审通过”判断。

## 核心边界

- **Domain**：纯数据对象、状态与不变式，不依赖 LaTeXML 或 HTTP。
- **Application**：用例、状态跃迁、策略组合，不执行 shell。
- **Adapters**：外部工具运行、解析日志、PDF、GitHub/arXiv 等数据来源。
- **Infrastructure**：工作区、缓存、队列、对象存储、sandbox。
- **Interfaces**：CLI/API/UI 只将请求映射为 application commands。

## 数据与任务主键

`source_fingerprint = SHA256(archive bytes)`；`job_key = H(source_fingerprint, selected_roots, normalized_config, engine_version, recovery_version, schema_version)`。注意 JSON 配置排序、路径规范化和版本强制入键，防止同论文不同版本共用缓存。

## 任务生命周期

`QUEUED → INGESTING → ANALYZING → CONVERTING → (RECOVERING → CONVERTING)* → NORMALIZING → EVALUATING → {SUCCEEDED, DEGRADED, REVIEW_REQUIRED, FAILED, CANCELLED}`。每次 attempt 有自己的日志、产物和状态，worker 崩溃后只从可核实 checkpoint 恢复。

## 可观测性

每个任务必须有 trace_id、source hash、root path、attempt_no、engine image digest、elapsed、peak memory、diagnostic counts、quality report、artifact hashes；运维指标分开统计 `output_created_rate` 与 `content_verified_rate`。

## 非目标

不在 v0.1 训练 TeX 语法模型；不设计联网任意宏包下载；不实现论文内容自动补写；不直接公开未经许可的大规模整库。
