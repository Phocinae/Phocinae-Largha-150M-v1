# PII 扫描报告

- 扫描对象：`test_typed_400.jsonl`（400 行全部文本内容，覆盖 state / questions / criteria / options / factors 全部字段）
- 扫描时间：2026-10-08
- 扫描方式：正则模式逐行全量匹配；命中文案按「保留首尾字符 / 末 4 位」规则脱敏展示
- 判定结论：**真实可识别个人信息（PII）命中 0 处**。全部命中均为合成占位符或正则误报，证据如下。

## 各模式命中数与判定

| 模式 | 命中数 | 判定 |
|---|---|---|
| email 邮箱 | 21 | 合成占位符（域名全部为 example.com / corp.com / contoso.com / acme.com / betaindustries.com / mybiz.com 等占位域名） |
| phone 电话 | 352 | **正则误报**——全部为 `INV-2026-XXXX` 发票编号及同族 2026-XXXX 单据编号；无括号区号/国际区号等真实电话形态（0 处） |
| ssn 社保号 | 0 | 无命中 |
| card16 卡号（13–19 位数字串） | 0 | 无命中 |
| iban 银行账号 | 0 | 无命中 |
| name_honorific 姓名（Mr./Ms./Dr. 等） | 0 | 无命中 |
| name_field 姓名字段（customer name: …） | 0 | 无命中 |
| acct_keyword 账号关键词 | 0 | 无命中 |
| ip_addr IP 地址 | 87 | 合成/技术地址——RFC 5737 文档段（203.0.113.x / 198.51.100.x / 192.0.2.x）、RFC 1918 私网段（10.x / 172.16.x / 192.168.x）与 0.0.0.0；另有 5 个公网地址（185.199.108.133、185.53.177.10 等，合成场景数据，无归属/身份关联） |

## 脱敏样例（按模式）

### email（21 处，全部占位域名）
- `customer_service_000004` → `j***e@example.com`
- `customer_service_000022` → `m***t@example.com`
- `customer_service_000025` → `b***g@acme.com`

### phone（352 处，全部发票/单据编号误报）
- `invoice_processing_000000` → `INV-2026-2424`（原文即含 `INV-` 前缀，非电话号码）
- `invoice_processing_000000` → `INV-2026-9279`
- `customer_service_000001` → `A-30926`（订单号）

### ip_addr（87 处，文档/私网段为主，含 5 个合成公网地址）
- `security_incidents_000000` → `203.0.113.45`（RFC 5737 文档段）
- `security_incidents_000001` → `198.51.100.22`（RFC 5737 文档段）
- `security_incidents_000002` → `10.0.5.12`（RFC 1918 私网段）

## 结论

- 本行集为上游 LocalLLaMA/typed-decisions 的合成决策场景数据，不含真实姓名、电话、邮箱、卡号或账号信息。
- 电话类命中为「2026-XXXX」编号串与电话号码正则的形态碰撞（年份前缀单据编号），并非电话号码。
- 邮箱类命中全部落在 RFC 2606 保留域与常见占位域名上，属作者有意使用的合成占位符。
- 发布无需额外脱敏处理；本报告随包保留供审计。
