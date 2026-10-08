# FAQ（常见问题）— Phocinae-Largha-150M-v1

关于斑海豹（Largha，**144.3M 参数中英双语决策模型**）的常见问题。本文引用的数字全部来自 [BENCHMARKS.md](../BENCHMARKS.md)——对外数字的唯一权威源。

## 1. 这到底是什么模型？

基于编码器的**决策模型**，不是聊天模型。一次前向把一段 `state` 加一组带类型的问题（`noul` 是否 · `choice` 多选一 · `score` 2–10 打分）变成带置信度的判定答案。不生成文本、不采样——固定批形状下结果确定。

## 2. 怎么在本地跑起来？

官方运行时是 [phocinae-server](https://github.com/Phocinae/phocinae-server)（纯 torch 前向，不需要额外运行时）：

```bash
git clone https://github.com/Phocinae/phocinae-server.git && cd phocinae-server
python -m venv .venv && . .venv/bin/activate
pip install fastapi uvicorn torch
PHOC_MODEL_DIR=/path/to/Phocinae-Largha-150M-v1 python -m phocinae.main   # http://127.0.0.1:8155
```

硬件三档、guard 与 MCP 部署见 [deployment.md](./deployment.md)；请求契约见 [protocol.md](./protocol.md)。

## 3. 服务是 OpenAI 兼容的吗？

**不是——这是刻意设计。**模型不是聊天模型，API 也不装成聊天 API。它只暴露 `POST /v1/systemone`（另有 `/permute`、`/batch`），且默认只监听 127.0.0.1。完整契约：[protocol.md](./protocol.md)。

## 4. 需要什么硬件？

| 档位 | 内存 / 存储 / GPU | 预期表现 |
|---|---|---|
| 底线（试跑） | 4 GB 内存 · 8 GB 存储 · 无 GPU | 每决策约 1.5–1.7 s（CPU 单线程） |
| 下限（高效） | 8 GB 内存 · 8 核 · ≥4 GB 显存（3060 → 30–60 ms；4090 → 18.6 ms） | GPU 18.6–60 ms；CPU 8 线程 8–21 决策/s |
| 推荐 | 16 GB · 512 GB NVMe · 8 GB+ 显存 | 其他应用同跑时 18.6–25 ms |

权重 288.6 MB（fp16 safetensors）；推理峰值约 1.6 GB 显存 / 1.8 GB 内存。
## 5. 速度到底多快？为什么 CPU 要约 1.5 s？

- GPU fp16 单决策：p50 **18.6 ms**（发布冻结值）。
- CPU 单线程：p50 **1.51 s/case**（1 case＝1 state＋5 题单次前向）——端到端（分词＋前向＋答案组装）单线程 fp32；单决策 ≈0.28 s。这是诚实的 CPU 数字，不是 GPU 数字。
- CPU 8 线程批处理：**8–21 决策/s**（b=1 → 21.0，b=32 → 8.7）。

## 6. 「翻转率（flip）」数字是什么意思？

我们把一个决策的选项重新排序、再看答案是否变化（即「翻转」，越低越好）。CPU fp32、空载：反转 **0.0300**（flip150）/ **0.0300**（flip400）· 随机平均 **0.0233** · 任一序翻转 **0.0433**。相当于每约 33 次重排改一次答案——比 Laya 域内（3.7%）好 0.7 pp，对比 Jev 约 9%、Laya 域外 19.4%。GPU 0.027/0.028 与 1k 行 0.0187/0.0205/0.0431 仅为备注值（协议不同）。

## 7. 模型是怎么校准的？

发货列 ECE **0.1313**（en）。checkpoint 里的 `temperature` 张量是哑元（全 1）；真正冻结的温度 **0.7698 / 0.7879 / 0.7560** 在 `rl_agent_config.json` 里，由 phocinae-server 在推理时应用。开发期重校准曾到 0.0106——**未随发布权重发货**，引用时不得套用。

## 8. 为什么没过 JevBench 验收门？

确实没过，而且我们公开它：**0.5108（118/231）**，验收门 58.4%。数字如实发布，从未用评测行训练，也不据此做任何榜单主张。（tool_selection k≤10 为 12/12。）

## 9. 中文真的能用吗？

在英文测试集实测 **0.797**，翻译版 typed-decisions 用例 **0.789**。同协议参考分：Laya 0.766 · JEV 0.727 · meraGPT 0.768（英文测试集）。诚实口径：中文行是英文测试用例的机器翻译——模型**没有原生中文训练行**。中文结果请当作跨语言迁移证据。

## 10. 能当安全/审批门用吗？

不能当唯一一道门。斑海豹是一线决策辅助：配合升级门（E1 τ=0.6 会把没把握的 45.7% 转出去）和确定性 L0 规则层（如 [phocinae-guard](https://github.com/Phocinae/phocinae-guard)）使用——绝不能作为破坏性/安全关键操作的唯一防护。


## 11. 能省多少钱？

τ=0.6 升级门把约一半决策留在本地（保留集准确率 0.797 → **0.886**，+0.089），没把握的 45.7% 转出，大模型调用砍掉 **−54%**（τ=0.5 档为 82.8%）。算例：每月每 1 万次路由决策 ≈ 1140 万 token ≈ 每年省 **$326**（Claude Sonnet 5 牌价，2026-10）。仅为估算——见 [cost-savings.md](./cost-savings.md)。

## 12. 主要局限是什么？

- 不能聊天/生成，不适于长文档推理与世界知识问答。
- 中文仅为翻译用例；长输入退化（16k/32k 探针：0.453 / 0.387）。
- JevBench 门未过（第 8 问）；序鲁棒性好但非完美（第 6 问）。
- 未做人口统计/公平性评测；英文业务运营域偏置会带入。

完整清单：[MODEL_CARD.md](../MODEL_CARD.md)。

## 14. 许可协议是什么？

权重：**Apache-2.0**（见 LICENSE）。底座编码器 `jhu-clsp/mmBERT-small`：请查阅其上游许可。server/guard 代码：Apache-2.0。

## 15. 如何引用与复现？

```bibtex
@misc{phocinae-largha-150m-v1,
  title  = {Phocinae-Largha-150M-v1: a 150M-class decision model},
  author = {Phocinae},
  year   = {2026},
  note   = {https://huggingface.co/Phocinae/Phocinae-Largha-150M-v1}
}
```

先校验权重（`sha256sum model.safetensors` → `db79d5ee2f16597f34e564f5a4363bddb5b5bbd9827c01819725dabcc7802697`），再按 [reproduce.md](./reproduce.md) 核对协议、冻结值与证据路径。冻结评测 harness 将在 github.com/Phocinae 发布。
