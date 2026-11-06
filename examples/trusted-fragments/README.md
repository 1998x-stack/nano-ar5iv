# Minimal self-authored M03 fragment fixtures

These three fragments deliberately have **no** document class or document environment. They are used to demonstrate the **explicit** recovery wrapper, not to simulate a corrupted paper recovered automatically. No third-party paper content or PDF files are included.

Example (does not require Docker):
~~~bash
nano-ar5iv --output ./run-data recover ./examples/trusted-fragments --fragments intro.tex method.tex --preamble macros.tex --plan-only
~~~

To execute against a locally pre-pulled image in a trusted environment, remove \`--plan-only\`. See [M03 recovery](../../docs/07-reproduction/m03-conservative-recovery.md).

An HTML file produced by this example remains \`quality_status=NOT_EVALUATED\`.
