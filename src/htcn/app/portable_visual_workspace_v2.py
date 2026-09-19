from __future__ import annotations

import json
from typing import Any


def build_portable_visual_workspace_html_v2(
    inspection: dict[str, Any],
) -> str:
    encoded = json.dumps(
        inspection,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).replace("</", "<\\/")

    template = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>HT-CN v4 便携图形复盘 · Visual Semantics v2</title>
<style>
:root{font-family:Inter,"PingFang SC","Microsoft YaHei",sans-serif;color:#172033;background:#f4f6fa}
*{box-sizing:border-box}body{margin:0}.shell{max-width:1640px;margin:auto;padding:22px}
h1{margin:0 0 5px;font-size:28px}h2{font-size:18px;margin:0 0 12px}h3{font-size:15px;margin:14px 0 8px}.muted{color:#69758a}
.banner,.card{background:#fff;border:1px solid #dfe5ef;border-radius:12px;padding:13px}
.banner{margin:14px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin:12px 0 18px}
.metric b{display:block;font-size:22px;margin-top:4px}.layout{display:grid;grid-template-columns:minmax(360px,.82fr) minmax(720px,1.9fr);gap:14px}
@media(max-width:1120px){.layout{grid-template-columns:1fr}}.toolbar{display:flex;gap:8px;margin-bottom:10px}
input[type="text"]{width:100%;padding:10px 11px;border:1px solid #cbd4e2;border-radius:9px}.list{max-height:860px;overflow:auto}
.item{width:100%;text-align:left;padding:11px;border:1px solid #e2e7ef;border-radius:10px;background:#fff;margin-bottom:8px;cursor:pointer}
.item.active{outline:2px solid #75849c}.item .top{display:flex;justify-content:space-between;gap:8px}.tag{display:inline-block;padding:2px 7px;border-radius:999px;background:#eef2f7;margin:3px 4px 0 0;font-size:12px}
.detail-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:8px;margin:10px 0}.detail-grid>div{padding:9px;background:#f8fafc;border-radius:8px}
.chart{width:100%;overflow:auto;border:1px solid #e0e6ef;border-radius:12px;background:#fff}.chart svg{display:block;min-width:900px;width:100%;height:auto}
.legend{display:flex;gap:12px;flex-wrap:wrap;font-size:12px;margin:8px 0}.swatch{display:inline-block;width:22px;height:0;border-top:2px solid currentColor;vertical-align:middle;margin-right:5px}.dash{border-top-style:dashed}.dot{border-top-style:dotted}
.error{padding:14px;border:1px solid #e0b6b6;border-radius:10px;background:#fff8f8}.notice{padding:10px;border:1px solid #dfe5ef;border-radius:9px;background:#fafbfd;margin:8px 0}
.controls{display:flex;gap:8px 14px;flex-wrap:wrap;padding:9px 10px;background:#f8fafc;border-radius:9px;margin:8px 0}.controls label{font-size:12px;white-space:nowrap}
table{width:100%;border-collapse:collapse;font-size:12px}th,td{text-align:left;padding:7px 8px;border-bottom:1px solid #edf0f5;vertical-align:top}th{background:#f8fafc;position:sticky;top:0}
.table-wrap{max-height:260px;overflow:auto;border:1px solid #edf0f5;border-radius:9px}.pill-source{font-weight:700}.warning{color:#7a4d1f}.notes{white-space:pre-wrap;line-height:1.6}
footer{margin:24px 0;color:#68758a;font-size:12px}
</style>
</head>
<body>
<div class="shell">
<h1>HT-CN v4 便携图形复盘</h1>
<div class="muted">Visual Semantics v2 · 比例 / Raw PRZ / Ideal Core / Envelope / Source Clock 分层展示</div>
<div class="banner" id="verify"></div>
<div class="grid" id="metrics"></div>
<div class="layout">
  <section class="card">
    <div class="toolbar"><input type="text" id="search" placeholder="搜索证券 / 形态 / schema / action / lifecycle / display key"></div>
    <div class="list" id="items"></div>
  </section>
  <section class="card">
    <h2 id="title">选择一个候选</h2>
    <div id="summary"></div>
    <div class="controls">
      <label><input type="checkbox" id="show-source" checked> Source Raw PRZ</label>
      <label><input type="checkbox" id="show-ideal" checked> Ideal Core</label>
      <label><input type="checkbox" id="show-envelope"> 全组件 Envelope</label>
      <label><input type="checkbox" id="show-components" checked> PRZ 组件线</label>
      <label><input type="checkbox" id="show-life" checked> Source Clock</label>
      <label><input type="checkbox" id="show-guides" checked> 目标/下一关键价</label>
    </div>
    <div class="legend">
      <span><i class="swatch"></i>真实已发生形态腿</span>
      <span><i class="swatch dash"></i>目标/下一关键导引，不是预测腿</span>
      <span><i class="swatch dot"></i>工程/审计层，不等于 Source Raw PRZ</span>
    </div>
    <div class="chart" id="chart"></div>
    <div id="semantic-panels"></div>
    <div class="notes" id="notes"></div>
  </section>
</div>
<footer>本工作区只解释 transport 中已有的数据。Visual Semantics v2 不创建节点、不修改谐波身份、不改写 Source Raw PRZ/生命周期，也不生成收益排序或买卖指令。</footer>
</div>
<script type="application/json" id="htcn-data">__DATA__</script>
<script>
const DATA=JSON.parse(document.getElementById("htcn-data").textContent);
const ITEMS=DATA.portable_items||[], DETAILS=DATA.details_by_display_key||{};
let selectedKey=null;
const esc=v=>String(v??"—");
const fmt=v=>v==null||!Number.isFinite(Number(v))?"—":Number(v).toFixed(3);
const tag=v=>'<span class="tag">'+esc(v)+'</span>';
const ctrl=id=>document.getElementById(id).checked;

document.getElementById("verify").textContent=
 "验证："+esc(DATA.source?.verification_status)+" ｜ Transport："+esc(DATA.summary?.status)+
 " ｜ 交易日："+esc(DATA.summary?.trade_date)+" ｜ Visual semantics：v2";
const metrics=[
 ["Queue候选",DATA.summary?.queue_display_key_count],
 ["图形可用",DATA.summary?.detail_display_key_count],
 ["显式失败",DATA.summary?.error_display_key_count],
 ["完整覆盖",DATA.summary?.detail_complete?"是":"降级"]
];
document.getElementById("metrics").innerHTML=metrics.map(x=>'<div class="card metric"><span class="muted">'+x[0]+'</span><b>'+esc(x[1])+'</b></div>').join("");

function svgEl(name,attrs={},text=""){
 const el=document.createElementNS("http://www.w3.org/2000/svg",name);
 for(const [k,v] of Object.entries(attrs)) el.setAttribute(k,String(v));
 if(text) el.textContent=text; return el;
}
function layerEnabled(id){
 if(id==="source_raw_prz") return ctrl("show-source");
 if(id==="ideal_core") return ctrl("show-ideal");
 if(id==="component_envelope") return ctrl("show-envelope");
 return true;
}
function renderChart(detail,queue){
 const host=document.getElementById("chart");host.innerHTML="";
 if(!detail){host.innerHTML='<div class="error">该候选没有 portable detail。</div>';return}
 const p=detail.pattern||{},vs=detail.visual_semantics||{},top=vs.topology||{},prz=vs.prz||{},life=vs.lifecycle||{};
 if(top.status==="invalid_non_prefix"||top.status==="unsupported_schema"){host.innerHTML='<div class="error">Schema 拓扑不可安全绘制；已 fail closed。</div>';return}
 const allBars=(detail.bars||[]).filter(x=>x&&x.index!=null);
 const pts=(p.points||[]).filter(x=>x&&x.index!=null&&x.price!=null);
 if(!allBars.length||!pts.length){host.innerHTML='<div class="error">图形数据不完整。</div>';return}
 const minP=Math.min(...pts.map(x=>Number(x.index))),maxP=Math.max(...pts.map(x=>Number(x.index)));
 let bars=allBars.filter(x=>Number(x.index)>=minP-20&&Number(x.index)<=maxP+50);
 if(bars.length<20) bars=allBars.slice(Math.max(0,allBars.length-140));

 const visibleLayers=(prz.layers||[]).filter(x=>layerEnabled(x.id));
 const components=ctrl("show-components")?(prz.components||[]):[];
 const guides=ctrl("show-guides")?(life.price_guides||[]):[];
 const extra=[
   ...pts.map(x=>Number(x.price)),
   ...visibleLayers.flatMap(x=>[Number(x.price_low),Number(x.price_high)]),
   ...components.flatMap(x=>[Number(x.price_low),Number(x.price_high)]),
   ...guides.map(x=>Number(x.price))
 ].filter(Number.isFinite);

 const W=1180,H=570,L=68,R=128,T=28,B=44,pw=W-L-R,ph=H-T-B;
 const minI=Math.min(...bars.map(x=>Number(x.index))),maxI=Math.max(...bars.map(x=>Number(x.index))),spanI=Math.max(1,maxI-minI);
 let lo=Math.min(...bars.map(x=>Number(x.low)),...extra),hi=Math.max(...bars.map(x=>Number(x.high)),...extra);
 const pad=Math.max((hi-lo)*.08,Math.abs(hi)*.01,.01);lo-=pad;hi+=pad;const spanP=Math.max(.01,hi-lo);
 const X=i=>L+(Number(i)-minI)/spanI*pw,Y=v=>T+(hi-Number(v))/spanP*ph;
 const svg=svgEl("svg",{viewBox:`0 0 ${W} ${H}`,role:"img","aria-label":"HT-CN 便携谐波图形语义 v2"});
 svg.appendChild(svgEl("rect",{x:0,y:0,width:W,height:H,fill:"#fff"}));

 for(let g=0;g<6;g++){const val=lo+spanP*g/5,yy=Y(val);svg.appendChild(svgEl("line",{x1:L,x2:W-R,y1:yy,y2:yy,stroke:"#edf0f5"}));svg.appendChild(svgEl("text",{x:L-8,y:yy+4,"text-anchor":"end","font-size":11,fill:"#677287"},fmt(val)))}

 for(const layer of [...visibleLayers].reverse()){
   const y1=Y(layer.price_high),y2=Y(layer.price_low),h=Math.max(2,y2-y1);
   if(layer.id==="source_raw_prz"){
     svg.appendChild(svgEl("rect",{x:L,y:y1,width:pw,height:h,fill:"#b8c4d4","fill-opacity":.28,stroke:"#4c5d73","stroke-width":1.5}));
   }else{
     svg.appendChild(svgEl("rect",{x:L,y:y1,width:pw,height:h,fill:"none",stroke:"#8b97a8","stroke-width":1.2,"stroke-dasharray":layer.id==="ideal_core"?"7 4":"2 5"}));
   }
   svg.appendChild(svgEl("text",{x:L+6,y:Math.max(T+12,y1+12),"font-size":10,fill:"#526176"},layer.label+" "+fmt(layer.price_low)+"–"+fmt(layer.price_high)));
 }

 const step=pw/Math.max(1,bars.length),cw=Math.max(1,Math.min(6,step*.58));
 for(const b of bars){
   const x=X(b.index),yo=Y(b.open),yc=Y(b.close),yh=Y(b.high),yl=Y(b.low);
   svg.appendChild(svgEl("line",{x1:x,x2:x,y1:yh,y2:yl,stroke:"#667386","stroke-width":1}));
   svg.appendChild(svgEl("rect",{x:x-cw/2,y:Math.min(yo,yc),width:cw,height:Math.max(1,Math.abs(yc-yo)),fill:Number(b.close)>=Number(b.open)?"#fff":"#737f90",stroke:"#5f6b7c","stroke-width":1}));
 }

 for(const leg of top.legs||[]){
   if(leg.from_index==null||leg.to_index==null||leg.from_price==null||leg.to_price==null)continue;
   if(leg.from_index<minI||leg.to_index>maxI)continue;
   svg.appendChild(svgEl("line",{x1:X(leg.from_index),y1:Y(leg.from_price),x2:X(leg.to_index),y2:Y(leg.to_price),stroke:"#26364d","stroke-width":2.5}));
   const mx=(X(leg.from_index)+X(leg.to_index))/2,my=(Y(leg.from_price)+Y(leg.to_price))/2;
   svg.appendChild(svgEl("text",{x:mx,y:my-6,"text-anchor":"middle","font-size":10,"font-weight":"600",fill:"#3c4c62"},leg.name));
 }

 for(const q of pts.filter(x=>Number(x.index)>=minI&&Number(x.index)<=maxI)){
   svg.appendChild(svgEl("circle",{cx:X(q.index),cy:Y(q.price),r:4.5,fill:"#fff",stroke:"#26364d","stroke-width":2}));
   svg.appendChild(svgEl("text",{x:X(q.index),y:Y(q.price)-10,"text-anchor":"middle","font-size":11,"font-weight":"700",fill:"#26364d"},esc(q.label)+" "+fmt(q.price)));
 }

 if(ctrl("show-components")){
   let ordinal=0;
   for(const comp of components){
     ordinal++;
     const price=(Number(comp.price_low)+Number(comp.price_high))/2,yy=Y(price);
     svg.appendChild(svgEl("line",{x1:L,x2:W-R,y1:yy,y2:yy,stroke:comp.source_raw_prz_member?"#53647b":"#a0a9b6","stroke-width":comp.source_raw_prz_member?1.5:1,"stroke-dasharray":comp.source_raw_prz_member?"":"2 4"}));
     svg.appendChild(svgEl("text",{x:W-R+5,y:yy+3,"font-size":9,fill:"#647186"},"["+ordinal+"]"));
   }
 }

 if(ctrl("show-life")){
   let evn=0;
   for(const ev of life.events||[]){
     if(ev.bar<minI||ev.bar>maxI)continue;
     const xx=X(ev.bar),slot=evn++%5;
     svg.appendChild(svgEl("line",{x1:xx,x2:xx,y1:T,y2:H-B,stroke:"#8795a8","stroke-width":1,"stroke-dasharray":"4 4"}));
     svg.appendChild(svgEl("text",{x:xx+3,y:T+12+slot*12,"font-size":9,fill:"#5f6d80"},ev.label));
   }
 }

 if(ctrl("show-guides")){
   for(const guide of guides){
     if(!Number.isFinite(Number(guide.price)))continue;
     const yy=Y(guide.price);
     svg.appendChild(svgEl("line",{x1:X(maxP),x2:W-R,y1:yy,y2:yy,stroke:"#64748b","stroke-width":1.4,"stroke-dasharray":"7 5"}));
     svg.appendChild(svgEl("text",{x:W-R-4,y:yy-5,"text-anchor":"end","font-size":10,fill:"#526176"},guide.label+" "+fmt(guide.price)));
   }
 }

 svg.appendChild(svgEl("text",{x:L,y:H-13,"font-size":11,fill:"#69758a"},esc(bars[0]?.trade_date)));
 svg.appendChild(svgEl("text",{x:W-R,y:H-13,"text-anchor":"end","font-size":11,fill:"#69758a"},esc(bars[bars.length-1]?.trade_date)));
 host.appendChild(svg);
}

function semanticPanels(detail){
 const vs=detail?.visual_semantics||{},top=vs.topology||{},prz=vs.prz||{},ratios=vs.ratios||[],spec=vs.schema_specific||{};
 const ratioRows=ratios.length?ratios.map(r=>'<tr><td>'+esc(r.label)+'</td><td><b>'+fmt(r.value)+'</b></td><td>'+esc(r.source_check_target)+'</td><td>'+esc(r.source_check_passed)+'</td></tr>').join(""):'<tr><td colspan="4">当前 payload 没有更多已知比例。</td></tr>';
 const compRows=(prz.components||[]).length?(prz.components||[]).map((x,i)=>'<tr><td>['+(i+1)+'] '+esc(x.name)+'</td><td>'+fmt(x.ratio_low)+(x.ratio_high!==x.ratio_low?'–'+fmt(x.ratio_high):'')+'</td><td>'+fmt(x.price_low)+(x.price_high!==x.price_low?'–'+fmt(x.price_high):'')+'</td><td class="'+(x.source_raw_prz_member?'pill-source':'')+'">'+(x.source_raw_prz_member?'Raw PRZ 成员':(x.execution_refinement_only?'执行 refinement':'审计组件'))+'</td></tr>').join(""):'<tr><td colspan="4">无组件。</td></tr>';
 const warnings=(vs.warnings||[]).map(x=>'<div class="notice warning">'+esc(x)+'</div>').join("");
 const conflicts=(vs.identity_conflicts||[]).length?'<div class="notice">同几何身份冲突：'+(vs.identity_conflicts||[]).map(tag).join(" ")+'<br><span class="muted">当前图只画 Queue 选中的 primary identity，避免多形态重叠遮挡。</span></div>':'';
 let schemaNote='';
 if(spec.shark_management) schemaNote='<div class="notice">Shark 专属管理：50%='+fmt(spec.shark_management.target_50)+' ｜ 61.8%='+fmt(spec.shark_management.target_618)+' ｜ Reciprocal AB=CD='+fmt(spec.shark_management.reciprocal_abcd)+'。Shark 终点是 C，不虚构 D。</div>';
 if(spec.five_zero_boundary) schemaNote='<div class="notice warning">'+esc(spec.five_zero_boundary.visual_warning)+'</div>';
 return conflicts+schemaNote+warnings+
 '<h3>Schema / 拓扑</h3><div class="notice"><b>'+esc(top.schema_name)+'</b> ｜ 状态 '+esc(top.status)+'<br>已观察：'+esc((top.observed_labels||[]).join(" → "))+'<br>完整定义：'+esc((top.expected_labels||[]).join(" → "))+(top.missing_future_labels?.length?'<br><span class="warning">尚未发生：'+esc(top.missing_future_labels.join(" / "))+'（只列出，不绘制）</span>':'')+'</div>'+
 '<h3>已知比例</h3><div class="table-wrap"><table><thead><tr><th>测量</th><th>实际</th><th>源检查目标</th><th>检查结果</th></tr></thead><tbody>'+ratioRows+'</tbody></table></div>'+
 '<h3>PRZ 组件</h3><div class="table-wrap"><table><thead><tr><th>组件</th><th>比例</th><th>价格</th><th>语义</th></tr></thead><tbody>'+compRows+'</tbody></table></div>';
}

function selectItem(key){
 selectedKey=key;renderList();
 const wrap=ITEMS.find(x=>x.display_key===key),q=wrap?.queue||{},d=DETAILS[key];
 document.getElementById("title").textContent=esc(q.instrument_id)+" · "+esc(q.pattern_id)+" · "+esc(q.schema)+" · S"+esc(q.scale);
 if(!d){
   document.getElementById("summary").innerHTML='<div class="error">portable detail 失败：'+esc(wrap?.detail_error)+'</div>';
   document.getElementById("semantic-panels").innerHTML="";
   document.getElementById("notes").textContent="";
   renderChart(null,q);return;
 }
 const p=d.pattern||{},vs=d.visual_semantics||{},life=vs.lifecycle||{},prz=vs.prz||{};
 const rawLayer=(prz.layers||[]).find(x=>x.id==="source_raw_prz");
 document.getElementById("summary").innerHTML='<div class="detail-grid">'+
  '<div><span class="muted">Action / Lifecycle</span><br>'+tag(q.action_state)+tag(q.lifecycle_state)+'</div>'+
  '<div><span class="muted">当前判断</span><br>'+esc(q.current_position)+'</div>'+
  '<div><span class="muted">先看</span><br>'+esc(q.first_watch)+'</div>'+
  '<div><span class="muted">下一关键</span><br><b>'+fmt(q.next_key_price)+'</b><br>'+esc(q.next_key_price_role)+'</div>'+
  '<div><span class="muted">Source Raw PRZ</span><br>'+fmt(rawLayer?.price_low)+' – '+fmt(rawLayer?.price_high)+'</div>'+
  '<div><span class="muted">Source Clock</span><br>'+esc(life.state)+'<br><span class="muted">'+esc(life.state_reason)+'</span></div></div>';
 document.getElementById("semantic-panels").innerHTML=semanticPanels(d);
 document.getElementById("notes").textContent=
   "节点："+(p.points||[]).map(x=>esc(x.label)+"="+fmt(x.price)).join("  ｜  ")+"\n"+
   "边界：所有实线腿都来自 transport 中真实存在的 pattern.points；形成中缺失节点绝不补画。\n"+
   "PRZ：Source Raw PRZ 是 source-defined 层；Ideal Core 是 HT-CN 工程收敛层；Envelope 只是全部组件审计外包络。\n"+
   "虚线：只用于 Source Clock / 目标价 / 下一关键价导引，不属于谐波身份几何。";
 renderChart(d,q);
}

function hay(x){return JSON.stringify(x).toLowerCase()}
function renderList(){
 const term=document.getElementById("search").value.trim().toLowerCase();
 const filtered=ITEMS.filter(x=>!term||hay(x).includes(term)||hay(DETAILS[x.display_key]||{}).includes(term));
 document.getElementById("items").innerHTML=filtered.map(x=>{const q=x.queue||{},d=DETAILS[x.display_key],vs=d?.visual_semantics||{};return '<button class="item '+(x.display_key===selectedKey?'active':'')+'" data-key="'+esc(x.display_key).replace(/"/g,"&quot;")+'"><div class="top"><b>'+esc(q.instrument_id)+'</b><span>'+(x.detail_available?'图形✓':'图形×')+'</span></div><div>'+tag(q.pattern_id)+tag(q.schema)+tag(q.action_state)+tag(q.lifecycle_state)+'</div><div class="muted">'+esc(vs.topology?.schema_name)+' ｜ '+esc(q.current_position)+'</div></button>'}).join("")||'<div class="muted">无匹配候选</div>';
 for(const el of document.querySelectorAll(".item")) el.addEventListener("click",()=>selectItem(el.dataset.key));
}
document.getElementById("search").addEventListener("input",renderList);
for(const id of ["show-source","show-ideal","show-envelope","show-components","show-life","show-guides"]){
 document.getElementById(id).addEventListener("change",()=>{if(selectedKey)selectItem(selectedKey)});
}
renderList();
const first=ITEMS.find(x=>x.detail_available)||ITEMS[0];if(first)selectItem(first.display_key);
</script>
</body></html>"""
    return template.replace("__DATA__", encoded)
