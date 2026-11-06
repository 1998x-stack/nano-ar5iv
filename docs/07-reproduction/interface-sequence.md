# 运行时序、状态机和接口设计（尚未实现）

## 一、主流程时序（Mermaid 设计图）

~~~mermaid
sequenceDiagram
    participant U as User/CLI
    participant A as Application
    participant S as Source+Manifest
    participant E as Engine Adapter
    participant R as Recovery
    participant N as Normalizer
    participant Q as Quality
    participant O as Artifact Store
    U->>A: request (source, policy)
    A->>S: snapshot + inventory + discover roots
    S-->>A: SourceBundle + EntryDecision
    alt unique roots / DocumentSet
        loop each selected root
            A->>E: baseline convert (sandbox, limits)
            E-->>A: EngineAttempt / logs
            opt failed and budget permits
                A->>R: root cause + repair proposal
                R-->>A: immutable RecoveryPlan
                A->>E: retry changed working copy
                E-->>A: EngineAttempt (new)
            end
            A->>N: normalize selected attempt
            N-->>A: PaperDocument
            A->>Q: multi-dimensional validation
            Q-->>A: QualityReport
        end
    else no reliable root
        A-->>U: REVIEW_REQUIRED + evidence
    end
    A->>O: persist artifact hashes + manifest
    O-->>A: artifact IDs
    A-->>U: JobResult
~~~

## 二、任务状态

~~~mermaid
stateDiagram-v2
    [*] --> QUEUED
    QUEUED --> INGESTING
    INGESTING --> ANALYZING
    ANALYZING --> CONVERTING: unique root(s)
    ANALYZING --> REVIEW_REQUIRED: ambiguous
    CONVERTING --> RECOVERING: recoverable failure
    RECOVERING --> CONVERTING: safe patch, budget remains
    CONVERTING --> NORMALIZING: usable attempt
    NORMALIZING --> EVALUATING
    EVALUATING --> SUCCEEDED: quality gates pass
    EVALUATING --> DEGRADED: partial or fallback
    EVALUATING --> REVIEW_REQUIRED: unknown critical fidelity
    INGESTING --> FAILED: unsafe archive
    CONVERTING --> FAILED: no recoverable artifact
    RECOVERING --> FAILED: policy exhausted
    SUCCEEDED --> [*]
    DEGRADED --> [*]
    REVIEW_REQUIRED --> [*]
    FAILED --> [*]
~~~

状态图是拟议行为。`QualityReport.decision` 与 `Job.state` 独立：`SUCCEEDED` 只有在质量门禁满足后才可分配。

## 三、未来接口抽象（API 草案，不可调用）

| 方法 | 请求 | 响应 | 常见失败 |
|---|---|---|---|
| `POST /v1/jobs` | SourceReference, ConversionPolicy | job_id / QUEUED | unsafe_input / unsupported |
| `GET /v1/jobs/{id}` | job_id | state, attempts, timestamps | not_found |
| `GET /v1/jobs/{id}/result` | job_id | PaperDocument + QualityReport | not_ready |
| `GET /v1/jobs/{id}/artifacts` | job_id | manifest and scoped links | authorization |
| `POST /v1/jobs/{id}/replay` | job_id | new job reference | incompatible_version |
| `POST /v1/jobs/{id}/cancel` | job_id | cancellation state | already_terminal |

**仅定义路径意图**，未实现 HTTP 层、授权与部署。不同实体间请求必须经身份、权限和数据保留审查。

## 四、状态转换约束

- `QUEUED→INGESTING`：输入被引用，不意味着已安全解压。
- `INGESTING→ANALYZING`：archive safe checks + source snapshot 已记录。
- `ANALYZING→CONVERTING`：至少一个安全相对 root 及选择证据。
- `CONVERTING→RECOVERING`：失败类别有匹配白名单策略且预算未超。
- `RECOVERING→CONVERTING`：copy-on-write patch 已审核；attempt 序号递增。
- `EVALUATING→SUCCEEDED`：必需维度非 unknown/not-run 且 hard gate 全部 PASS。
- `SUCCEEDED/FAILED/REVIEW_REQUIRED` 终态不可隐式回退；`replay` 产生新 job 但关联 parent job id。

## 五、事件模型草案

`ArchiveAccepted`、`EntryResolved`、`EntryAmbiguous`、`ConversionStarted`、`ConversionFailed`、`RepairProposed`、`RepairRejected`、`RetryScheduled`、`DocumentNormalized`、`QualityAssessed`、`ArtifactPersisted`。每个事件保留 job_id、attempt_no、time、source_hash、policy_version、reason_code。

## 六、幂等和回放

相同输入和显式参数的 `job_key` 必须包括源码哈希、root 集合、配置标准化哈希、引擎镜像 digest、修复策略版本、IR schema 版本。缓存命中不得跳过新版本质量门禁要求；修复采用新的 attempt 工作目录，不能覆盖旧 XML/HTML。

接口详解：[数据契约](../04-architecture/data-contracts.md) / [完整蓝图](../04-architecture/reproduction-blueprint.md)。
