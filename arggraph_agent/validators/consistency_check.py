"""一致性检查模块（§14）

验证论证图的结构完整性：
1. 每个 Pn_C 是否连接到 MC
2. 每个 E 是否连接到某个 C
3. 每个 EA 是否连接到 E 或 C
4. 是否有孤立节点（入度和出度均为 0）
5. 是否有循环
"""

from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict


def _build_adjacency(edge_table: List[Dict[str, Any]]) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
    """从边表构建邻接表。"""
    out_edges = defaultdict(set)
    in_edges = defaultdict(set)
    for edge in edge_table:
        src = edge.get("from", edge.get("source", ""))
        tgt = edge.get("to", edge.get("target", ""))
        if src and tgt:
            out_edges[src].add(tgt)
            in_edges[tgt].add(src)
    return dict(out_edges), dict(in_edges)


def _can_reach(start: str, target: str, out_edges: Dict[str, Set[str]], visited: Set[str] = None) -> bool:
    """检查从 start 是否能通过有向边到达 target（BFS）"""
    if visited is None:
        visited = set()
    if start in visited:
        return False
    visited.add(start)
    if target in out_edges.get(start, set()):
        return True
    for nb in out_edges.get(start, set()):
        if _can_reach(nb, target, out_edges, visited):
            return True
    return False


def check_claims_to_mc(node_table: List[Dict], edge_table: List[Dict]) -> Tuple[bool, List[str]]:
    """检查段落 Claim 是否全部连接到 MC"""
    out_edges, _ = _build_adjacency(edge_table)
    claims = [n["node_id"] for n in node_table if n.get("type") == "paragraph_claim"]
    unconnected = [c for c in claims if not _can_reach(c, "MC", out_edges)]
    return len(unconnected) == 0, unconnected


def check_evidence_connected(node_table: List[Dict], edge_table: List[Dict]) -> Tuple[bool, List[str]]:
    """检查 Evidence/EA 是否连接到某个 Claim"""
    out_edges, _ = _build_adjacency(edge_table)
    claim_ids = {n["node_id"] for n in node_table if n.get("type") in ("paragraph_claim", "major_claim")}
    ev_ids = [n["node_id"] for n in node_table if n.get("type") in ("evidence", "evidence_analysis")]

    unconnected = []
    for ev in ev_ids:
        targets = out_edges.get(ev, set())
        if not any(_can_reach(ev, cid, out_edges) for cid in claim_ids):
            unconnected.append(ev)
    return len(unconnected) == 0, unconnected


def find_orphans(node_table: List[Dict], edge_table: List[Dict]) -> List[str]:
    """查找孤立节点（出入度均为 0）"""
    out_edges, in_edges = _build_adjacency(edge_table)
    all_ids = {n["node_id"] for n in node_table}
    return [nid for nid in all_ids if len(out_edges.get(nid, set())) == 0 and len(in_edges.get(nid, set())) == 0]


def detect_cycles(edge_table: List[Dict]) -> Tuple[bool, List[List[str]]]:
    """DFS 三色标记法检测有向环"""
    out_edges, _ = _build_adjacency(edge_table)
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {}
    cycles = []

    def dfs(node: str, path: List[str]):
        color[node] = GRAY
        path.append(node)
        for nb in out_edges.get(node, set()):
            cc = color.get(nb, WHITE)
            if cc == GRAY:
                start = path.index(nb)
                cycles.append(path[start:] + [nb])
            elif cc == WHITE:
                dfs(nb, path)
        path.pop()
        color[node] = BLACK

    all_nodes = set(out_edges.keys())
    for e in edge_table:
        tgt = e.get("to", e.get("target", ""))
        if tgt:
            all_nodes.add(tgt)

    for node in all_nodes:
        if isinstance(node, str) and color.get(node, WHITE) == WHITE:
            dfs(node, [])

    return len(cycles) > 0, cycles


def run_consistency_check(node_table: List[Dict], edge_table: List[Dict]) -> Dict[str, Any]:
    """运行 §14 完整一致性检查"""
    claims_ok, uc = check_claims_to_mc(node_table, edge_table)
    ev_ok, ue = check_evidence_connected(node_table, edge_table)
    orphans = find_orphans(node_table, edge_table)
    has_cycles, cycles = detect_cycles(edge_table)

    issues = []
    if not claims_ok:
        issues.append(f"未连接 MC 的段落 Claim: {uc}")
    if not ev_ok:
        issues.append(f"未连接 Claim 的 Evidence/EA: {ue}")
    if orphans:
        issues.append(f"孤立节点: {orphans}")
    if has_cycles:
        issues.append(f"检测到循环: {cycles}")

    return {
        "all_claims_connected_to_mc": claims_ok,
        "all_evidence_connected": ev_ok,
        "orphan_nodes": orphans,
        "cycles_detected": has_cycles,
        "cycles": cycles if has_cycles else [],
        "passed": len(issues) == 0,
        "issues": issues,
    }
