#!/usr/bin/env python3
"""
用 Graphviz 生成学术论文级论证图。

读取 result JSON，生成 DOT 文件并渲染为 PNG/SVG/PDF。
节点类型五色编码，关系类型多色边线，支持图例。
"""

import json
import subprocess
import sys
from pathlib import Path

# ===================== 样式配置 =====================

# 节点类型配色（柔和的学术色调）
NODE_STYLES = {
    "major_claim":        {"fill": "#FFD700", "font": "#222222", "border": "#DAA520", "label": "MC·中心论点"},
    "paragraph_claim":    {"fill": "#B3D9FF", "font": "#1a1a2e", "border": "#4A90D9", "label": "Claim·段落主张"},
    "analysis":           {"fill": "#C8F7C5", "font": "#1b5e20", "border": "#4CAF50", "label": "A·分析"},
    "evidence":           {"fill": "#FFE0B2", "font": "#e65100", "border": "#FB8C00", "label": "E·论据"},
    "evidence_analysis":  {"fill": "#E8D1F0", "font": "#4a148c", "border": "#9C27B0", "label": "EA·论据分析"},
}

# 关系类型配色
EDGE_STYLES = {
    "support":     {"color": "#2E7D32", "style": "solid",  "penwidth": 2.0, "label": "支持"},
    "attack":      {"color": "#C62828", "style": "dashed", "penwidth": 2.0, "label": "反驳"},
    "example-of":  {"color": "#E65100", "style": "dotted", "penwidth": 1.5, "label": "例证"},
    "explain":     {"color": "#1565C0", "style": "solid",  "penwidth": 1.5, "label": "解释"},
    "extend":      {"color": "#6A1B9A", "style": "dashed", "penwidth": 1.5, "label": "延伸"},
    "parallel":    {"color": "#546E7A", "style": "dotted", "penwidth": 1.0, "label": "并列"},
    "include":     {"color": "#00838F", "style": "solid",  "penwidth": 1.0, "label": "包含"},
}


def truncate(text: str, max_len: int = 40) -> str:
    """截断文本用于节点标签"""
    text = text.replace('"', "'").replace("\n", " ").strip()
    if len(text) > max_len:
        return text[:max_len] + "…"
    return text


def escape_dot(text: str) -> str:
    """转义 DOT 中的特殊字符"""
    return text.replace('"', '\\"').replace("\n", " ")


