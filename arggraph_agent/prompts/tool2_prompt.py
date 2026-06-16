"""Tool 2 Prompt 模板：Component Classifier（论证组件分类器）

对应 SOP §3（MC 识别）、§4（段落 Claim 识别）、§5（段内 ADU 分类）、§6（节点命名规范）
"""

TOOL2_PROMPT = """## 任务：论证组件分类

你已经获得了一篇议论文的 ADU 切分列表。现在需要对每个 ADU 进行分类，构建节点表。

### 节点类型

| 类型 | 全称 | 含义 |
|------|------|------|
| major_claim | Major Claim | 全文中心论点 |
| paragraph_claim | Paragraph Claim | 段落主张 |
| analysis | Analysis | 分析/解释/展开 |
| evidence | Evidence | 论据/事例/引用 |
| evidence_analysis | Evidence Analysis | 对论据的分析/解释/回扣 |

### 第一步：识别 MC（中心论点）【§3】

**搜索范围**：仅在 P1（首段）和 Pn（末段）中搜索。

**优先级顺序**（从高到低）：
1. P1 段尾（最后 1-2 句）——最常见位置
2. P1 中后部
3. Pn 开头
4. Pn 结尾

**识别特征词**：
- "因此……" "可见……" "归根到底……"
- "我们应当……" "不能只是……而应……"
- "这启示我们……" "综上所述……"
- 含有总结性判断、价值表态的句子

**统摄测试**：如果你认为某个句子是 MC，检查其他段落的 claim 是否都可以理解为在支持/论证它？如果可以，它就是 MC。

**题目贴近测试**：如果有多个候选，选最贴近作文题目核心问题的那一个。

**MC 唯一**：全文只有一个 MC。如果首尾段都不像有 MC，选择最像全文总结的那个句子。

### 第二步：识别段落 Claim（段落主张）【§4】

对 P2 到 Pn-1 的每一段，按以下优先级寻找段落主张：

1. **段首句**（如果是判断句/观点句）——最高优先级
2. **段尾句**（如果是总结句）
3. 被本段最多句子支持的句子

**冲突时**：优先选段首句。

每个段落**必须有且仅有一个**段落 Claim，命名为 Pn_C。

### 第三步：分类剩余 ADU【§5】

对每段中非 MC/非 Claim 的 ADU 进行三类划分：

| 类型 | 判别标准 | 命名 |
|------|---------|------|
| analysis (A) | 直接解释/展开/限定 Claim 的抽象分析句；不含具体事例 | Pn_Am |
| evidence (E) | 提供事实/事例/引用/名言/数据的句子 | Pn_Em |
| evidence_analysis (EA) | 对 evidence 进行分析/解释/回扣 Claim 的句子 | Pn_EAm |

**判别要点**：
- E 包含具体的人、事、数据、引用 → 这是 evidence
- A 只有抽象说理，没有具体事例 → 这是 analysis
- EA 紧跟在 E 之后，解释 E 如何支持 Claim → 这是 evidence_analysis

### 第四步：节点命名【§6】

- MC 命名为 "MC"
- 段落 Claim 命名为 "Pn_C"（n=段号）
- A 命名为 "Pn_Am"（m 从 1 开始递增）
- E 命名为 "Pn_Em"
- EA 命名为 "Pn_EAm"

### 输出格式

必须严格按照以下 JSON 格式输出（只输出纯 JSON，不要 markdown code block）：

{
  "node_table": [
    {
      "node_id": "MC",
      "original_id": "P1_S4",
      "text": "因此，我们应当……",
      "type": "major_claim",
      "reasoning": ["位于第一段段尾", "含有总结性判断'因此'", "统摄P2/P3/P4的段落主张"]
    },
    {
      "node_id": "P2_C",
      "original_id": "P2_S1",
      "text": "勤奋是成功的基石",
      "type": "paragraph_claim",
      "reasoning": ["段首句", "提出本段核心判断"]
    },
    {
      "node_id": "P2_A1",
      "original_id": "P2_S2",
      "text": "只有通过不懈的努力才能积累足够的能力",
      "type": "analysis",
      "reasoning": ["解释P2_C成立的原因", "抽象分析句，不含具体事例"]
    },
    {
      "node_id": "P2_E1",
      "original_id": "P2_S3",
      "text": "苏轼在贬谪期间仍笔耕不辍，创作了大量传世之作",
      "type": "evidence",
      "reasoning": ["提供苏轼的具体事例", "属于事实论据"]
    },
    {
      "node_id": "P2_EA1",
      "original_id": "P2_S4",
      "text": "这说明在逆境中保持勤奋的态度尤为重要",
      "type": "evidence_analysis",
      "reasoning": ["对苏轼事例进行分析", "回扣段落主张"]
    }
  ]
}

### 注意事项
1. 每个节点必须有 reasoning（判定理由），至少一条
2. 节点按在原文中出现的顺序排列
3. 节点类型必须使用给出的五种之一
4. 每个非 MC/非 Claim 的 ADU 必须被分配为 A、E 或 EA 之一
5. reasoning 应包含具体的文本特征（如位置、关键词、句子类型）"""


def get_tool2_prompt() -> str:
    return TOOL2_PROMPT


def build_tool2_messages(essay_text: str, essay_topic: str, adu_list: list) -> list:
    """构建 Tool 2 调用的 messages"""
    import json
    adu_json = json.dumps(adu_list, ensure_ascii=False, indent=2)
    topic_info = f"\n作文题目：{essay_topic}" if essay_topic else ""

    return [
        {"role": "system", "content": TOOL2_PROMPT},
        {"role": "user", "content": (
            f"请对以下议论文进行论证组件分类。{topic_info}\n\n"
            f"**原始文本**：\n{essay_text}\n\n"
            f"**ADU 切分结果**：\n{adu_json}\n\n"
            f"请按 SOP 规则完成：识别 MC → 识别各段 Claim → 分类剩余 ADU。"
        )},
    ]
