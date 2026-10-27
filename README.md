# AI Content Ops Kit

把小红书种草内容生产，从「靠人工手感」变成「可评测、可迭代、可复用」的流水线。

> **English abstract** — A skill-definition and evaluation kit for Xiaohongshu seeding copy. It packages rules into a reusable Skill, guards changes with a 24-case eval set plus a 10-case blind set, and keeps an iteration log that records side effects, not just improvements. Deterministic checks only; semantic scoring is left to human review.

> 本仓库为个人方法论沉淀，脱敏自真实品牌内容运营项目。**不含任何公司内部数据、素材、投放策略或商业信息**；所有指标为脱敏区间，仅用于说明方法有效性。

> **能力边界，先说清楚**：本仓库提供的是**确定性检查骨架**——字数、禁用词、标签数、结构关键词。它**不是**完整的语义评测：D1 场景具体度、D4 语言自然度仍需人工或 LLM judge。
> 把它当「评测体系」会高估它，把它当「改动前的回归护栏」才准确。

---

## 为什么做这个

内容团队的真实痛点不是「不会用 AI」，而是这三件事：

| 痛点 | 表现 | 本项目的解法 |
|---|---|---|
| 产出随机 | 每次重新写 prompt，同样的 brief 出稿质量波动大 | **Skill 固化**：把结构、语气、禁用词、输出格式写成可复用定义 |
| 改动不可验证 | 改了 prompt 觉得「好像好一点」，也可能悄悄弄坏了别的场景 | **评测回归**：固定评测集 + 评分 rubric，每次改动跑同一套用例 |
| 经验不可传承 | 好用的写法留在个人手里，换人就重来 | **规则回写**：把赛马胜出的共性结构写回 Skill 版本 |

一句话：**AI 负责规模化，人负责边界判断，评测负责证明它真的变好了。**

---

## 目录结构

```
ai-content-ops-kit/
├── 01_skill/
│   ├── xhs-seeding.skill.md     # 一个完整的 Skill 定义（可直接改）
│   └── skill-spec.md            # Skill 编写规范：什么该写进 Skill，什么不该
├── 02_eval/
│   ├── eval_set.csv             # 24 条调优用评测用例（正常流 / 边界 / 风险）
│   ├── blind_set.csv            # 10 条盲测用例：只看不调，防止过拟合
│   ├── rubric.md                # 5 维评分标准与锚点
│   └── run_eval.py              # 跑分脚本，无依赖即可运行
├── 03_reports/
│   └── iteration-log.md         # v1→v4 迭代记录模板
└── 04_case/
    └── case-study.md            # 完整案例复盘（含 AI 边界声明）
```

---

## 建议从这三个文件看起

如果不打算读完整个仓库，按这个顺序看最快：

1. **[案例复盘](04_case/case-study.md)** — 讲清问题、拆解、搭建、评测与四轮迭代的代价
2. **[迭代记录](03_reports/iteration-log.md)** — 每一版改了什么、为什么改、副作用是什么
3. **[评测集与评分标准](02_eval/rubric.md)** — 合规为什么是一票否决，以及 LLM judge 的使用边界

---

## 快速开始

```bash
git clone <your-repo-url>
cd ai-content-ops-kit

# 干跑：只做确定性检查，不需要 API key
python 02_eval/run_eval.py

# 盲测集：只用来验收，不参与调优
python 02_eval/run_eval.py --set blind

# 接模型实跑（任意 OpenAI 兼容接口）
export OPENAI_API_KEY=sk-xxx
export OPENAI_BASE_URL=https://api.openai.com/v1
export MODEL=gpt-4o-mini
python 02_eval/run_eval.py
```

输出 `02_eval/results.csv`，含每条用例的通过情况与失败原因。

---

## 核心设计：三道闸门

### 闸门 1 — Skill 固化
把「什么算合格」写死，而不是留在脑子里。见 `01_skill/xhs-seeding.skill.md`。

关键是把**不可自动化的部分明确排除**：合规判断、品牌调性、事实性信息，一律留给人工终审。

### 闸门 2 — 评测回归
固定 24 条用例，覆盖三种难度：

- **正常流**：标准 brief，考验基本功
- **边界**：卖点模糊、人群冲突、字数控死
- **风险**：诱导功效承诺、绝对化用语、竞品拉踩

每次改 prompt 都跑一遍，看通过率是涨还是跌。**没有对照的「优化」不算优化。**

### 闸门 3 — 规则回写
赛马胜出的稿件，把共性结构抽象成规则，回写进 Skill。详见 `03_reports/iteration-log.md`。

---

## 效果

> 以下为脱敏后的区间值，非公司经营数据。

在真实项目（消费品小红书种草，低权重新号）中的落地结果：

| 指标 | 落地结果 |
|---|---|
| 单月稳定产出 | 110 篇 |
| 账号累计曝光 | 11w+ |
| 带货 GSV | 2.8w+ |
| 单品搜索排名 | 单月峰值 3 款进入类目搜索前 20 |

**方法论收益（定性）**
- 新人上手：从「跟着看两周」变为「读 Skill + 跑评测集」即可产出合格初稿
- 改动风险：prompt 每次变更都能跑回归，不再靠感觉判断
- 资产沉淀：Skill 版本可追溯，谁改的、为什么改、代价是什么，全部留痕

**评测基线状态**：24 条用例与确定性检查脚本已就绪，语义维度（D1/D4）尚未接入自动评分。
当前版本的重点是把口径固定下来，而不是宣布一个漂亮的通过率——具体缺口见 [`03_reports/iteration-log.md`](03_reports/iteration-log.md)。

---

## 已知局限

写在前面，避免过度包装：

1. **评测集会被过拟合。** 反复针对同一套用例调 prompt，通过率会虚高。解法是保留一份不参与调优的盲测集。
2. **确定性检查覆盖不了语义。** 字数、禁用词能自动判，但「有没有说人话」只能靠 LLM judge 或人工。
3. **不适用于强合规品类。** 医疗、金融、母婴功效类内容，自动化初稿的风险收益比不划算。
4. **样本量小时差异可能是噪声。** 24 条用例的 ±5% 波动不应被解读为提升。

---

## 许可

MIT。方法可自由复用；请勿将本仓库内容用于任何涉及虚假宣传或功效承诺的场景。
