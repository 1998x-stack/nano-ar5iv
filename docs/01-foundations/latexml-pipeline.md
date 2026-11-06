# 02｜LaTeXML 内核：从 TeX 到 XML

## 核心编译链 [F]

LaTeXML 不是把 PDF 转 HTML 的 OCR 工具，而是模拟关键 TeX 执行语义并生成 XML DOM。官方文档的五个阶段：**Digestion → Construction → Rewriting → Math Parsing → Serialization**。

- **Mouth**：依据 catcode 将字符流切成 TeX Token。
- **Gullet**：宏展开、读取参数、解析部分基础数据类型；状态里存放控制序列定义与作用域。
- **Stomach**：执行 primitive / constructor，把展开结果转为 Box / Whatsit 等。
- **Construction**：将 Box / Whatsit 插入结构化 XML DOM；依据文档模型处理结构约束。
- **Rewriting**：重写某些 token 及数学信息。
- **Math Parsing**：尽量为公式建立表达式结构，但不保证消除所有语义歧义。
- **Serialization**：输出 XML。

来源：[官方 `3.1](https://math.nist.gov/~BMiller/LaTeXML/manual/architecture/latexml/)、[数学解析章节](https://math.nist.gov/~BMiller/LaTeXML/manual/math/details/)。

## 后处理链 [F]

`latexmlpost` 常用过滤阶段包括 Split、Scan（标签与交叉引用）、MakeIndex、MakeBibliography、CrossRef、MathML/图像转换、图形处理、XSLT、Writer。具体排序与运行组合依赖选项，不能把单一管线硬编码为所有版本的唯一形式。[官方 `3.2](https://math.nist.gov/~BMiller/LaTeXML/manual/architecture/latexmlpost/)

~~~text
TeX Source
   ├── macro bindings (.sty/.cls compatible bindings)
   ├── semantic XML
   └── diagnostics (severity/category/object/location)
              ↓
LaTeXML XML → labels + bibliography → MathML + Graphics → HTML5
~~~

## 自定义宏包的本质

LaTeXML 使用 *bindings* 将 TeX 包/控制序列映射成更合理的 XML 结构。缺少 binding 可能是“引擎不懂原文”，不意味着作者写错。不要用空宏简单吞掉未知命令：命令可能包含定理、符号或科学数据。[官方自定义说明](https://math.nist.gov/~BMiller/LaTeXML/manual/customization/)

## 失败分析

日志的 `Warn/Error/Fatal` 属于转换器视角。官方手册特别提醒：错误既可能源于源文件，也可能源于 LaTeXML 的理解能力。需要记录 *first meaningful failure*，防止“一个未知类导致 100 个后续错误”被误分为 100 个根因。[错误码](https://math.nist.gov/~BMiller/LaTeXML/manual/errorcodes/index.html)

## 版本能力及未来兼容

官方主线（Perl LaTeXML）与实验性的 Rust 生态（如 `latexml-oxide`、`docs.rs/latexml`）应当通过独立 Adapter 管理。Rust 的 `main_tex` 模块已提供目录入口启发式；这是可参考的现有能力，不等于二者具有完全一致的宏包/质量支持。[main_tex API](https://docs.rs/latexml/latest/latexml/main_tex/index.html)

## nano-ar5iv 设计推导 [D]

- 源文件分析不得与 LaTeXML 内核互相污染。
- 记录 `engine_name/version/container_digest`，并将版本包含在缓存键。
- 输出 XML 视为转换中间产物，不能代替经过验证的 PaperDocument。
- 解析错误不自动触发“编造缺失正文”的 LLM 生成。
