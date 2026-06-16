# 🔍 ArgGraph-Agent

**高考议论文论证结构自动拆解智能体**

基于 ReAct（Reasoning + Acting）范式，调用 DeepSeek API，自动将高考议论文拆解为论证单元（ADU），分类为 MC（中心论点）、Claim（段落主张）、Analysis（分析）、Evidence（论据）、Evidence-Analysis（论据分析），并构建论证关系图。

> 浙江大学「人工智能基础」大作业项目

---

## 🧠 核心架构

```
用户输入作文 → ReAct 循环 ↓
  🧠 Thought → 🔧 Action → 👁 Observation → 🧠 Thought → ...
                                  ↓
  三步工具链：ADU 切分 → 组件分类 → 关系图构建 → 一致性检查
                                  ↓
  输出：节点表 + 边表 + 论证树 + 论证关系图 + 总结
```

## 🛠 可用工具

| 工具 | 功能 | 依赖 |
|------|------|------|
| `adu_segmenter` | 切分议论文为论证单元 | 无 |
| `component_classifier` | 对 ADU 进行组件分类（MC/C/A/E/EA） | adu_segmenter |
| `relation_builder` | 构建论证关系图（边表+树+Mermaid） | component_classifier |
| `consistency_check` | 本地图算法一致性验证 | relation_builder |

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r arggraph_agent/requirements.txt
```

### 2. 配置 API Key

```bash
# 在 arggraph_agent/ 目录下创建 .env 文件
echo "DEEPSEEK_API_KEY=sk-your-key-here" > arggraph_agent/.env
```

### 3. 运行

**Web 界面（推荐）：**
```bash
python -m arggraph_agent.app_web
# 打开 http://localhost:5001
```

**终端演示：**
```bash
python -m arggraph_agent.app --demo
```

**直接分析文本：**
```bash
python -m arggraph_agent.app --text "你的议论文全文" --topic "作文题目"
```

**从文件读取：**
```bash
python -m arggraph_agent.app --file samples/sh_gaokao/2019_万种风烟过眼后.txt
```

## 📂 项目结构

```
arggraph_agent/
├── agent.py              # ReAct 主循环
├── app.py                # 终端 CLI 入口
├── app_web.py            # Flask Web 界面
├── requirements.txt      # 依赖
├── .env.example          # 环境变量模板
├── tools/                # 三步工具链
│   ├── adu_segmenter.py
│   ├── component_classifier.py
│   ├── relation_builder.py
│   └── graphviz_render.py
├── validators/           # 一致性检查
├── utils/                # API 客户端
├── prompts/              # Prompt 模板
├── schemas/              # 数据 schema
└── samples/              # 示例作文
```

## 📊 内置范例

2019 年上海高考真题《万种风烟过眼后》· 一类上 70 分

## ⚙️ 技术栈

- **LLM**: DeepSeek Chat API
- **范式**: ReAct (Reasoning + Acting)
- **Web**: Flask + 纯 JS SVG 渲染
- **验证**: 图算法一致性检查（BFS 连通性 + 环检测）

## 📄 License

MIT
