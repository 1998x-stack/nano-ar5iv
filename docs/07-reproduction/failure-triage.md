# 故障排查手册：从第一条证据出发（M03.1 首因分类已实现）

M03.1 已实现 CLI diagnose：统计首条 Error/Fatal 与后续级联错误并按类别给出启发式判定，但不保证找到真正根因；详见 [M03 implementation](m03-recovery.md)。

## 诊断顺序

1. **输入层**：归档是否正确、路径/编码/大小限制、是否包含 TeX、是否存在 `00README`。
2. **入口层**：`root` 是否在清单中，是否被其他文件包含，多个 root 是否其实是正文/附录。
3. **执行层**：镜像 digest、运行目录、参数、输出权限、退出码、elapsed、OOM/timeout。
4. **首次有效错误**：按照时间位置定位根因而非追逐尾部 100+ 个级联 Error。
5. **内容层**：XML 是否含章节/公式；HTML/MathML 是否有符号缺失，bib links 是否正确。
6. **输出层**：相对资源引用是否可达，浏览器样式是否遮挡图表，是否数据存在却无法发现。
7. **结论层**：修复、降级、review、reject 四条路径；记录每个未验证项。

## 典型故障树（设计规则）

| 现象 | 可能根因（尚需证据） | 下一步 |
|---|---|---|
| no top-level | metadata 缺/错误、被包含、动态宏 | manifest→图→候选试转换 |
| `Undefined control sequence` | 缺 binding、作者源码错、包选项未生效 | 查首个定义点与 .sty/.cls |
| hundreds of errors | 早期类文件/包依赖异常 | 先聚合首因，避免逐条 LLM 修 |
| PDF 正常，HTML 数学丢符号 | font/MathML/binding 兼容 | 数学符号级比对并标 failure |
| bib 部分空/错 | .bib/.bbl、cite map、后处理 | 原始 Bib 与 CrossRef 检查 |
| 图表重叠 | CSS 或转换后布局 | 数据内容与视觉分别核验 |
| conversion timeout | 资源配额、递归宏、复杂图形 | 禁无界重试 |
| usable HTML but untrusted math | 内容不可验证 | PARTIAL/REVIEW_REQUIRED |

## 带根因信息的社区例子

- [ar5iv #437](https://github.com/dginev/ar5iv/issues/437)：未知 class/`\\ExecuteOptions` 引发数学包关联问题。
- [ar5iv #477](https://github.com/dginev/ar5iv/issues/477)：宏包兼容导致错误级联/超时。
- [arXiv HTML #7007](https://github.com/arXiv/html_feedback/issues/7007)：mathdesign 希腊符号的保真报告。
- [arXiv HTML #6544](https://github.com/arXiv/html_feedback/issues/6544)：原目录“缺失”报告被用户自行修正，属于可发现性问题，避免误分类。

所有案例都只是外部报告和选定技术调查样本；实现时要保留论文版本并独立复现。

## 修复停止条件

无可信 root、补丁来源不明、会改变科学主张、连续质量下降、配额耗尽、缺核心符号验证、权限/安全限制触发：立即停止自动修复，导出 diagnosis 和 review request。质量不确定时不宣布“已解决”。

关联：[recovery playbook](../02-source-recovery/recovery-playbook.md) / [quality evaluation](../05-quality/evaluation.md)。
