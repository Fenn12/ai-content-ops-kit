#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评测跑分脚本 —— 确定性检查版

用途：对固定评测集跑一遍 Skill，输出通过率与失败原因。
特点：不接模型也能跑（干跑模式），只做可确定性判定的检查。

用法：
    python run_eval.py                       # 干跑，用占位输出
    OPENAI_API_KEY=sk-xxx MODEL=gpt-4o-mini python run_eval.py   # 接模型实跑

输出：results.csv（逐条结果）+ 控制台汇总
"""

import csv
import os
import re
import sys
import json
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
EVAL_SET = os.path.join(HERE, "eval_set.csv")
RESULTS = os.path.join(HERE, "results.csv")
SKILL = os.path.join(HERE, "..", "01_skill", "xhs-seeding.skill.md")

# ---------- D3 合规红线：一旦命中直接判 0 ----------
BANNED_WORDS = [
    # 绝对化
    "最好", "第一", "唯一", "国家级", "顶级", "极致", "100%", "全网最低",
    # 功效承诺
    "根治", "治疗", "祛除", "美白", "抗衰", "增高", "瘦身", "掉秤",
    "一周见效", "7天", "疗程",
    # 医疗
    "替代药物", "无需就医", "医用级",
    # 金融
    "保本", "稳赚", "零风险", "收益率",
]

# 高危品类：出现这些词应主动拒写功效，只做风险提示
HIGH_RISK_CATEGORIES = ["胶原蛋白", "褪黑素", "钙片", "代餐", "祛痘", "理财", "保健品"]

# ---------- D2 结构检查阈值 ----------
MIN_CHARS, MAX_CHARS = 150, 800
MIN_TAGS, MAX_TAGS = 3, 8


def load_skill(path):
    """读 Skill 定义，取正文作为 system prompt。"""
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"[warn] 未找到 Skill 文件：{path}")
        return "你是小红书种草文案助手。"


def build_prompt(skill_text, row):
    """把 Skill + 单条用例组装成 prompt。"""
    user = f"""请按 Skill 规范生成 1 版种草笔记。

产品：{row['product']}
人群：{row['audience']}
场景：{row['scene']}
语气：{row['tone']}
必须包含：{row['must_have']}
禁止出现：{row['must_avoid']}

按 JSON 输出，字段：hook / body / cta / tags / risk_flags"""
    return skill_text, user


def call_model(system, user):
    """调模型。未配置 API key 时返回占位文本，用于干跑。"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "【干跑模式：未配置 OPENAI_API_KEY，此处为占位输出】"

    try:
        from openai import OpenAI
    except ImportError:
        print("[warn] 未安装 openai 库，退回干跑模式。pip install openai")
        return "【干跑模式：openai 未安装】"

    client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    )
    resp = client.chat.completions.create(
        model=os.getenv("MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.7,
    )
    return resp.choices[0].message.content or ""


def check_d3(text):
    """合规红线检查。返回 (是否通过, 命中词列表)。"""
    hits = [w for w in BANNED_WORDS if w in text]
    return len(hits) == 0, hits


def check_d2(text, row):
    """结构完整性检查。返回 (是否通过, 问题列表)。"""
    issues = []
    length = len(re.sub(r"\s", "", text))
    if length < MIN_CHARS:
        issues.append(f"字数不足({length})")
    if length > MAX_CHARS:
        issues.append(f"字数超限({length})")

    tag_count = text.count("#")
    if tag_count < MIN_TAGS:
        issues.append(f"标签过少({tag_count})")
    if tag_count > MAX_TAGS:
        issues.append(f"标签过多({tag_count})")

    # 三段结构：粗判关键词是否出现
    has_pain = any(k in text for k in ["麻烦", "难", "怕", "尴尬", "凑合", "累", "痛"])
    has_mech = any(k in text for k in ["因为", "原理", "材质", "成分", "工艺", "结构"])
    has_body = any(k in text for k in ["摸起来", "吃起来", "闻起来", "感觉", "用下来", "洗完"])
    if not has_pain:
        issues.append("缺痛点段")
    if not has_mech:
        issues.append("缺机制段")
    if not has_body:
        issues.append("缺体感段")

    return len(issues) == 0, issues


def main():
    if not os.path.exists(EVAL_SET):
        sys.exit(f"找不到评测集：{EVAL_SET}")

    skill_text = load_skill(SKILL)
    rows = list(csv.DictReader(open(EVAL_SET, encoding="utf-8-sig")))
    print(f"载入 {len(rows)} 条用例 | Skill: {os.path.basename(SKILL)}")
    print(f"模型：{os.getenv('MODEL', '未配置（干跑）')}\n")

    out, total, passed = [], 0, 0
    by_cat = {}

    for row in rows:
        system, user = build_prompt(skill_text, row)
        try:
            text = call_model(system, user)
        except Exception as e:
            text = f"【调用失败：{e}】"

        ok_d3, hits = check_d3(text)
        if not ok_d3:
            ok, issues, score = False, [f"D3红线:{'/'.join(hits)}"], 0
        else:
            ok_d2, issues = check_d2(text, row)
            ok, score = ok_d2, (100 if ok_d2 else 60)

        total += 1
        passed += 1 if ok else 0
        cat = row["category"]
        by_cat.setdefault(cat, [0, 0])
        by_cat[cat][1] += 1
        by_cat[cat][0] += 1 if ok else 0

        out.append({
            "id": row["id"],
            "category": cat,
            "pass": "Y" if ok else "N",
            "score": score,
            "issues": "; ".join(issues) if issues else "",
            "output_preview": text[:80].replace("\n", " "),
        })

    with open(RESULTS, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        writer.writeheader()
        writer.writerows(out)

    print("=" * 46)
    print(f"总通过率：{passed}/{total} = {passed / total:.1%}")
    for cat, (p, t) in sorted(by_cat.items()):
        print(f"  {cat:<6} {p}/{t} = {p / t:.0%}")
    print("=" * 46)
    print(f"明细写入：{RESULTS}")
    print(f"时间：{datetime.now():%Y-%m-%d %H:%M}")
    if not os.getenv("OPENAI_API_KEY"):
        print("\n提示：当前为干跑模式，只有接模型后才能得到真实通过率。")


if __name__ == "__main__":
    main()
