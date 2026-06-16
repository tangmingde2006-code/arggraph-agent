#!/usr/bin/env python3
"""批量运行 agent 分析多篇作文，并汇总结果。"""

import sys, json, time
from pathlib import Path

# 添加上级目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import ArgumentGraphAgent
from tools.graphviz_render import render as render_graphviz


def main():
    sample_dir = Path(__file__).parent.parent / "samples/sh_gaokao"
    output_dir = Path(__file__).parent.parent / "outputs/sh_gaokao"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 选择 4 篇代表性作文（不同年份、不同结构）
    target_files = [
        "2018_请理性看待_被需要.txt",
        "2019_万种风烟过眼后.txt",
        "2023_探索世界_步履不停.txt",
        "2025_专传之转_何须转.txt",
    ]

    results = []
    total_start = time.time()

    for i, fname in enumerate(target_files):
        fpath = sample_dir / fname
        if not fpath.exists():
            print(f"⚠️ 跳过不存在的文件: {fname}")
            continue

        essay_text = fpath.read_text(encoding='utf-8')
        title = fname.replace('.txt', '')

        print(f"\n{'='*80}")
        print(f"📝 [{i+1}/{len(target_files)}] {title}")
        print(f"   字数: {len(essay_text.replace(chr(10), ''))}")
        print(f"{'='*80}")

        start = time.time()

        try:
            agent = ArgumentGraphAgent()
            result = agent.analyze(essay_text=essay_text)

            elapsed = time.time() - start
            print(f"   ⏱ 耗时: {elapsed:.1f}s")

            # 提取关键指标
            graph = result.get("graph", {})
            nodes = graph.get("node_table", [])
            edges = graph.get("edge_table", [])
            consistency = graph.get("consistency_check", {})
            steps = result.get("total_steps", result.get("react_trace_steps", len(result.get("call_history", []))))

            summary = {
                "title": title,
                "year": fname.split('_')[0],
                "word_count": len(essay_text.replace('\n', '')),
                "nodes": len(nodes),
                "edges": len(edges),
                "steps": steps,
                "time": round(elapsed, 1),
                "mc": "",
                "consistency_passed": consistency.get("all_claims_connected_to_mc", False),
                "orphans": consistency.get("orphan_nodes", []),
                "cycles": consistency.get("cycles_detected", False),
            }

            # 提取 MC
            for n in nodes:
                if n.get("type") == "major_claim":
                    summary["mc"] = n["text"][:60] + ("..." if len(n["text"]) > 60 else "")
                    break

            # 保存结果 JSON
            out_json = output_dir / f"{title}.json"
            out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding='utf-8')

            # 渲染 Graphviz 图
            try:
                graph_out = output_dir / f"{title}"
                graph_out.mkdir(exist_ok=True)
                dot_str = render_graphviz(result, graph_out, formats=("png",))
                summary["graph_png"] = str(graph_out / "arg_graph.png")
            except Exception as e:
                print(f"   ⚠️ Graphviz 渲染失败: {e}")
                summary["graph_png"] = ""

            results.append(summary)

            # 打印本份摘要
            print(f"   📊 节点: {len(nodes)} | 边: {len(edges)} | ReAct轮: {steps}")
            print(f"   🎯 MC: {summary['mc']}")
            print(f"   ✅ 一致性: {'通过' if summary['consistency_passed'] else '⚠️ 有问题'}")

        except Exception as e:
            elapsed = time.time() - start
            print(f"   ❌ 失败 ({elapsed:.1f}s): {e}")
            results.append({
                "title": title, "year": fname.split('_')[0],
                "error": str(e), "time": round(elapsed, 1)
            })

    # ===== 汇总报告 =====
    total_elapsed = time.time() - total_start
    print(f"\n{'='*80}")
    print(f"📊 批量分析汇总 ({len(results)}篇, 总耗时 {total_elapsed:.0f}s)")
    print(f"{'='*80}")

    successful = [r for r in results if "error" not in r]
    failed = [r for r in results if "error" in r]

    for r in results:
        if "error" in r:
            print(f"  ❌ [{r['year']}] {r['title']} — {r['error']}")
        else:
            status = "✅" if r["consistency_passed"] else "⚠️"
            print(f"  {status} [{r['year']}] {r['title']}: {r['nodes']}节点/{r['edges']}边/{r['steps']}轮 — \"{r['mc'][:40]}...\"")

    # 保存汇总 JSON
    summary_path = output_dir / "_summary.json"
    summary_path.write_text(json.dumps({
        "total": len(results),
        "successful": len(successful),
        "failed": len(failed),
        "total_time": round(total_elapsed, 1),
        "results": results,
    }, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f"\n📁 汇总: {summary_path}")
    print(f"📁 详细结果: {output_dir}/")
    return results


if __name__ == "__main__":
    main()
