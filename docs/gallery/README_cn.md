# 场景演示动画（27 个：S01–S24 场景 + G25–G27 对照与可靠性）

斑海豹（Phocinae-Largha-150M-v1）的典型应用场景演示，全部为合成演示数据、逐帧渲染，数字与模型卡 [BENCHMARKS.md](../../BENCHMARKS.md) 一致。每张 GIF 首帧为结论卡，尾帧为一句总结。编号说明：**S = 应用场景，G = 对照与可靠性**。[English version](./README.md)

## 代表场景

<details>
<summary>▶ 精选演示（6 张，点击展开）</summary>

<div align="center">
  <img src="./S06_escalate_savings.gif" width="640"/>
  <p>大模型调用 −55.0%（τ=0.5 档 79.6%），准确率反而 0.906→0.9936 (kept subset)</p>
  <img src="./S01_rmrf_gate.gif" width="640"/>
  <p>命令审批门：rm -rf 毫秒级拦截（21.0ms（RTX 5090））</p>
  <img src="./S07_tool_routing.gif" width="640"/>
  <p>工具路由：工具选择 12/12</p>
  <img src="./S24_quickstart.gif" width="640"/>
  <p>三行跑起来：pip install → 启动 → 一次判定</p>
  <img src="./S23_bilingual.gif" width="640"/>
  <p>双语决策：typed acc en 0.906 / zh 0.848</p>
  <img src="./S13_event_triage.gif" width="640"/>
  <p>实时事件分级：30fps 帧门内逐帧判定</p>
</div>

</details>

## 全部场景索引

### 审批安全

| 场景 | 文件 | 一句话 |
|---|---|---|
| 危险命令拦截 | [S01_rmrf_gate.gif](./S01_rmrf_gate.gif) | `rm -rf` 被 21.0ms（RTX 5090） 内拦下，p(deny)=0.96 |
| 管道命令拦截 | [S02_curl_pipe_gate.gif](./S02_curl_pipe_gate.gif) | `curl \| bash` p(allow)=0.21 → 拒绝 |
| 批量权限变更 | [S03_chmod_batch.gif](./S03_chmod_batch.gif) | 8 条命令逐条三态判定：6 放行 / 1 转人工 / 1 拦截 |
| 三态门阈值 | [S04_tristate_gate.gif](./S04_tristate_gate.gif) | 阈值 0.30/0.65：git push 0.91 放行、sudo restart 0.44 转人工、rm -rf /etc 0.05 拦截 |
| 回放审计电池 | [S05_replay_battery.gif](./S05_replay_battery.gif) | 17 条回放审计：误放行 0、误拒 2 |

### 路由与省费

| 场景 | 文件 | 一句话 |
|---|---|---|
| 升级门省费 | [S06_escalate_savings.gif](./S06_escalate_savings.gif) | τ=0.6 升级门：大模型调用 −55.0%（τ=0.5 档 79.6%），acc 0.906→0.9936 (kept subset) |
| 工具路由 | [S07_tool_routing.gif](./S07_tool_routing.gif) | 单次前向选对工具，工具选择 12/12 |
| 中文域零外呼 | [S08_zh_zero_escalate.gif](./S08_zh_zero_escalate.gif) | 中文判定本地完成，斑海豹 .855 vs Kimi K3 .72 |
| 上下文粗筛 | [S09_context_screen.gif](./S09_context_screen.gif) | 30 个上下文块本地筛掉 11 个，CPU 批 8–20 决策/s |
| 模型路由 | [S10_model_routing.gif](./S10_model_routing.gif) | 简单决策本地 21.0ms（RTX 5090），复杂决策升级大模型 |

### 实时与趣味

| 场景 | 文件 | 一句话 |
|---|---|---|
| 微批吞吐 | [S11_microbatch_60fps.gif](./S11_microbatch_60fps.gif) | 微批 4 摊销后 7.0ms/决策，跑进 60fps 帧预算 |
| 贪吃蛇 | [S12_snake.gif](./S12_snake.gif) | 144M 参数的「蛇脑」21.0ms（RTX 5090）/步玩贪吃蛇 |
| 事件分级 | [S13_event_triage.gif](./S13_event_triage.gif) | 监控事件逐帧定级，P(3)=0.81 红闪告警 |

### 办公与文档

| 场景 | 文件 | 一句话 |
|---|---|---|
| 文档分类 | [S14_doc_triage.gif](./S14_doc_triage.gif) | 8 个文件本地贴标，零上云零 token |
| 报销预判 | [S15_expense_preapprove.gif](./S15_expense_preapprove.gif) | 无发票报销 p(approve)=0.07 直接拒，灰带才转人工 |
| 技能路由 | [S16_skill_routing.gif](./S16_skill_routing.gif) | 一句话选对技能，p=0.94 |
| 质量门 | [S17_quality_gate.gif](./S17_quality_gate.gif) | 周报草稿 p(需重写)=0.61 黄标打回——廉价初筛，不做终审 |
| 发票校验 | [S18_invoice_verify.gif](./S18_invoice_verify.gif) | 金额×税率与税额逐分核对，p(一致)=0.95 |

### 流程与工程

| 场景 | 文件 | 一句话 |
|---|---|---|
| 步骤校验 | [S19_step_verify.gif](./S19_step_verify.gif) | HTTP 500 vs 期望 200：p(pass)=0.04 停链，防级联错误 |
| 输出初筛 | [S20_output_screen.gif](./S20_output_screen.gif) | 输出第一道粗筛，省主模型 token（选择力弱于大模型，如实说明） |
| 内容三级门 | [S21_content_gate.gif](./S21_content_gate.gif) | 放行/复核/拦截三级，灰带转人工，不当唯一守门员 |
| 选项洗牌稳健 | [S22_flip_invariance.gif](./S22_flip_invariance.gif) | 选项顺序打乱后判定高度一致（翻转率 0.0217） |
| 双语并排 | [S23_bilingual.gif](./S23_bilingual.gif) | 同一判定中英并排，en 0.906 / zh 0.848 |
| 三行上手 | [S24_quickstart.gif](./S24_quickstart.gif) | pip install → 启动 → POST 判定，全流程演示 |


### 对照与可靠性

| 场景 | 文件 | 一句话 |
|---|---|---|
| 本地 vs API 竞速 | [G25_race_local_vs_api.gif](./G25_race_local_vs_api.gif) | 同一决策：本地 21.0ms（RTX 5090） vs API 往返 1.51s（我方实测 n=40；第三方实测 Jev API 单决策 238–301 ms） |
| token 省费 | [G26_token_savings.gif](./G26_token_savings.gif) | 100 个决策：54 本地 / 46 升级 · 大模型调用 −55.0%（τ=0.5 档 79.6%） |
| 服务不可达默认不放行 | [G27_failclosed.gif](./G27_failclosed.gif) | 服务挂掉 → 默认拒绝，绝不静默放行 |

## 诚实标注

- 所有 GIF 为**合成演示**（虚构场景数据），仅用于展示模型能力与用法，非真实用户数据
- 帧内数字与 [BENCHMARKS.md](../../BENCHMARKS.md) 及 [MODEL_CARD.md](../../MODEL_CARD.md) 一致；局限（如 JevBench 0.5455 未过 58.4% 门）在模型卡如实披露

文件校验：见同目录 [SHA256SUMS](./SHA256SUMS)。
