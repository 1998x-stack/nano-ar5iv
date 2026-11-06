# Contributing / 开发约定（架构占位阶段）

当前仅接受研究、文档、目录结构、数据契约与经明确批准的阶段实现；提交 PR 时标记范围为 `docs` / `scaffold` / `feat` / `fix` / `security`。本阶段禁止把占位文件当成可运行模块宣传。

## PR 清单

1. 说明问题、范围、哪些模块未实现。
2. 外部事实给一手链接，用户反馈标注「报告/更正/已复现」。
3. 任何新实现都给最小可复现输入、expected、observed、工具/镜像版本、哈希与测试结果。
4. 不覆盖原始 TeX；修改必须有原始位置、hash、独立修复副本和可回滚 patch。
5. 不把模型自评、process exit=0、生成 HTML 直接等同于科学保真。
6. 不向仓库直接提交未授权论文全文/附图、可识别私人数据、许可证不明依赖、真实密钥。
7. 所有 `src/` 下的占位 Python 文件只写模块用途和 TODO；本轮不得添加可执行实现、CLI 脚本或启动/部署流水线。
8. 安全风险前置：压缩包解压、TeX 执行、SVG/HTML 渲染、外部资源下载必须先完成 threat model 评审。

## 架构演进约束

`domain` 不依赖 adapters；`application` 仅通过 `ports` 调用外部功能；`adapters`/`infrastructure` 实现 Ports；`interfaces` 不执行业务规则。保持清晰的错误族、来源版本、质量判定、可追溯性。

## 规划中的开发过程

每个 M01–M07 PR 包含具体模块清单、该阶段 fixture、验收指标和失败边界。未完成验证要写 `NOT_RUN`，不可写“测试全绿”。

文档入口：[README](README.md) / [复现实施切片](docs/07-reproduction/implementation-slices.md) / [质量策略](docs/05-quality/test-strategy.md)。
