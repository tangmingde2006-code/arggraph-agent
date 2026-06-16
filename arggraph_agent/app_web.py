#!/usr/bin/env python3
"""ArgGraph-Agent Web 界面

在浏览器中运行，粘贴议论文即可可视化分析。

用法：
    python app_web.py
    然后打开 http://localhost:5000
"""

import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template_string, request, jsonify
from arggraph_agent.agent import create_agent

app = Flask(__name__)
agent = create_agent()

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ArgGraph-Agent | 高考议论文论证结构分析</title>
<!-- Mermaid 异步加载，不阻塞页面 -->
<style>
  :root {
    --bg: #f5f6fa; --card: #fff; --text: #222; --muted: #666;
    --blue: #2E75B6; --green: #27ae60; --red: #e74c3c; --orange: #e67e22;
    --border: #e0e0e0;
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family:"PingFang SC","Microsoft YaHei","Helvetica Neue",sans-serif; background:var(--bg); color:var(--text); line-height:1.7; }
  .container { max-width:960px; margin:0 auto; padding:24px 16px 60px; }
  header { text-align:center; padding:32px 0 24px; }
  header h1 { font-size:26px; color:var(--blue); letter-spacing:1px; }
  header p { color:var(--muted); font-size:14px; margin-top:4px; }

  .card { background:var(--card); border-radius:12px; box-shadow:0 2px 12px rgba(0,0,0,0.06); padding:24px; margin-bottom:20px; }

  textarea { width:100%; min-height:200px; border:1.5px solid var(--border); border-radius:8px; padding:14px; font-size:14px; font-family:inherit; line-height:1.8; resize:vertical; transition:border-color .2s; }
  textarea:focus { outline:none; border-color:var(--blue); }
  .row { display:flex; gap:12px; align-items:center; }
  .row input { flex:1; border:1.5px solid var(--border); border-radius:8px; padding:10px 14px; font-size:14px; font-family:inherit; }
  .row input:focus { outline:none; border-color:var(--blue); }

  .btn { display:inline-flex; align-items:center; gap:6px; background:var(--blue); color:#fff; border:none; border-radius:8px; padding:10px 28px; font-size:15px; font-weight:600; cursor:pointer; transition:background .2s,transform .1s; }
  .btn:hover { background:#1a5f96; transform:translateY(-1px); }
  .btn:active { transform:translateY(0); }
  .btn:disabled { opacity:0.6; cursor:not-allowed; transform:none; }
  .btn-bar { display:flex; gap:10px; margin-top:16px; flex-wrap:wrap; }

  .demo-btn { background:#fff; color:var(--blue); border:1.5px solid var(--blue); }
  .demo-btn:hover { background:#f0f6fb; }

  .spinner { display:inline-block; width:18px; height:18px; border:2.5px solid rgba(255,255,255,.3); border-top-color:#fff; border-radius:50%; animation:spin .7s linear infinite; }
  @keyframes spin { to { transform:rotate(360deg); } }

  .result { display:none; }
  .result.show { display:block; }

  .section-title { font-size:18px; font-weight:700; color:var(--blue); margin-bottom:12px; padding-bottom:6px; border-bottom:2px solid #d5e8f0; }
  .section-title .icon { margin-right:6px; }

  table { width:100%; border-collapse:collapse; margin:12px 0; font-size:13px; }
  th, td { border:1px solid #e0e0e0; padding:8px 10px; text-align:left; vertical-align:top; }
  th { background:#d5e8f0; font-weight:600; font-size:12px; }
  tr:hover { background:#fafcfd; }

  .badge { display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600; color:#fff; }
  .badge-mc { background:var(--red); }
  .badge-claim { background:var(--blue); }
  .badge-analysis { background:var(--green); }
  .badge-evidence { background:var(--orange); }
  .badge-ea { background:#8e44ad; }

  .tree-box { background:#f8f9fb; border:1px solid var(--border); border-radius:8px; padding:16px; font-family:"SF Mono","Consolas","Menlo",monospace; font-size:12px; line-height:1.7; white-space:pre-wrap; word-break:break-all; overflow-x:auto; margin:12px 0; }
  .mermaid-box { background:#fff; border:1px solid var(--border); border-radius:8px; padding:20px; margin:12px 0; overflow-x:auto; display:flex; justify-content:center; }

  .check-pass { color:var(--green); font-weight:600; }
  .check-fail { color:var(--red); font-weight:600; }
  .check-item { padding:4px 0; font-size:14px; }
  .issue { color:var(--orange); padding:4px 12px; }

  .summary-box { background:#f0f6fb; border-left:4px solid var(--blue); padding:14px 18px; border-radius:0 8px 8px 0; margin:12px 0; font-size:14px; line-height:1.8; }

  .error-box { background:#fef2f2; border:1px solid #fecaca; border-radius:8px; padding:16px; color:var(--red); margin:12px 0; }
  .empty-hint { text-align:center; color:var(--muted); padding:40px 0; font-size:14px; }

  .stats-row { display:flex; gap:12px; flex-wrap:wrap; margin:12px 0; }
  .stat { background:#f0f6fb; border-radius:8px; padding:12px 16px; text-align:center; min-width:80px; }
  .stat .num { font-size:24px; font-weight:700; color:var(--blue); }
  .stat .label { font-size:11px; color:var(--muted); margin-top:2px; }
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>🔍 ArgGraph-Agent</h1>
    <p>高考议论文论证结构自动拆解智能体 &nbsp;|&nbsp; ReAct + LLM 三步工具链</p>
  </header>

  <!-- 输入区 -->
  <div class="card">
    <textarea id="essay" placeholder="在此粘贴高考议论文全文……"></textarea>
    <div class="row" style="margin-top:12px;">
      <input id="topic" placeholder="作文题目（可选，如「2019年上海秋考·中国味」）">
    </div>
    <div class="btn-bar">
      <button class="btn" id="analyzeBtn" onclick="analyze()">🚀 开始分析</button>
      <button class="btn demo-btn" id="demoBtn" onclick="loadDemo()">📄 加载内置范例</button>
      <span style="font-size:12px;color:var(--muted);margin-left:8px;">2019 上海高考真题《万种风烟过眼后》· 一类上 70 分</span>
    </div>
  </div>

  <!-- 结果区 -->
  <div class="result" id="result">
    <!-- 动态填充 -->
  </div>
</div>

<script>
const DEMO_ESSAY = `记得歌里唱道："若非万种飞烟都过眼， 怎会迷恋巫山的那一片。"言甚是，若不曾含英咀华，怎能找到心中真正认同的美？而博览群书，知晓众人长，也必定会对自己的"根"，对心中的价值，拥有比别人更主动、更真诚的认同。

我们都是在比较之中，生发出对事物的感知与评判。王充的"两刃相割，利钝乃知，两论相驳，是非乃定"便是一例，通过比较，事物各自特点凸显，优劣立分，是非昌明。"比较"实在是我们认识事物的一把利器。

虽然"博闻"也不一定是比较，然而我向之所言，已带了主观的评判色彩，博闻本身使人丰富自我而并非无倾向，只是看到千万书卷，万种风烟之后，自我已悄然有了价值判断。"万种风烟之后"我之主体性方才显现，若是腹中空空，那么所谓认识与观点，自然基于空想，流于浅薄。

由是观之，我们要真正做到"博闻"才能真正客观地认识事物，所谓"操千曲而后晓声，观千剑而后识器"便是此意。在观"千剑"之后，形成对良器的判断，这便是博闻的作用了。

而所谓的博闻，与博闻中的比较，都需要一个开放的自我。否则会"井底之蛙"囿于身，失去了对外物的比较和借鉴，将会丢失自我的判断与认同。只有足够开阔的胸襟，执着的坚持，敢于突破，才能形成自身的认识。如冯友兰先生学贯中西，却终身致力于"阐旧邦以辅新命"，正是以为他在博采世界文化之众长后，更深刻地理解与认同了中国文化，他愿意投身于中国哲学史的浩海之中，以一己之力注解和发扬，若没有一个开放的自我，这是难以想象的。

万种风烟过眼后，有人得出"巫山之云最美"，便拒绝欣赏别处的美，我们大约都会觉得可惜、可叹。比较之后得到自己认同的价值，我们也不能抱守不放，而更要动态吸收，博采众长，才能算真正认识了事物。正如有人喜欢"中国味"音乐，而中国音乐也是文化交融、动态发展的，琵琶、扬琴、二胡……古时的异域风情，如今也成了正牌"民乐"，先人的灵活与进步，我们更应该守护与传扬。

正所谓，万种风烟过眼后，心中最美景，还是随时变，只是那份不变的，是根，是魂，是自我对它发自内心的认同。`;

function loadDemo() {
  document.getElementById('essay').value = DEMO_ESSAY;
  document.getElementById('topic').value = '万种风烟过眼后';
}

async function analyze() {
  const essay = document.getElementById('essay').value.trim();
  if (!essay) { alert('请先输入议论文文本'); return; }
  const topic = document.getElementById('topic').value.trim() || null;

  const btn = document.getElementById('analyzeBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> 分析中（约 30-60 秒，请耐心等待）……';

  const resultDiv = document.getElementById('result');
  resultDiv.classList.remove('show');
  resultDiv.innerHTML = '<div class="card empty-hint">🔄 正在调用 DeepSeek API 进行三步推理，请稍候……</div>';
  resultDiv.classList.add('show');

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 180000);

  try {
    const resp = await fetch('/analyze', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({essay_text:essay, essay_topic:topic}),
      signal: controller.signal
    });
    clearTimeout(timer);
    if (!resp.ok) { throw new Error('服务器返回 ' + resp.status); }
    const data = await resp.json();
    render(data);
  } catch(e) {
    if (e.name === 'AbortError') {
      resultDiv.innerHTML = '<div class="card error-box">⏰ 分析超时（3 分钟），请简化文本后重试。</div>';
    } else {
      resultDiv.innerHTML = '<div class="card error-box">❌ 请求失败：' + esc(e.message) + '</div>';
    }
    resultDiv.classList.add('show');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '🚀 开始分析';
  }
}

function badge(type) {
  const map = {major_claim:'MC',paragraph_claim:'Claim',analysis:'A',evidence:'E',evidence_analysis:'EA'};
  const cls = {major_claim:'badge-mc',paragraph_claim:'badge-claim',analysis:'badge-analysis',evidence:'badge-evidence',evidence_analysis:'badge-ea'};
  return `<span class="badge ${cls[type]||''}">${map[type]||type}</span>`;
}

function render(data) {
  let html = '';

  // 错误
  if (data.errors && data.errors.length) {
    html += `<div class="card error-box">⚠️ ${data.errors.join('<br>')}</div>`;
  }

  // 总结
  if (data.summary) {
    html += `<div class="card"><div class="summary-box">📝 <strong>论证结构总结</strong><br>${esc(data.summary)}</div></div>`;
  }

  // 节点表
  const nodes = (data.graph||{}).node_table || (data.classification||{}).node_table || [];
  if (nodes.length) {
    const types={}; nodes.forEach(n=>{const t=n.type||'?';types[t]=(types[t]||0)+1;});
    let st = '<div class="stats-row">';
    for (const [t,c] of Object.entries(types)) st += `<div class="stat"><div class="num">${c}</div><div class="label">${badge(t)}</div></div>`;
    st += '</div>';
    html += `<div class="card">
      <div class="section-title"><span class="icon">📊</span>节点表（${nodes.length} 个 ADU）</div>
      ${st}
      <table><tr><th>ID</th><th>类型</th><th>文本</th><th>理由</th></tr>`;
    nodes.forEach(n => {
      html += `<tr><td><code>${esc(n.node_id||n.id||'?')}</code></td><td>${badge(n.type)}</td><td>${esc((n.text||'').slice(0,100))}${(n.text||'').length>100?'…':''}</td><td style="font-size:11px;color:#666;">${esc((n.reasoning||[]).join('；')||'-')}</td></tr>`;
    });
    html += '</table></div>';
  }

  // 边表
  const edges = (data.graph||{}).edge_table || [];
  if (edges.length) {
    html += `<div class="card">
      <div class="section-title"><span class="icon">🔗</span>关系边表（${edges.length} 条）</div>
      <table><tr><th>From</th><th>关系</th><th>To</th><th>理由</th></tr>`;
    edges.forEach(e => {
      html += `<tr><td><code>${esc(e.from||'?')}</code></td><td style="font-weight:600;">${esc(e.relation||'?')}</td><td><code>${esc(e.to||'?')}</code></td><td style="font-size:11px;color:#666;">${esc((e.reasoning||'').slice(0,60))}</td></tr>`;
    });
    html += '</table></div>';
  }

  // 论证树
  const tree = (data.graph||{}).tree_graph || '';
  if (tree) {
    html += `<div class="card">
      <div class="section-title"><span class="icon">🌳</span>论证树</div>
      <div class="tree-box">${esc(tree)}</div></div>`;
  }

  // 论证关系图：纯 JS 生成 SVG，零外部依赖
  const mermaidCode = (data.graph||{}).mermaid_code || '';
  if (mermaidCode) {
    const svg = renderGraphSVG(mermaidCode);
    html += `<div class="card">
      <div class="section-title"><span class="icon">📐</span>论证关系图</div>
      <div class="mermaid-box">${svg}</div></div>`;
  }

  // 一致性检查
  const con = data.consistency || {};
  if (Object.keys(con).length) {
    const passed = con.passed !== false && !con.issues?.length;
    html += `<div class="card">
      <div class="section-title"><span class="icon">🔍</span>一致性检查 — <span class="${passed?'check-pass':'check-fail'}">${passed?'✅ 通过':'❌ 未通过'}</span></div>`;
    html += `<div class="check-item">段落 Claim → MC 连接：<span class="${con.all_claims_connected_to_mc!==false?'check-pass':'check-fail'}">${con.all_claims_connected_to_mc!==false?'✅':'❌'}</span></div>`;
    html += `<div class="check-item">Evidence → Claim 连接：<span class="${con.all_evidence_connected!==false?'check-pass':'check-fail'}">${con.all_evidence_connected!==false?'✅':'❌'}</span></div>`;
    const orphans = con.orphan_nodes || [];
    html += `<div class="check-item">孤立节点：${orphans.length ? '<span class="check-fail">'+orphans.join(', ')+'</span>' : '<span class="check-pass">无</span>'}</div>`;
    html += `<div class="check-item">循环检测：<span class="${con.cycles_detected?'check-fail':'check-pass'}">${con.cycles_detected?'❌ 有环':'✅ 无环'}</span></div>`;
    if (con.issues && con.issues.length) {
      con.issues.forEach(i => { html += `<div class="issue">⚠️ ${esc(i)}</div>`; });
    }
    html += '</div>';
  }

  const resultDiv = document.getElementById('result');
  resultDiv.innerHTML = html || '<div class="card empty-hint">暂无结果数据</div>';
  resultDiv.classList.add('show');
}

// ============ 纯 JS Mermaid→SVG 渲染器（零外部依赖）============
function renderGraphSVG(code) {
  const nodes = [], edges = [];
  const lines = code.split('\n').filter(l => l.trim());
  for (const line of lines) {
    const trimmed = line.trim();
    // 支持 Mermaid 边格式：-->、-.->、-->|label|、-.->|label|
    const edgeMatch = trimmed.match(/^(\S+?)\s*-*(?:\.-*)?>\s*(?:\|[^|]+\|)?\s*(\S+?)$/);
    if (edgeMatch) {
      edges.push({from:edgeMatch[1], to:edgeMatch[2]});
      continue;
    }
    const nodeMatch = trimmed.match(/^(\S+?)\s*\["(.+?)"\]/);
    if (nodeMatch) {
      nodes.push({id:nodeMatch[1], label:nodeMatch[2]});
    }
  }
  if (!nodes.length) return '<div style="color:#999;padding:12px;">无法解析论证图</div>';

  // 拓扑排序计算层级
  const inDegree = {}, outEdges = {};
  nodes.forEach(n => { inDegree[n.id] = 0; outEdges[n.id] = []; });
  edges.forEach(e => {
    if (!outEdges[e.from]) outEdges[e.from] = [];
    outEdges[e.from].push(e.to);
    inDegree[e.to] = (inDegree[e.to] || 0) + 1;
    inDegree[e.from] = inDegree[e.from] || 0;
  });
  const layers = [];
  let queue = nodes.filter(n => inDegree[n.id] === 0);
  const visited = new Set();
  while (queue.length) {
    const layer = {};
    const next = [];
    for (const n of queue) {
      if (visited.has(n.id)) continue;
      visited.add(n.id);
      layer[n.id] = true;
      for (const t of (outEdges[n.id] || [])) {
        inDegree[t]--;
        if (inDegree[t] === 0 && !visited.has(t)) next.push({id:t,label:''});
      }
    }
    // Find labels for next queue nodes
    next.forEach(nn => {
      const found = nodes.find(n => n.id === nn.id);
      if (found) nn.label = found.label;
    });
    if (Object.keys(layer).length) layers.push(layer);
    queue = next;
  }
  // Put remaining unvisited in last layer
  const remaining = nodes.filter(n => !visited.has(n.id));
  if (remaining.length) {
    const last = {};
    remaining.forEach(n => { last[n.id] = true; });
    layers.push(last);
  }

  // 布局参数
  const nodeW = 200, nodeH = 52, gapX = 30, gapY = 24, padX = 24, padY = 24;
  const fontSize = 13, lineH = 18;
  // 计算每层实际节点高度（多行文本）
  function calcNodeH(label) {
    const maxW = nodeW - 24;
    let lines = 1, cur = 0;
    for (const ch of label) {
      cur += (ch.charCodeAt(0) > 127) ? fontSize : fontSize * 0.55;
      if (cur > maxW) { lines++; cur = (ch.charCodeAt(0) > 127) ? fontSize : fontSize * 0.55; }
    }
    return Math.max(nodeH, lines * lineH + 20);
  }
  // 计算每列最大高度
  const layerInfos = layers.map(layer => {
    const ids = nodes.filter(n => layer[n.id]).map(n => n.id);
    const layout = [];
    ids.forEach((id, i) => {
      const n = nodes.find(nn => nn.id === id);
      layout.push({id, label:n?n.label:id, h:calcNodeH(n?n.label:id)});
    });
    const maxH = Math.max(...layout.map(l => l.h));
    return {ids: layout, maxH};
  });

  let totalW = layerInfos.reduce((sum, l) => sum + nodeW + gapX, 0) - gapX + padX * 2;
  totalW = Math.max(totalW, 400);
  let totalH = 0;
  layerInfos.forEach(l => { totalH = Math.max(totalH, l.ids.reduce((s, n, i) => s + n.h + (i>0?gapY:0), 0)); });
  totalH += padY * 2;

  // 节点位置
  const positions = {};
  let x = padX;
  layerInfos.forEach(l => {
    const total = l.ids.reduce((s, n, i) => s + n.h + (i>0?gapY:0), 0);
    let y = padY + (totalH - total) / 2;
    l.ids.forEach(nn => {
      positions[nn.id] = {x, y, w: nodeW, h: nn.h};
      y += nn.h + gapY;
    });
    x += nodeW + gapX;
  });

  // 颜色
  function nodeColor(id) {
    const n = nodes.find(nn => nn.id === id);
    if (!n) return '#555';
    if (n.label.startsWith('MC:')) return '#e74c3c';
    if (n.label.startsWith('P')) return '#2E75B6';
    return '#27ae60';
  }

  // 生成 SVG
  let svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${totalW} ${totalH}" style="max-width:100%;height:auto;font-family:PingFang SC,Microsoft YaHei,sans-serif;">`;
  // 箭头标记
  svg += `<defs><marker id="arrow" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto"><polygon points="0 0, 10 3.5, 0 7" fill="#888"/></marker></defs>`;
  // 边
  edges.forEach(e => {
    const f = positions[e.from], t = positions[e.to];
    if (!f || !t) return;
    const x1 = f.x + f.w, y1 = f.y + f.h / 2;
    const x2 = t.x, y2 = t.y + t.h / 2;
    const mx = (x1 + x2) / 2;
    svg += `<path d="M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}" stroke="#888" stroke-width="1.5" fill="none" marker-end="url(#arrow)"/>`;
  });
  // 节点
  positions && Object.entries(positions).forEach(([id, p]) => {
    const n = nodes.find(nn => nn.id === id);
    const label = n ? n.label : id;
    const color = nodeColor(id);
    const shortLabel = label.length > 35 ? label.slice(0,33)+'…' : label;
    svg += `<rect x="${p.x}" y="${p.y}" width="${p.w}" height="${p.h}" rx="6" fill="white" stroke="${color}" stroke-width="2"/>`;
    svg += `<text x="${p.x+p.w/2}" y="${p.y+p.h/2}" text-anchor="middle" dominant-baseline="middle" font-size="${fontSize}" fill="#222">${escXml(shortLabel)}</text>`;
  });
  svg += '</svg>';
  return svg;
}
function escXml(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

function esc(s) {
  if (!s) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
</script>
</body>
</html>"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(force=True)
    essay_text = data.get("essay_text", "").strip()
    essay_topic = data.get("essay_topic") or None

    if not essay_text:
        return jsonify({"errors": ["请输入议论文文本"]}), 400

    result = agent.analyze(essay_text, essay_topic=essay_topic, verbose=False)

    # 构建前端友好的扁平结构
    return jsonify({
        "summary": result.get("summary"),
        "classification": result.get("classification"),
        "graph": result.get("graph"),
        "consistency": result.get("consistency"),
        "errors": result.get("errors", []),
    })


if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("  ArgGraph-Agent Web 界面")
    print("  " + "=" * 51)
    print("  🌐 打开浏览器访问: http://localhost:5001")
    print("  🛑 按 Ctrl+C 停止服务器")
    print("=" * 55 + "\n")
    app.run(host="127.0.0.1", port=5001, debug=False)
