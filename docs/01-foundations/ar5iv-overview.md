# 01｜ar5iv 背后的核心逻辑

## 1. 四套系统的职责边界

`ar5iv`（dginev/ar5iv）主要是**HTML 论文展示 Web 服务**；`LaTeXML` 负责将 TeX 文本/宏展开与文档结构解释为 XML；`latexmlpost` 对 XML 做参考文献、交叉引用、数学和图形处理；`ar5ivist` 负责将本地 LaTeX 源码方便地转换成 ar5iv 风格 HTML。`ar5iv-css` 提供网页样式。不要误把 ar5iv Web 仓库当作 TeX 编译器。 [F]

参考：[ar5iv 仓库](https://github.com/dginev/ar5iv)、[LaTeXML 架构](https://math.nist.gov/~BMiller/LaTeXML/manual/architecture/)、[ar5ivist](https://github.com/dginev/ar5ivist)。

## 2. 信息流

~~~text
arXiv 源文件 / TeX bundle
    ↓ 安全解压、选择入口
TeX + .sty/.cls + .bib + figures
    ↓ LaTeXML：宏展开、digest、DOM、数学解析
LaTeXML XML（结构/标签/定位线索）
    ↓ latexmlpost：索引、书目、交叉引用、Graphics、MathML、XSLT
HTML5 + MathML + SVG/图片 + CSS
    ↓ 发布、缓存、网页路由
浏览器阅读
~~~

**关键区别：不是“先生成 PDF 再 OCR”。** LaTeXML 可以直接利用源码里的结构控制序列；PDF 解析主要从版面恢复逻辑关系。前者优势是章、公式、标签、引用的结构显式；限制是 TeX 语言可编程、宏包生态大、源码不一定可恢复。[F]

## 3. 为什么不能简单 `regex.tex → html`

TeX 具有 catcode、宏定义和展开、模式切换、作用域、包选项、条件分支、自定义类、动态文件名及图形宏。因此 `\\section` 并非任何上下文里都能直接替换为 `<h2>`；一个类文件的选项还能间接加载数学宏包。这种非局部依赖在 [ar5iv issue #437](https://github.com/dginev/ar5iv/issues/437) 中出现过。[F]

## 4. 转换成功的三个不同概念

- **可用性（availability）**：存在有效 HTML 输出。
- **结构正确性（structural validity）**：文档树合法，标题/公式/引用可引用。
- **内容保真（fidelity）**：科学论述、符号、图表、文献没有实质遗漏或变形。

在 2024 ar5iv 数据集中，`no_problem / warning / error` 被分开统计，不能据此把所有有 HTML 的论文视作无损。数据是历史快照，不能代表当前转换覆盖率。[F] [数据集](https://sigmathling.kwarc.info/resources/ar5iv-dataset-2024/)

## 5. nano-ar5iv 的差异化定位 [D]

只在转换器外围实现 **Source Recovery Plane + Quality Plane**：入口发现、源码快照、依赖图、可审计修复、转换适配、统一 PaperDocument、质量门禁与降级策略。首阶段**不重写 TeX 引擎**、不承诺与官方网页 CSS 完全等价、不把 LLM 当作编译器。

## 6. 边界与开源注意事项

arXiv 官方 HTML 和 ar5iv Lab 不应混为同一服务；应分别记录来源 URL、论文版本、转换引擎和更新时间。大批量 ar5iv 2024 数据集有独立的许可申请要求，不能因为能下载网页就认定可以再分发整库。[数据发布页](https://sigmathling.kwarc.info/resources/ar5iv-dataset-2024/)
