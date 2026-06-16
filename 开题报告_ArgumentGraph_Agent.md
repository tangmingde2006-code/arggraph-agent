# 《人工智能基础》大作业开题报告

## 选题一：基于 ReAct 范式的论证图自动拆解 Agent

---

**项目名称**：ArgGraph-Agent —— 面向高考议论文的论证结构自动拆解智能体

**选题编号**：选题一（AI Agent 框架搭建）

**组长**：曾栎凝（学号 3250102562）
**组员**：汤明德（学号 3250104743）

**提交日期**：2026 年 5 月 31 日

---

## 目录

1. [选题背景与研究意义](#1-选题背景与研究意义)
2. [技术背景调研与文献分析](#2-技术背景调研与文献分析)
3. [核心原理预研](#3-核心原理预研)
4. [技术方案设计](#4-技术方案设计)
5. [系统架构与模块设计](#5-系统架构与模块设计)
6. [团队分工细节](#6-团队分工细节)
7. [任务进度表](#7-任务进度表)
8. [可行性分析](#8-可行性分析)
9. [预期成果与交付物](#9-预期成果与交付物)
10. [参考文献](#10-参考文献)

---

## 1. 选题背景与研究意义

### 1.1 选题背景

自 2023 年大语言模型（LLM）爆发以来，AI 的定位正从"聊天机器人"向"智能代理（Agent）"快速演进。虽然 LLM 具备强大的常识和推理能力，但它本质上是一个受限于训练数据的闭环系统——它无法感知外部世界，也无法精确执行结构化的分析流程。AI Agent 的出现打破了这层限制：通过引入 **ReAct（Reasoning + Acting）范式**，赋予模型调用外部工具和自主决策的能力，使其从一个"会说话的模型"变成一个"能做事的智能体"（Yao et al., 2023）。这是 2023 年以来 AI 应用层最重要的范式之一，也是 ChatGPT、Claude 等产品背后的关键技术。

与此同时，**论辩挖掘（Argument Mining, AM）** 作为自然语言处理的一个新兴子领域，致力于自动从自然语言文本中提取论证结构——包括论证组件（Argumentative Components, ACs）的识别、分类，以及论证关系（Argumentative Relations, ARs）的判定。从论证图理论到文本挖掘技术的跨越，Peldszus & Stede（2013）做了关键的桥梁性综述工作。近年来，该领域取得了显著进展（Ivanova et al., 2024），并被应用于自动作文评分（Persing & Ng, 2015）、写作辅助（Stab & Gurevych, 2017）和论证搜索（Wachsmuth et al., 2017a）等下游任务。

然而，现有的 AM 系统存在一个根本性的困境：**端到端的深度学习模型虽然高效，却缺乏可解释性和可控性；基于规则的传统方法虽然透明，却难以处理自然语言的复杂性。** 本项目试图走第三条路：将严谨的人工标注规范（SOP）编码为 AI Agent 的工具链，使 LLM 在结构化流程的约束下执行论证拆解，既保留了规则的严格性和可解释性，又利用了 LLM 的语义理解能力。

本项目选择**高考议论文**作为分析对象，原因有二：其一，议论文是中文学术写作的基础文体，对其论证结构的自动分析具有广泛的教育应用前景；其二，高考议论文长度适中（约 800–1000 字）、结构相对规整，适合作为方法论验证的起点。

### 1.2 研究意义

- **理论意义**：探索"规则驱动的 Agent"这一新兴范式在论辩挖掘中的适用性，为可解释的 NLP 系统设计提供参考。
- **应用意义**：若实现可靠的论证结构自动拆解，将为自动作文评分、写作智能辅导、论证质量评估等教育技术应用奠定基础。
- **教学意义**：作为《人工智能基础》课程的项目实践，本项目完整覆盖了选题一所要求的技术要点——Prompt 工程、ReAct 循环、工具调用、对话历史管理——是将课堂理论转化为工程能力的典型训练。

---

## 2. 技术背景调研与文献分析

### 2.1 技术现状：AI Agent 与论辩挖掘的交叉前沿

#### 2.1.1 AI Agent 的主流范式

当前，AI Agent 的主流构建范式主要包括以下几种：

**（1）ReAct 范式（Reasoning + Acting）**

ReAct（Yao et al., 2023）是当前最具影响力的 Agent 范式。其核心思想是让 LLM 在"思考（Thought）"和"行动（Action）"之间交替循环：模型首先生成对当前状态的分析（Thought），然后决定下一步调用哪个工具（Action），获取工具返回的观察结果（Observation）后，再进入下一轮思考。这种交错推理-行动的范式有效解决了 LLM 的"幻觉"问题——通过工具调用来获取模型参数之外的真实信息或执行精确操作。

ReAct 与 OpenAI Function Calling 的核心区别在于：Function Calling 是一种**接口规范**（定义函数的 JSON Schema 让模型输出参数），而 ReAct 是一种**认知架构**（规定了推理和行动的交替模式）。在实际系统中，两者常常结合使用：以 ReAct 为循环框架，以 Function Calling 为工具调用机制。

**（2）Plan-and-Execute 范式**

该范式将 Agent 的运作分为"规划"和"执行"两个阶段：规划阶段生成完整的行动计划（通常是一个步骤列表），执行阶段按计划逐步调用工具。其优势在于全局最优性和可预测性，劣势在于对动态环境的适应性不足。

**（3）Multi-Agent 协作范式**

在多 Agent 架构中，不同 Agent 承担不同角色（如规划者、执行者、审查者），通过消息传递进行协作。典型案例如 AutoGen（Wu et al., 2023）和 MetaGPT（Hong et al., 2023）。

#### 2.1.2 论辩挖掘的技术现状

论辩挖掘（AM）的技术路线经历了从规则方法到深度学习、再到端到端生成式框架的演进：

**（1）传统的流水线方法**

将 AM 分解为四个子任务（Das et al., 2025；Stede & Schneider, 2018）：论证单元切分（Component Segmentation）、论证组件分类（Component Classification）、关系识别（Relation Identification）、关系分类（Relation Classification）。前两个子任务合称论证组件抽取（ACE），后两个合称论证关系分类（ARC）。流水线方法面临的主要挑战是误差传播——前一步的错误会连锁影响后续步骤。

**（2）端到端的依赖解析方法**

以 biaffine dependency parsing 为代表的端到端方法（Morris et al., 2020）试图在一个统一的模型中完成组件抽取和关系构建。这类方法通过 BIO 标签序列和依存弧来同时表示组件边界和关系结构，但往往需要复杂的后处理步骤。

**（3）生成式方法**

近期的 argTANL 框架（Das et al., 2025）将 AM 重新表述为"增强自然语言生成"（Augmented Natural Language, ANL）任务：将论证结构信息（组件类型标签、关系标签）以特殊格式嵌入原始文本，使模型通过生成标注文本来完成 AM。该框架的实验表明，论证标记词（markers）——如"因此""但是""例如"——对模型性能有显著增强作用，这与本项目 SOP 中以关联词作为切分触发词的思路高度一致。

**（4）论证质量评估（Argumentation Quality, AQ）**

Wachsmuth et al.（2017a）首次对论证质量评估进行了全面梳理，提出了涵盖三个高层维度（逻辑质量、修辞质量、辩证质量）和 15 个子维度的分类体系。该体系源自 Blair（2012）对"好论证"的哲学分析——逻辑维度关注前提的可接受性（acceptability）、相关性（relevance）和充分性（sufficiency）；修辞维度关注论证的说服效果和语言表达；辩证维度关注其在论辩对话中的合理性。Lauscher et al.（2020）在此基础上构建了大规模多领域语料库 GAQCorpus，验证了基于理论维度的细粒度论证质量标注的可行性，并展示了如何将维度预测转化为可操作的写作反馈。Ivanova et al.（2024）进一步对 211 篇文献和 32 个数据集进行了系统综述，识别出该领域的主要研究空白，包括：缺乏多维度联合标注的数据集、跨领域泛化能力不足、以及质量评估与结构分析的割裂。

**（5）中文自动作文评分（ACEE）与论证语料**

中文自动作文评分（Automatic Chinese Essay Evaluation, ACEE）是 NLP 在教育领域的重要应用方向。Yang et al.（2023）对 ACEE 进行了系统性文献综述，梳理了语料库构建、特征工程、评分模型三大技术模块，并指出当前瓶颈在于深层特征（如论证结构、逻辑连贯性）的自动提取能力不足。在具体系统实践方面，Chang & Sung（2019）开发的 SmartWriting-Mandarin 系统是针对中文作为外语学习者的代表性 AES 案例，展示了从特征提取到分数映射的完整工程流程。

在语料资源方面，中文议论文论证挖掘近年来取得了重要进展。Ren et al.（2024）构建的 CEAMC（Chinese Essay Argument Mining Corpus）包含 226 篇高中中文议论文，每篇标注了 4 个粗粒度和 10 个细粒度的论证成分标签，是目前中文 AM 领域最全面的标注语料之一。清华 NLP 实验室发布的"中文议论文组织评估数据集"（Chinese Essay Dataset for Organization Evaluation）则提供了 Thesis / Main Idea / Evidence 等篇章结构标签，其标注规范对 SOP 的标签体系设计具有直接参考价值。此外，佟威与赵静宇（2020）通过实证研究论证了"分项评分优于整体评分"的结论，为本项目"辅助评价"而非"替代评分"的定位提供了教育测量学依据。

#### 2.1.3 本项目的技术定位

综合以上分析，本项目在技术图谱中占据一个独特的交叉位置：**以 ReAct Agent 为架构框架，以结构化 SOP 为规则引擎，以 DeepSeek LLM 为语义推理核心，实现面向中文高考议论文的端到端论证图自动拆解。** 与现有工作的区别在于：

| 维度 | 传统流水线 AM | 端到端深度学习 AM | **本项目（Agent + SOP）** |
|------|--------------|-------------------|--------------------------|
| 架构 | 多模型串联 | 单一神经网络 | LLM + 工具链 |
| 规则来源 | 隐式（训练数据） | 隐式（训练数据） | 显式（SOP 编码为 Prompt + Tool） |
| 可解释性 | 低 | 低 | **高**（每步输出带判定理由） |
| 可控性 | 低 | 低 | **高**（SOP 规则可独立修改） |
| 语言 | 主要英文 | 主要英文 | **中文（高考议论文）** |

---

## 3. 核心原理预研

### 3.1 AI Agent 如何通过 Prompt 约束输出格式

本项目 Agent 的核心工作机制基于 ReAct 范式，其 Prompt 设计包含三个层次：

**第一层：系统角色定义**

```text
你是一个高考议论文论证结构分析专家。你的任务是严格按照
给定的 SOP（标准操作流程），将一篇议论文拆解为论证图
（Argument Graph）。你必须使用提供的工具逐步完成分析，
不得跳过任何步骤，不得自行编造规则。
```

**第二层：工具选择指令**

Agent 的 ReAct 循环按照"Thought → Action → Tool Call"的模式运行。每个工具对应 SOP 的一个阶段，Agent 通过 Thought 分析当前状态，通过 Action 决定调用哪个工具。

**第三层：输出格式约束**

每个工具的输出遵循严格的 Schema。以 Tool 2（论证组件分类器）为例，其输出格式要求为：

```json
{
  "MC": {
    "node_id": "MC",
    "text": "...",
    "reasoning": ["位于第一段段尾", "含有总结性判断", "能统摄主体段落"]
  },
  "paragraph_claims": [
    {
      "node_id": "P2_C",
      "text": "...",
      "reasoning": ["段首句", "提出本段核心判断"]
    }
  ],
  "components": [...]
}
```

这种结构化输出约束确保了 Agent 的行为完全可预测、可验证。

### 3.2 论证图（Argument Graph）的形式定义

本项目输出的论证图由三个数学对象构成：

**定义 1（论证图）**：一个论证图 $G = (V, E, T)$，其中：
- $V = \{v_1, v_2, ..., v_n\}$ 是论证单元（ADU）节点的有限集合
- $E \subseteq V \times V \times R$ 是带关系标签的有向边集合，$R = \{\text{support, attack, example-of, explain, extend, parallel, include, disconnected}\}$
- $T: V \to \{\text{MC, paragraph-claim, analysis, evidence, evidence-analysis}\}$ 是节点类型赋值函数

**定义 2（ADU 切分）**：给定原始文本 $D$，ADU 切分是一个划分 $\Pi = \{S_1, S_2, ..., S_k\}$，其中每个 $S_i$ 是一个连续文本片段，满足：
- 一级切分以句号类标点（。？！；）为界
- 二级切分由关联词（因为/所以/但是/例如等）触发
- 默认不切分，仅在显式论证结构标记出现时切分

**定义 3（关系约束）**：论证图中的边 $E$ 必须满足以下一致性条件：
- $\forall v \in V_{\text{paragraph-claim}}: \exists e = (v, \text{MC}) \in E$（每个段落主张必须连接 MC）
- $\forall v \in V_{\text{evidence}}: \exists e = (v, w) \in E$ 且 $T(w) \in \{\text{paragraph-claim}\}$（每个论据必须连接某个主张）
- $G$ 中不存在有向环

### 3.3 ReAct 循环下的 SOP 执行逻辑

本项目的核心创新在于将 14 节 SOP 规则编码为 Agent 的三个工具，通过 ReAct 循环实现 SOP 的阶段式执行。其执行逻辑如下：

```
输入：一篇高考议论文 D

Step 1（Thought）: Agent 分析 D 的结构特征，
    判断是否需要分段预处理
Step 1（Action）: 调用 Tool 1 (ADU Segmenter)
Step 1（Observation）: 获得 ADU 列表 {P1_S1, P1_S2, ..., Pn_Sk}

Step 2（Thought）: Agent 审查 ADU 列表，
    确定第一段/最后一段为 MC 候选范围
Step 2（Action）: 调用 Tool 2 (Component Classifier)
Step 2（Observation）: 获得节点表（含 MC、段落 Claim、A/E/EA 分类）

Step 3（Thought）: Agent 验证节点表的完整性，
    检查是否每个段落都有 Pn_C
Step 3（Action）: 调用 Tool 3 (Relation Builder)
Step 3（Observation）: 获得边表、树状图、Mermaid 图

Step 4（Thought）: Agent 执行 §14 一致性检查
Step 4（Action）: 输出完整的 Argument Graph
```

这个执行流程清晰地体现了选题一的"多步调用"要求——切分 → 分类 → 建图，三步依次依赖，每一步的输出是下一步的输入。

---

## 4. 技术方案设计

### 4.1 整体架构

ArgGraph-Agent 采用三层架构：**接口层 → Agent 核心层 → 工具层**。

<div class="arch-diagram">

<div class="arch-layer layer-interface">
<div class="layer-label">接口层</div>
<div class="layer-row">
<div class="arch-box">自然语言对话接口</div>
<div class="arch-box">Web 界面<br>(进阶: Gradio)</div>
</div>
</div>

<div class="arch-arrow">▼</div>

<div class="arch-layer layer-core">
<div class="layer-label">Agent 核心层</div>
<div class="layer-box-main">
<div class="core-title">ReAct 推理循环</div>
<div class="core-flow">Thought → Action → Observation</div>
<div class="layer-row">
<div class="arch-box small">System Prompt</div>
<div class="arch-box small">对话历史管理<br>(Messages)</div>
</div>
</div>
</div>

<div class="arch-arrow">▼</div>

<div class="arch-layer layer-tools">
<div class="layer-label">工具层</div>
<div class="layer-row three">
<div class="arch-box tool">Tool 1<br><strong>ADU 切分器</strong><br>§1–2</div>
<div class="arch-box tool">Tool 2<br><strong>组件分类器</strong><br>§3–6</div>
<div class="arch-box tool">Tool 3<br><strong>关系构建器</strong><br>§7–14</div>
</div>
<div class="backend-line">DeepSeek-v3 API（统一推理后端）</div>
</div>

</div>

### 4.2 技术栈

| 组件 | 技术选型 | 理由 |
|------|----------|------|
| 编程语言 | Python 3.11+ | 生态成熟，NLP 库丰富 |
| LLM API | DeepSeek-v3（deepseek-chat） | 中文理解能力强，API 价格低廉（¥1/百万 token） |
| API 调用 | openai Python SDK（兼容 DeepSeek 接口） | 标准 OpenAI 兼容接口，降低开发成本 |
| 对话管理 | 原生 messages 列表 | 满足选题一"不允用 LangChain"的要求 |
| JSON 解析 | Python json 模块 + Pydantic 验证 | 结构化输出校验 |
| 图表生成 | Mermaid.js（通过 API 返回代码） | 无需额外依赖，浏览器即可渲染 |
| Web 界面（进阶） | Gradio | 选题一进阶要求，轻量级 |
| 版本控制 | Git | 代码管理 |

### 4.3 三个核心工具的设计

#### Tool 1: ADU Segmenter（论证单元切分器）

**功能**：接收原始议论文文本，输出编号的论证单元列表。

**SOP 依据**：§1（ADU 划分规则）、§2（分析范围）

**实现逻辑**：

```
1. 预处理：按自然段分解为 {P1, P2, ..., Pn}
2. 一级切分：对每段按句号类标点（。？！；）切分 → 基础句
3. 二级切分：对过长句子检测关联词：
   - "因为……所以……" → 切为两个单元
   - "虽然……但是……" → 切为两个单元
   - "例如……这说明……" → 切为两个单元
   - "不是……而是……" → 切为两个单元
4. 默认策略：不确定时，不切分
5. 编号：Pn_Sm（n=段号，m=本段第m个ADU）
```

**输入 Schema**：
```json
{
  "essay_text": "（完整议论文文本，含所有自然段）"
}
```

**输出 Schema**：
```json
{
  "segments": [
    {"id": "P1_S1", "text": "……"},
    {"id": "P1_S2", "text": "……"},
    {"id": "P2_S1", "text": "……"}
  ],
  "paragraph_count": 4,
  "total_adus": 15
}
```

**Prompt 设计要点**：
- 在 system prompt 中完整嵌入 §1 的切分规则表格
- 明确优先级：默认不切 → 仅在有显式关联词时切
- 要求对每次二级切分给出触发了哪个关联词

#### Tool 2: Component Classifier（论证组件分类器）

**功能**：接收 ADU 列表和原始文本，识别 MC、段落 Claim，并将剩余 ADU 分类为 analysis / evidence / evidence-analysis。

**SOP 依据**：§3（MC 识别）、§4（段落 Claim 识别）、§5（段内 ADU 分类）、§6（节点命名规范）

**实现逻辑**：

```
1. MC 识别：
   - 搜索范围：仅 P1 和 Pn（首尾段）
   - 优先位置：P1 段尾 > P1 中后部 > Pn 开头 > Pn 结尾
   - 识别词汇："因此""可见""归根到底""我们应当""不能只是……而应"
   - 统摄测试：其他段落的 claim 是否都可以理解为在支持它？
   - 题目贴近测试：多个候选时，选最贴合作文题核心的一个

2. 段落 Claim 识别（对 P2 到 Pn-1 每一段）：
   - 优先段首句（若是判断句）> 段尾句（若是总结句）> 被最多句子支持的句子
   - 冲突时：选段首句

3. 剩余 ADU 分类（对每段）：
   - Pn_Am：直接解释/展开/限定 Claim 的抽象分析句
   - Pn_Em：提供事实/事例/引用/名言/数据的句子
   - Pn_EAm：对 evidence 进行分析/解释/回扣的句子

4. 对每个识别结果标注判定理由（至少一条）
```

**输入 Schema**：
```json
{
  "essay_text": "（原始全文）",
  "essay_topic": "（作文题目，可选，用于 MC 的题目贴合测试）",
  "adu_list": [
    {"id": "P1_S1", "text": "……"},
    ...
  ]
}
```

**输出 Schema**：
```json
{
  "node_table": [
    {
      "node_id": "MC",
      "original_id": "P1_S4",
      "text": "……",
      "type": "major_claim",
      "reasoning": ["位于第一段段尾", "含有总结性判断'因此'", "统摄P2/P3/P4的段落主张"]
    },
    {
      "node_id": "P2_C",
      "original_id": "P2_S1",
      "text": "……",
      "type": "paragraph_claim",
      "reasoning": ["段首句", "提出本段核心判断"]
    },
    {
      "node_id": "P2_A1",
      "original_id": "P2_S2",
      "text": "……",
      "type": "analysis",
      "reasoning": ["解释P2_C成立的原因"]
    },
    {
      "node_id": "P2_E1",
      "original_id": "P2_S3",
      "text": "……",
      "type": "evidence",
      "reasoning": ["提供苏轼事例"]
    }
  ]
}
```

#### Tool 3: Relation Builder（论证关系构建器）

**功能**：接收节点表，构建段内关系、段间关系、MC 关系，输出边表、树状图和 Mermaid 代码，并执行一致性检查。

**SOP 依据**：§7（关系类型定义）、§8（段内关系规则）、§9（C→MC 关系）、§10（段间关系）、§11（关系标记符号）、§12（图的构造方法）、§13（完整输出模板）、§14（一致性检查）

**实现逻辑**：

```
1. C→MC 关系构建（全文骨架图，§9 & §12.1）：
   - 每个 Pn_C 对 MC 的关系判定
   - 默认 support，让步段可能为 attack

2. 段内关系构建（§8 & §12.2）：
   - A → C：Explain / Extend / Disconnected
   - E → C：Example-of / Disproof / Disconnected
   - EA → E：Explain / Extend / Disconnected
   - 关系判定优先级：example-of > explain > support > extend > attack > parallel > include > disconnected

3. 段间关系构建（§10 & §12.3）：
   - 仅在有明确标志词时标注：
     - parallel："同时/另一方面/此外"
     - support："进一步/不仅如此/更重要的是"
     - attack："但是/然而/不过"
     - include："具体来说/例如/其中"

4. 生成输出（§13）：
   - 节点表（完整版，含类型和判定理由）
   - 边表（From / To / Relation / 判定理由）
   - 树状图（从 MC 开始，├── 结构）
   - Mermaid 代码（graph TD 格式）

5. 一致性检查（§14）：
   - 每个 Pn_C 是否连接到 MC
   - 每个 E 是否连接到某个 C
   - 每个 EA 是否连接到 E 或 C
   - 是否有孤立节点
   - 是否有循环
```

**输入 Schema**：
```json
{
  "essay_text": "（原始全文，用于上下文参考）",
  "node_table": [
    {"node_id": "MC", "text": "...", "type": "major_claim"},
    {"node_id": "P2_C", "text": "...", "type": "paragraph_claim"},
    ...
  ]
}
```

**输出 Schema**：
```json
{
  "edge_table": [
    {"from": "P2_C", "to": "MC", "relation": "support", "reasoning": "第二段主张支持全文中心论点"},
    {"from": "P2_A1", "to": "P2_C", "relation": "explain", "reasoning": "解释P2_C成立的原因"},
    {"from": "P2_E1", "to": "P2_C", "relation": "example-of", "reasoning": "苏轼事例作为P2_C的例证"}
  ],
  "tree_graph": "MC\n├── P2_C [support]\n│   ├── P2_A1 [explain]\n│   ├── P2_E1 [example-of]\n│   └── P2_EA1 [support]\n...",
  "mermaid_code": "graph TD\nMC[...]\nP2C[...]\nP2C -->|support| MC\n...",
  "consistency_check": {
    "all_claims_connected_to_MC": true,
    "all_evidence_connected": true,
    "orphan_nodes": [],
    "cycles_detected": false
  },
  "summary": "本文采用……的论证结构。首先……其次……最后……"
}
```

### 4.4 Agent 主体循环（ReAct 实现）

```python
# 核心循环伪代码
def agent_loop(essay_text: str, essay_topic: str = None) -> dict:
    """ReAct 循环：分步调用三个工具，生成完整论证图"""

    # 初始化对话历史
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},  # 含 SOP 概要
        {"role": "user", "content": f"请分析以下议论文：\n{essay_text}"}
    ]

    # Step 1: ADU 切分
    # Agent Thought: "首先需要将文本切分为论证单元。"
    # Agent Action: call_tool("ADU_Segmenter", {"essay_text": essay_text})
    adu_result = call_tool_1(essay_text)
    messages.append({"role": "assistant", "content": f"[Tool Result] ADU切分完成，共{len(adu_result['segments'])}个单元"})

    # Step 2: 组件分类
    # Agent Thought: "ADU切分完成。接下来需要识别MC和段落Claim，
    #   并将剩余ADU分类为A/E/EA。"
    # Agent Action: call_tool("Component_Classifier", {...})
    node_result = call_tool_2(essay_text, essay_topic, adu_result["segments"])
    messages.append({"role": "assistant", "content": f"[Tool Result] 组件分类完成，MC={node_result['MC']['node_id']}"})

    # Step 3: 关系构建
    # Agent Thought: "组件分类完成，现在需要构建论证关系图。"
    # Agent Action: call_tool("Relation_Builder", {...})
    graph_result = call_tool_3(essay_text, node_result["node_table"])

    # Step 4: 结果整合与呈现
    # Agent Thought: "论证图构建完成，一致性检查通过。
    #   现在将所有结果整合输出。"
    return format_final_output(node_result, graph_result)
```

### 4.5 Prompt 工程设计

Agent 的 System Prompt 是整个系统的核心控制机制。其设计遵循"约束输出格式 + 引导推理步骤 + 嵌入领域知识"三层策略：

**核心设计原则**：
1. **角色锚定**：明确 Agent 是"高考议论文论证结构分析专家"
2. **规则透传**：将 SOP 的核心规则（切分优先级、MC 判别特征、关系类型优先级）以结构化表格嵌入 Prompt
3. **步骤强制**：禁止 Agent 跳过中间步骤直接给出最终结论
4. **格式锁死**：每个工具的输出 Schema 以 JSON 形式在 Prompt 中显式定义
5. **拒绝策略**：当输入文本不具备论证结构时，Agent 应明确返回"无法分析"而非强行编造

---

## 5. 系统架构与模块设计

### 5.1 模块划分

```
arggraph_agent/
├── agent.py            # Agent 主循环（ReAct 推理）
├── tools/
│   ├── __init__.py
│   ├── adu_segmenter.py    # Tool 1: ADU 切分器
│   ├── component_classifier.py  # Tool 2: 组件分类器
│   └── relation_builder.py      # Tool 3: 关系构建器
├── prompts/
│   ├── system_prompt.py    # 系统角色 Prompt 模板
│   ├── tool1_prompt.py     # Tool 1 的 Prompt 模板
│   ├── tool2_prompt.py     # Tool 2 的 Prompt 模板
│   └── tool3_prompt.py     # Tool 3 的 Prompt 模板
├── schemas/
│   ├── adu_schema.py       # ADU 输出 Schema（Pydantic）
│   ├── node_schema.py      # 节点表输出 Schema
│   └── graph_schema.py     # 论证图输出 Schema
├── validators/
│   └── consistency_check.py  # §14 一致性验证
├── utils/
│   ├── api_client.py       # DeepSeek API 封装
│   ├── json_parser.py      # JSON 提取与修复
│   └── message_manager.py  # 对话历史管理
├── app.py               # 命令行入口 / Gradio 界面
├── README.md
└── requirements.txt
```

### 5.2 关键模块说明

| 模块 | 功能 | 关键技术点 |
|------|------|-----------|
| `agent.py` | ReAct 主循环 | 维护 messages 列表；解析 LLM 输出的 Thought/Action；调度工具调用；处理 Token 超限截断 |
| `adu_segmenter.py` | ADU 切分 | 正则预处理（按标点切分）+ LLM 精细切分（关联词触发）；两阶段结合以提高效率 |
| `component_classifier.py` | 组件识别与分类 | 分区处理（P1/Pn 搜 MC，P2-Pn-1 搜段落 Claim）；统摄测试逻辑；判定理由生成 |
| `relation_builder.py` | 关系判定与图构建 | 逐对关系判定；优先级仲裁；Mermaid 代码生成；一致性检查 |
| `consistency_check.py` | 图结构验证 | 连通性检查；孤立节点检测；循环检测；按 §14 规则逐条验证 |
| `api_client.py` | API 调用封装 | DeepSeek 兼容接口；重试机制（网络错误）；流式输出支持（进阶） |
| `message_manager.py` | 上下文管理 | 滑动窗口策略；关键信息保留（MC/段落 Claim 不丢弃）；Token 计数 |

### 5.3 数据流图

<div class="dataflow">

<table class="flow-table">
<tr class="flow-input"><td colspan="3"><strong>输入：</strong>一篇高考议论文 D</td></tr>

<tr><td class="flow-step">Step 1</td>
<td class="flow-module agent">agent.py<br><small>ReAct Loop</small></td>
<td class="flow-desc"><span class="thought">Thought:</span> "需要切分文本" → <span class="action">Action:</span> call Tool 1</td></tr>

<tr><td class="flow-arrow" colspan="3">▼ DeepSeek API</td></tr>

<tr><td class="flow-step">　</td>
<td class="flow-module tool">Tool 1<br><small>ADU Segmenter</small></td>
<td class="flow-desc"><span class="obs">Observation:</span> ADU 列表 {P1_S1, ..., Pn_Sk}<br><small>Prompt: 切分规则 + D</small></td></tr>

<tr><td class="flow-arrow" colspan="3">▼ 返回 agent.py</td></tr>

<tr><td class="flow-step">Step 2</td>
<td class="flow-module agent">agent.py<br><small>ReAct Loop</small></td>
<td class="flow-desc"><span class="thought">Thought:</span> "需要识别 MC 和分类" → <span class="action">Action:</span> call Tool 2<br><small>ADU 列表注入 messages</small></td></tr>

<tr><td class="flow-arrow" colspan="3">▼ DeepSeek API</td></tr>

<tr><td class="flow-step">　</td>
<td class="flow-module tool">Tool 2<br><small>Component Classifier</small></td>
<td class="flow-desc"><span class="obs">Observation:</span> 节点表（含 MC / 段落 Claim / A / E / EA）<br><small>Prompt: 分类规则 + D + ADU 列表</small></td></tr>

<tr><td class="flow-arrow" colspan="3">▼ 返回 agent.py</td></tr>

<tr><td class="flow-step">Step 3</td>
<td class="flow-module agent">agent.py<br><small>ReAct Loop</small></td>
<td class="flow-desc"><span class="thought">Thought:</span> "需要构建关系" → <span class="action">Action:</span> call Tool 3<br><small>节点表注入 messages</small></td></tr>

<tr><td class="flow-arrow" colspan="3">▼ DeepSeek API</td></tr>

<tr><td class="flow-step">　</td>
<td class="flow-module tool">Tool 3<br><small>Relation Builder</small></td>
<td class="flow-desc"><span class="obs">Observation:</span> 边表 + 树状图 + Mermaid 代码<br><small>Prompt: 关系规则 + D + 节点表</small></td></tr>

<tr><td class="flow-arrow" colspan="3">▼ 返回 agent.py</td></tr>

<tr><td class="flow-step">Step 4</td>
<td class="flow-module check">一致性检查<br><small>§14</small></td>
<td class="flow-desc">孤立节点检测 · 循环检测 · 连通性验证</td></tr>

<tr class="flow-output"><td colspan="3"><strong>输出：</strong>完整 Argument Graph（节点表 + 边表 + 树状图 + Mermaid + 总结）</td></tr>
</table>

</div>

---

## 6. 团队分工细节

### 6.1 团队成员与角色

| 姓名 | 学号 | 角色 | 专业背景 | 核心职责 |
|------|------|------|----------|----------|
| 曾栎凝 | 3250102562 | **组长** | 哲学 | 项目规划、文献调研与综述撰写、论证理论指导 |
| 汤明德 | 3250104743 | 组员 | 哲学 | 技术实现（代码开发）、14 节 SOP 制定与形式化编码、Prompt 工程、实验测试 |

### 6.2 具体职责分配

**曾栎凝（组长）**：
1. **全局架构规划**：负责项目的整体设计思路，确保技术实现与论证理论的严格对应
2. **文献调研与综述**：系统检索和梳理论辩挖掘（AM）、论证质量评估（AQ）领域的中英文文献，撰写开题报告中的技术背景调研和文献分析部分
3. **数据收集与标注验证**：收集高考议论文样本（≥10 篇），按 SOP 进行人工标注，作为 Agent 输出的对照基准
4. **实验评估标准制定**：定义评估指标（如节点类型分类准确率、关系分类准确率、整体图结构一致性），建立人工评估流程
5. **实验报告撰写（原理与理论部分）**：撰写报告中的论证理论基础、评估结果分析

**汤明德（组员）**：
1. **SOP 体系制定与形式化**：独立完成 14 节高考议论文 Argument Graph 标注 SOP 的设计与撰写，确保规则的完整性和可操作性
2. **技术架构实现**：从零搭建基于 ReAct 范式的 Agent 框架，实现主循环、工具调用、对话管理模块
3. **三个核心工具的开发**：独立完成 ADU Segmenter、Component Classifier、Relation Builder 的编码、调试和优化
4. **Prompt 工程设计**：设计 System Prompt 和各工具的 Prompt 模板，将 SOP 规则编码为 LLM 可理解的结构化指令
5. **DeepSeek API 对接**：封装 API 调用模块，实现重试机制、JSON 解析与修复、Token 超限处理
6. **一致性验证模块实现**：根据 SOP §14 编写图结构验证逻辑
7. **实验报告撰写（技术部分）**：撰写报告中的系统架构设计、工程实现细节、代码模块说明
8. **可选进阶功能**：在时间和条件允许的情况下，实现 Gradio Web 界面

---

## 7. 任务进度表

本项目规划 4 周（夏六周至夏九周），总工期 2026 年 5 月 31 日 – 6 月 18 日（含开题阶段）。

| 阶段 | 时间 | 主要任务 | 负责人 | 里程碑 / 交付物 |
|------|------|----------|--------|----------------|
| **第一周**（夏六周） | 5.31–6.06 | **环境准备与原理验证** | | |
| | 5.31 | 完成开题报告 | 曾栎凝（主笔）、汤明德（技术部分） | ✅ 开题报告提交 |
| | 6.01–6.02 | 开发环境搭建（Python 虚拟环境、DeepSeek API 注册与测试、Git 仓库初始化） | 汤明德 | 环境就绪，API 连通 |
| | 6.02–6.03 | SOP 规则的形式化编码（将 14 节规则转为 Prompt 可用的结构化描述） | 汤明德 | SOP 编码 v1.0 |
| | 6.03–6.04 | 设计 System Prompt 和 Tool 1 Prompt 初稿 | 汤明德 | Prompt 模板 v0.1 |
| | 6.04–6.06 | 实现 Tool 1（ADU Segmenter）并测试 | 汤明德 | Tool 1 可运行版本 |
| | 6.04–6.06 | 收集高考议论文样本，完成 5 篇人工标注 | 曾栎凝 | 5 篇标注样本 |
| **第二周**（夏七周） | 6.07–6.13 | **核心功能开发** | | |
| | 6.07–6.08 | 基于 Tool 1 测试结果调优切分 Prompt | 汤明德 | Tool 1 调优完成 |
| | 6.07–6.09 | 实现 Agent 主循环（ReAct 框架） | 汤明德 | Agent 核心可运行 |
| | 6.09–6.11 | 实现 Tool 2（Component Classifier）并测试 | 汤明德 | Tool 2 可运行版本 |
| | 6.10–6.11 | 再完成 5 篇人工标注，建立完整对照集 | 曾栎凝 | 10 篇对照集 |
| | 6.11–6.13 | 实现 Tool 3（Relation Builder）并测试 | 汤明德 | Tool 3 可运行版本 |
| **第三周**（夏八周） | 6.14–6.17 | **优化与实验对比** | | |
| | 6.14 | 端到端联调：完整 Agent 流程跑通 5 篇样本 | 汤明德 | 端到端跑通 |
| | 6.14–6.15 | 一致性验证模块实现与调试 | 汤明德 | §14 验证完成 |
| | 6.15–6.16 | 系统化实验：10 篇样本全量运行 Agent，对比人工标注 | 曾栎凝、汤明德 | 实验数据表 |
| | 6.16–6.17 | 误差分析：分类混淆矩阵；Prompt 调优迭代 | 曾栎凝（分析）、汤明德（调优） | 优化版 Agent |
| **第四周**（夏九周） | 6.17–6.18 | **结项与交付** | | |
| | 6.17 | 撰写实验报告（论证理论 + 技术实现 + 实验结果 + 误差分析） | 曾栎凝（理论部分）、汤明德（技术部分） | 实验报告初稿 |
| | 6.17 | 截取多步调用对话日志，制作 Demo 截图 | 汤明德 | Demo 素材 |
| | 6.17 | 制作答辩 PPT / Markdown | 曾栎凝（PPT）、汤明德（技术图表） | 答辩材料 |
| | 6.18 | 代码整理、注释补充、README 撰写 | 汤明德 | 代码打包 |
| | 6.18 | 全部材料终审、打包提交 | 曾栎凝 | ✅ 压缩包提交 |

**注**：以上计划对两名哲学系学生而言较为紧凑，但得益于 AI 辅助编程（WorkBuddy），代码实现效率可显著提升。

---

## 8. 可行性分析

### 8.1 技术可行性

| 风险因素 | 影响程度 | 应对策略 |
|----------|----------|----------|
| DeepSeek API 响应不稳定 | 中 | 实现自动重试（最多 3 次）+ 指数退避；缓存已成功的调用结果 |
| LLM 输出格式不符预期（JSON 格式错误） | 高 | 实现鲁棒的 JSON 提取器（支持 Markdown code block 包裹、多余逗号修复）；Pydantic 验证 + 降级策略 |
| 长文本超出 Token 限制 | 中 | DeepSeek-v3 支持 128K 上下文，800 字议论文仅约 2000 token，裕度充足 |
| SOP 规则在 Prompt 中表述不清导致 LLM 行为不稳定 | 高 | 将复杂规则拆分为 Few-shot 示例；关键规则在 System Prompt 和 Tool Prompt 中双重嵌入 |
| 论辩关系的下意识判断不准确 | 中 | 在判定理由中要求 LLM 明确引用文本依据；不一致时向用户展示置信度 |

### 8.2 学术可行性

- **SOP 体系已成熟**：14 节 SOP 经过详细设计，规则明确，可操作性高
- **文献支撑充分**：Wachsmuth et al.（2017a）的分类体系、Das et al.（2025）的标记词方法、Ivanova et al.（2024）的综述为技术方案提供了坚实的学术基础
- **中文议论文的 AM 研究尚属空白**：现有 AM 数据集和系统几乎全为英文，本项目在中文议论文上的探索具有学术价值和创新性

### 8.3 资源可行性

- **DeepSeek API 费用**：按 10 篇样本 × 每篇 3 次 API 调用 × 2000 token 计算，总消耗约 60K token，按 DeepSeek 价格（输入 ¥1/百万 token，输出 ¥2/百万 token），总费用 < ¥1，成本可忽略
- **计算资源**：仅需 API 调用，无需本地 GPU，任何笔记本电脑即可完成开发
- **时间资源**：4 周工期对两名学生的课程项目而言合理紧凑

### 8.4 团队可行性

本团队的特殊优势在于两名成员均为哲学专业背景，对论证理论（Toulmin 模型、Walton 论证型式、非形式逻辑的 RSA 三角）具有系统的学术训练。这使得 SOP 规则的制定和优化具有扎实的理论根基——而非仅仅依赖工程直觉。同时，AI 编程助手（WorkBuddy）可大幅降低代码实现的技术门槛。

---

## 9. 预期成果与交付物

### 9.1 基本要求（必须完成）

| 序号 | 交付物 | 对应作业要求 |
|------|--------|-------------|
| 1 | 可运行的 Python 代码（ArgGraph-Agent） | 选题一：提交代码 |
| 2 | 至少 3 个工具（ADU Segmenter / Component Classifier / Relation Builder） | 选题一：至少实现 3 个工具 |
| 3 | 多步调用 Demo：输入一篇议论文 → Agent 自动完成切分→分类→建图→输出 Argument Graph | 选题一：完成多步调用任务 |
| 4 | Demo 截图 / 对话日志（至少 5 步交互） | 选题一：提交 demo 视频或对话截图 |
| 5 | 完整的实验报告（含 Agent 决策闭环流程图、ReAct Prompt 模板、论证图输出示例） | 选题一 + 大作业统一要求 |

### 9.2 进阶目标（加分项）

| 序号 | 功能 | 说明 |
|------|------|------|
| 1 | **Gradio Web 界面** | 用户可直接粘贴议论文文本，点击"分析"，即时查看 Argument Graph 的交互式展示（节点表 + 边表 + Mermaid 图渲染） |
| 2 | **流式输出** | 在 Web 界面中实时展示 Agent 的思考过程（Thought → Action → Observation 逐步可见） |
| 3 | **短期记忆机制** | 对同一篇议论文的多轮优化请求（如"把 P2_E1 和 P2_C 的关系改为 attack"），Agent 能基于之前的分析结果进行调整，而不必从头分析 |

### 9.3 最终提交包结构

```
选题一-曾栎凝-3250102562/
├── 源代码/
│   ├── agent.py
│   ├── tools/
│   │   ├── adu_segmenter.py
│   │   ├── component_classifier.py
│   │   └── relation_builder.py
│   ├── prompts/
│   ├── schemas/
│   ├── validators/
│   ├── utils/
│   ├── app.py                # 命令行入口
│   └── app_gradio.py         # Gradio 界面（进阶）
├── 实验报告.pdf
├── Demo截图/
│   ├── step1_segmentation.png
│   ├── step2_classification.png
│   ├── step3_graph.png
│   └── final_output.png
├── 答辩PPT.pptx
└── README.md
```

---

## 10. 参考文献

[1] Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y. (2023). ReAct: Synergizing Reasoning and Acting in Language Models. *International Conference on Learning Representations (ICLR)*.

[2] Wachsmuth, H., Naderi, N., Hou, Y., Bilu, Y., Prabhakaran, V., Thijm, T. A., Hirst, G., & Stein, B. (2017a). Computational Argumentation Quality Assessment in Natural Language. *Proceedings of the 15th Conference of the European Chapter of the Association for Computational Linguistics (EACL)*, 176–187.

[3] Ivanova, R. V., Huber, T., & Niklaus, C. (2024). Let's discuss! Quality Dimensions and Annotated Datasets for Computational Argument Quality Assessment. *Proceedings of the 2024 Conference on Empirical Methods in Natural Language Processing (EMNLP)*, 20749–20779.

[4] Das, N., Choudhary, V., Saradhi, V. V., & Anand, A. (2025). Exploration of Marker-Based Approaches in Argument Mining through Augmented Natural Language. *Proceedings of the International Joint Conference on Neural Networks (IJCNN 2025)*.

[5] Persing, I., & Ng, V. (2015). Modeling Argument Strength in Student Essays. *Proceedings of the 53rd Annual Meeting of the Association for Computational Linguistics and the 7th International Joint Conference on Natural Language Processing (ACL-IJCNLP)*, 543–552.

[6] Stab, C., & Gurevych, I. (2017). Parsing Argumentation Structures in Persuasive Essays. *Computational Linguistics*, 43(3), 619–659.

[7] Blair, J. A. (2012). *Groundwork in the Theory of Argumentation*. Springer.

[8] Walton, D., Reed, C., & Macagno, F. (2008). *Argumentation Schemes*. Cambridge University Press.

[9] Toulmin, S. E. (1958). *The Uses of Argument*. Cambridge University Press.

[10] Eemeren, F. H. van, Grootendorst, R., & Henkemans, F. S. (1996). *Fundamentals of Argumentation Theory: A Handbook of Historical Backgrounds and Contemporary Developments*. Routledge.

[11] Wu, Q., Bansal, G., Zhang, J., Wu, Y., Li, B., Zhu, E., ... & Wang, C. (2023). AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation. *arXiv:2308.08155*.

[12] Hong, S., Zheng, X., Chen, J., Cheng, Y., Wang, J., Zhang, C., ... & Wu, C. (2023). MetaGPT: Meta Programming for Multi-Agent Collaborative Framework. *arXiv:2308.00352*.

[13] Lauscher, A., Ng, L., Napoles, C., & Tetreault, J. (2020). Rhetoric, Logic, and Dialectic: Advancing Theory-based Argument Quality Assessment in Natural Language Processing. *Proceedings of the 28th International Conference on Computational Linguistics (COLING 2020)*, 4553–4574.

[14] Yang, H., He, Y., Bu, X., Xu, H., & Guo, W. (2023). Automatic Essay Evaluation Technologies in Chinese Writing—A Systematic Literature Review. *Applied Sciences*, 13(19), 10737.

[15] Chang, T.-H., & Sung, Y.-T. (2019). SmartWriting-Mandarin: An Automated Essay Scoring System for Chinese as a Foreign Language Learners. In *The Routledge International Handbook of Automated Essay Evaluation* (Chapter 6). Routledge.

[16] Peldszus, A., & Stede, M. (2013). From Argument Diagrams to Argumentation Mining in Texts: A Survey. *International Journal of Cognitive Informatics and Natural Intelligence*, 7(1), 1–31.

[17] Ren, Y., Wu, H., Long, Z., Zhao, S., Zhou, X., Yin, Z., Zhuang, X., Bai, X., & Lan, M. (2024). CEAMC: Corpus and Empirical Study of Argument Analysis in Education via LLMs. *Findings of the Association for Computational Linguistics: EMNLP 2024*, 6964–6978.

[18] 佟威, 赵静宇. (2020). 高考语文写作整体评分与分项评分的实证研究. 《中国考试》, 2020(3), 6–12.

[19] Stede, M., & Schneider, J. (2018). *Argumentation Mining*. Synthesis Lectures on Human Language Technologies. Morgan & Claypool.

---

*本报告由曾栎凝与汤明德共同撰写，AI 编程助手（WorkBuddy）辅助文献检索与技术方案设计。*
