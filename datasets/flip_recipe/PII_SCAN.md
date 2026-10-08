# PII 扫描说明（flip_recipe）

本包 `flip_rows_subset.jsonl` 与 `typed_test` 包行件同源（上游 typed-decisions test 集，
逐字段 0 差异，仅增映射字段），PII 结论一致：**未检出真实个人可识别信息**。

- 邮箱：全部为 example.com / corp.com / contoso.com 等占位域名（0 真实邮箱）
- 电话形命中：全部为 `INV-2026-XXXX` 发票单号（0 真实号码）
- IP：文档段（RFC 5737 / RFC 1918）为主，另含 5 个公网地址（合成场景数据，无归属/身份关联）
- 手机号 / 身份证 / 银行卡：0 命中

详扫描记录见 `../typed_test/PII_SCAN.md`。
