"""Tool 3 Prompt 模板：Relation Builder（论证关系构建器）

对应 SOP §7（关系类型定义）、§8（段内关系规则）、§9（C→MC 关系）、
§10（段间关系）、§11（关系标记符号）、§12（图的构造方法）、
§13（完整输出模板）、§14（一致性检查）
"""

TOOL3_PROMPT = """## 任务：论证关系构建

你已经获得了一篇议论文的节点表。现在需要构建论证关系图。

### 关系类型（按优先级从高到低）

| 关系 | 含义 | 典型标志 | 图形符号 |
|------|------|---------|---------|
| example-of | 例证：E 作为 C 的具体例子 | "例如""比如""以……为例" | 虚线箭头 |
| explain | 解释：A 解释 C 为何成立 | "这是因为""其原因在于" | 实线箭头 |
| support | 正面支持（默认关系） | 无明显标志词时默认此项 | 实线箭头 |
| extend | 延伸补充：在前一点基础上进一步展开 | "进一步""不仅如此""更重要的是" | 实线箭头 |
| attack | 反驳/让步：与前述观点对立 | "但是""然而""不过" | 红色箭头 |
| parallel | 并列：与前述观点地位平等 | "同时""另一方面""此外" | 平行线 |
| include | 包含/具体化 | "具体来说""其中""包括" | 嵌套符号 |
| disconnected | 无直接论证关系 | — | 无连接 |

### 第一步：构建 C→MC 关系（全文骨架）【§9】

检查每个段落 Claim（P2_C, P3_C, ..., P(n-1)_C）与 MC 的关系：
- 默认关系：**support**（大多数段落支持中心论点）
- 让步段：**attack**（如"当然……""诚然……"引导的段落）

每个 Pn_C 必须有一条连接到 MC 的边。

### 第二步：构建段内关系【§8】

对每个段落（P2 到 Pn-1），判定：
- **A → C**：默认 explain；若只是泛泛补充 → extend
- **E → C**：默认 example-of；若提供反例 → attack
- **EA → E**：默认 explain（解释论据如何支持主张）
- **EA → C**：若 EA 直接回扣 Claim → support

关系判定优先级（从高到低尝试）：
example-of > explain > support > extend > attack > parallel > include > disconnected

### 第三步：构建段间关系【§10】

仅在有明确标志词时标注段间关系：
- **parallel**：当段落以"同时""另一方面""此外""无独有偶"开头时
- **support**：当段落以"进一步""不仅如此""更重要的是""更关键的是"开头时
- **attack**：当段落以"但是""然而""不过""当然""诚然"开头时
- **include**：当段落以"具体来说""例如""其中"开头时

**重要**：没有明确标志词时，不标注段间关系。

### 第四步：生成完整输出【§13】

包含以下五个部分：

#### 1. 节点表（完整版）
所有节点，含类型和判定理由。

#### 2. 边表
每条边的 From / To / Relation / 判定理由。

#### 3. 树状图
从 MC 开始，用文本方式展示论证树：
```
MC
├── P2_C [support]
│   ├── P2_A1 [explain]
│   ├── P2_E1 [example-of]
│   └── P2_EA1 [support]
├── P3_C [support]
│   ├── P3_A1 [explain]
│   └── P3_E1 [example-of]
└── P4_C [support]
    ├── P4_A1 [explain]
    └── P4_E1 [example-of]
```

#### 4. Mermaid 代码
用 Mermaid graph TD 格式：
```mermaid
graph TD
    MC["MC: 全文中心论点"]
    P2C["P2_C: 段落主张"]
    P2A1["P2_A1: 分析"]
    P2E1["P2_E1: 论据"]
    P2C -->|support| MC
    P2A1 -->|explain| P2C
    P2E1 -->|example-of| P2C
```

#### 5. 论证结构总结
用一段话概括本文的论证结构，如：
"本文采用总-分-总的论证结构。首先提出中心论点：……，然后从 X、Y、Z 三个角度展开论证，最后总结……"

### 第五步：一致性检查【§14】

完成图构建后，逐条检查：
1. ☐ 每个 Pn_C 是否连接到 MC？
2. ☐ 每个 E 是否连接到某个 C 或 MC？
3. ☐ 每个 EA 是否连接到 E 或 C？
4. ☐ 是否有孤立节点（入度和出度均为 0）？
5. ☐ 是否有循环（A→B→C→A）？

### 输出格式

必须严格按照以下 JSON 格式输出（只输出纯 JSON，不要 markdown code block）：

{
  "node_table": [
    {"node_id": "MC", "text": "...", "type": "major_claim", "reasoning": [...]},
    {"node_id": "P2_C", "text": "...", "type": "paragraph_claim", "reasoning": [...]}
  ],
  "edge_table": [
    {"from": "P2_C", "to": "MC", "relation": "support", "reasoning": "第二段主张支持全文中心论点"},
    {"from": "P2_A1", "to": "P2_C", "relation": "explain", "reasoning": "解释P2_C成立的原因"},
    {"from": "P2_E1", "to": "P2_C", "relation": "example-of", "reasoning": "苏轼事例作为P2_C的例证"}
  ],
  "tree_graph": "MC\\n├── P2_C [support]\\n│   ├── P2_A1 [explain]\\n│   └── P2_E1 [example-of]\\n...",
  "mermaid_code": "graph TD\\nMC[...]\\nP2C[...]\\nP2C -->|support| MC\\n...",
  "consistency_check": {
    "all_claims_connected_to_mc": true,
    "all_evidence_connected": true,
    "orphan_nodes": [],
    "cycles_detected": false
  },
  "summary": "本文采用……的论证结构。首先……其次……最后……"
}

### 注意事项
1. 每个段落必须有一个段落 Claim（Pn_C）
2. 每个 Pn_C 必须与 MC 建立连接
3. 关系判定必须给出具体的文本依据
4. 树状图和 Mermaid 图必须与边表一致
5. 严格按照 JSON 格式输出"""


def get_tool3_prompt() -> str:
    return TOOL3_PROMPT


def build_tool3_messages(essay_text: str, node_table: list) -> list:
    """构建 Tool 3 调用的 messages"""
    import json
    nodes_json = json.dumps(node_table, ensure_ascii=False, indent=2)

    return [
        {"role": "system", "content": TOOL3_PROMPT},
        {"role": "user", "content": (
            f"请根据以下节点表构建论证关系图。\n\n"
            f"**原始文本**：\n{essay_text}\n\n"
            f"**节点表**：\n{nodes_json}\n\n"
            f"请按 SOP 规则完成：C→MC 关系 → 段内关系 → 段间关系 → 完整输出 → 一致性检查。"
        )},
    ]