def build_dot(data: dict, output_dir: Path, title: str = "") -> str:
    """从 result JSON 构建 DOT 字符串"""
    graph = data.get("graph", {})
    nodes = graph.get("node_table", [])
    edges = graph.get("edge_table", [])

    # 从数据中动态获取标题
    if not title:
        essay_topic = (data.get("input", {}) or {}).get("essay_topic", "")
        if essay_topic and essay_topic != "（无）":
            title = essay_topic
        else:
            # 从 MC 文本提取标题
            for n in nodes:
                if n.get("type") == "major_claim":
                    title = n.get("text", "")[:20]
                    break
    if not title:
        title = "论证结构图"

    lines = []
    lines.append('digraph ArgumentGraph {')
    lines.append('  // ===== 全局样式 =====')
    lines.append('  rankdir=TB;')
    lines.append('  bgcolor="#ffffff";')
    lines.append('  fontname="Arial";')
    lines.append('  fontsize=14;')
    lines.append(f'  label="论证结构图：{title}";')
    lines.append('  labelloc=t;')
    lines.append('  fontsize=18;')
    lines.append('  fontcolor="#1a1a2e";')
    lines.append('  nodesep=0.5;')
    lines.append('  ranksep=1.0;')
    lines.append('  splines=polyline;')
    lines.append('  newrank=true;')
    lines.append('')
    lines.append('  // 默认节点样式')
    lines.append('  node [shape=box, style="rounded,filled", fontname="Arial", fontsize=10, margin="0.15,0.1"];')
    lines.append('  edge [fontname="Arial", fontsize=9, arrowsize=0.8];')
    lines.append('')

    # ===== 节点定义 =====
    lines.append('  // ===== 节点 =====')
    node_map = {}
    for n in nodes:
        nid = n["node_id"]
        ntype = n["type"]
        text = truncate(n["text"], 50)
        style = NODE_STYLES.get(ntype, NODE_STYLES["analysis"])

        # 短别名（去下划线，更可读）
        short_id = nid.replace("_", "")
        node_map[nid] = short_id

        # 标签：两行，第一行节点ID，第二行文本
        label = f"{nid}\\n{text}"
        lines.append(f'  {short_id} [')
        lines.append(f'    label="{escape_dot(label)}",')
        lines.append(f'    fillcolor="{style["fill"]}",')
        lines.append(f'    fontcolor="{style["font"]}",')
        lines.append(f'    color="{style["border"]}",')
        lines.append(f'    penwidth=1.5')
        lines.append(f'  ];')

    lines.append('')

    # ===== 边定义 =====
    lines.append('  // ===== 关系边 =====')
    for e in edges:
        frm = node_map.get(e["from"], e["from"].replace("_", ""))
        to = node_map.get(e["to"], e["to"].replace("_", ""))
        rel = e["relation"]
        style = EDGE_STYLES.get(rel, EDGE_STYLES["support"])

        lines.append(f'  {frm} -> {to} [')
        lines.append(f'    label="{style["label"]}",')
        lines.append(f'    color="{style["color"]}",')
        lines.append(f'    style="{style["style"]}",')
        lines.append(f'    penwidth={style["penwidth"]},')
        lines.append(f'    fontcolor="{style["color"]}"];')

    lines.append('')

    # ===== 图例（用 subgraph） =====
    lines.append('  // ===== 图例 =====')
    lines.append('  subgraph cluster_legend {')
    lines.append('    label="图例";')
    lines.append('    fontsize=12;')
    lines.append('    fontname="Arial";')
    lines.append('    fontcolor="#555555";')
    lines.append('    style="rounded,dashed";')
    lines.append('    color="#aaaaaa";')
    lines.append('    bgcolor="#fafafa";')
    lines.append('')

    # 节点图例
    for i, (ntype, ns) in enumerate(NODE_STYLES.items()):
        lines.append(f'    legend_node_{i} [label="{ns["label"]}", fillcolor="{ns["fill"]}", fontcolor="{ns["font"]}", color="{ns["border"]}", shape=box, style="rounded,filled", fontsize=9];')
    lines.append('')

    # 关系图例（用不可见节点+边）
    for i, (rel, es) in enumerate(EDGE_STYLES.items()):
        a_id = f"legend_edge_a_{i}"
        b_id = f"legend_edge_b_{i}"
        lines.append(f'    {a_id} [label="", width=0.01, height=0.01, shape=point, style=invis];')
        lines.append(f'    {b_id} [label="", width=0.01, height=0.01, shape=point, style=invis];')
        lines.append(f'    {a_id} -> {b_id} [label="{es["label"]}", color="{es["color"]}", style="{es["style"]}", penwidth={es["penwidth"]}, fontcolor="{es["color"]}", fontsize=9];')

    lines.append('  }')
    lines.append('')

    # ===== 层级约束：从节点数据动态生成 =====
    lines.append('  // ===== 层级约束（从数据动态生成）=====')
    # MC 放最顶层
    lines.append('  { rank=source; MC; }')
    # 段落主张同级
    claim_nodes = [node_map[n["node_id"]] for n in nodes if n.get("type") == "paragraph_claim"]
    if claim_nodes:
        lines.append(f'  {{ rank=same; {"; ".join(claim_nodes)}; }}')
    # 末段分析/总结放最底层
    last_para = max((int(n["node_id"].split("_")[0][1:]) for n in nodes if n["node_id"].startswith("P") and n["node_id"][1:].split("_")[0].isdigit()), default=5)
    sink_nodes = [node_map[n["node_id"]] for n in nodes if n.get("type") in ("analysis", "evidence_analysis") and n["node_id"].startswith(f"P{last_para}")]
    if sink_nodes:
        lines.append(f'  {{ rank=sink; {"; ".join(sink_nodes)}; }}')

    lines.append('}')
    return "\n".join(lines)


def _find_dot() -> str:
    """查找 Graphviz dot 命令路径（跨平台）"""
    import shutil
    # 优先使用系统 PATH 中的 dot
    dot_path = shutil.which("dot")
    if dot_path:
        return dot_path
    # macOS Homebrew 常见路径
    for candidate in ["/opt/homebrew/bin/dot", "/usr/local/bin/dot"]:
        if Path(candidate).exists():
            return candidate
    raise RuntimeError("未找到 Graphviz dot 命令。请安装 Graphviz: brew install graphviz (macOS) 或 apt install graphviz (Linux)")


def render(result_path: Path, output_dir: Path, formats=("png", "svg", "pdf")):
    """读取 JSON，生成 DOT，渲染为指定格式"""
    try:
        with open(result_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        raise RuntimeError(f"无法读取结果文件 {result_path}: {e}")

    dot_str = build_dot(data, output_dir)
    dot_path = output_dir / "arg_graph.dot"
    dot_path.write_text(dot_str, encoding="utf-8")

    print(f"[DOT] 已生成: {dot_path}  ({len(dot_str)} 字符)")

    dot_bin = _find_dot()
    for fmt in formats:
        out_path = output_dir / f"arg_graph.{fmt}"
        cmd = [dot_bin, f"-T{fmt}", str(dot_path), "-o", str(out_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"[{fmt.upper()}] 已生成: {out_path}  ({out_path.stat().st_size:,} bytes)")
        else:
            msg = f"[{fmt.upper()}] 渲染失败: {result.stderr.strip()}"
            print(msg)
            raise RuntimeError(msg)

    return dot_str


if __name__ == "__main__":
    result_file = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent / "outputs/result_20260616_081056.json"
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else result_file.parent

    render(result_file, out_dir)
    print("\n✅ 论证图渲染完成")
