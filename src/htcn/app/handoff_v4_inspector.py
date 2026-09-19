from __future__ import annotations

import json
import tempfile
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from htcn.app.handoff_v3_inspector import build_handoff_v3_inspection
from htcn.app.handoff_v4_portable_detail import (
    DAILY_HANDOFF_V4_SCHEMA_VERSION,
    verify_daily_handoff_bundle_v4,
)
from htcn.app.portable_visual_semantics import build_pattern_visual_semantics
from htcn.app.portable_visual_workspace_v2 import (
    build_portable_visual_workspace_html_v2,
)

HANDOFF_V4_INSPECTION_SCHEMA_VERSION = 2


@dataclass(frozen=True, slots=True)
class HandoffV4InspectorContract:
    version: int = 2
    semantics: str = "portable_pattern_visual_review_v2"
    source_bundle_schema: int = DAILY_HANDOFF_V4_SCHEMA_VERSION
    visual_semantics_version: int = 2
    schema_specific_rendering: bool = True
    layered_prz_rendering: bool = True
    future_pattern_points_may_be_invented: bool = False
    requires_market_database: bool = False
    imports_product_state: bool = False
    writes_review_journal: bool = False
    creates_review_events: bool = False
    writes_m4_evidence: bool = False
    predictive_score_used: bool = False
    historical_outcome_used_for_ranking: bool = False
    alpha_inference_allowed: bool = False
    is_trade_instruction: bool = False

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


def _read_json_bytes(data: bytes, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{label}_unreadable:{type(exc).__name__}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"{label}_not_object")
    return payload


def _roles(manifest: dict[str, Any]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for record in manifest.get("files") or []:
        if not isinstance(record, dict):
            continue
        role = str(record.get("role") or "")
        arcname = str(record.get("arcname") or "")
        if role and arcname:
            result.setdefault(role, []).append(arcname)
    return result


def _nested_v3_inspection(data: bytes) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="htcn-v4-inspector-v3-") as temp:
        path = Path(temp) / "htcn-daily-handoff-v3.zip"
        path.write_bytes(data)
        return build_handoff_v3_inspection(path)


def build_handoff_v4_inspection(bundle_path: str | Path) -> dict[str, Any]:
    source = Path(bundle_path)
    checked = verify_daily_handoff_bundle_v4(source)
    if checked.status != "valid":
        raise RuntimeError(
            "handoff_v4_invalid:" + ",".join(checked.errors)
        )

    with zipfile.ZipFile(source, "r") as archive:
        manifest = _read_json_bytes(
            archive.read("daily-handoff-v4-manifest.json"),
            label="handoff_v4_manifest",
        )
        roles = _roles(manifest)
        base_members = roles.get("m5_handoff_v3_base", [])
        if len(base_members) != 1:
            raise RuntimeError("handoff_v4_nested_v3_missing")
        base_inspection = _nested_v3_inspection(
            archive.read(base_members[0])
        )

        details_by_key: dict[str, dict[str, Any]] = {}
        detail_instruments: dict[str, dict[str, Any]] = {}
        for arcname in roles.get("m5_portable_instrument_detail", []):
            payload = _read_json_bytes(
                archive.read(arcname),
                label="portable_instrument_detail",
            )
            instrument_id = str(payload.get("instrument_id") or "")
            detail_instruments[instrument_id] = payload
            bars = payload.get("bars") or []
            for entry in payload.get("patterns") or []:
                if not isinstance(entry, dict):
                    continue
                key = str(entry.get("display_key") or "")
                pattern = entry.get("pattern")
                if not key or not isinstance(pattern, dict):
                    continue
                details_by_key[key] = {
                    "display_key": key,
                    "instrument_id": instrument_id,
                    "trade_date": payload.get("trade_date"),
                    "price_mode": payload.get("price_mode"),
                    "warning": payload.get("warning"),
                    "bars": bars,
                    "pattern": pattern,
                    "visual_semantics": build_pattern_visual_semantics(pattern),
                }

        error_members = roles.get("m5_portable_detail_errors", [])
        detail_errors: list[dict[str, Any]] = []
        if len(error_members) == 1:
            error_payload = _read_json_bytes(
                archive.read(error_members[0]),
                label="portable_detail_errors",
            )
            detail_errors = [
                dict(item)
                for item in (error_payload.get("items") or [])
                if isinstance(item, dict)
            ]

    queue_items = (
        (base_inspection.get("indexes") or {}).get("current_queue_items") or []
    )
    queue_by_key = {
        str(item.get("display_key") or ""): dict(item)
        for item in queue_items
        if isinstance(item, dict) and item.get("display_key")
    }
    error_by_key = {
        str(item.get("display_key") or ""): item
        for item in detail_errors
        if item.get("display_key")
    }

    portable_items: list[dict[str, Any]] = []
    for key, queue_item in queue_by_key.items():
        detail = details_by_key.get(key)
        error = error_by_key.get(key)
        portable_items.append(
            {
                "display_key": key,
                "instrument_id": queue_item.get("instrument_id"),
                "queue": queue_item,
                "detail_available": detail is not None,
                "detail_error": None if error is None else error.get("error"),
            }
        )

    return {
        "schema_version": HANDOFF_V4_INSPECTION_SCHEMA_VERSION,
        "contract": HandoffV4InspectorContract().as_payload(),
        "source": {
            "bundle_path": str(source),
            "verification_status": checked.status,
            "bundle_schema_version": checked.schema_version,
            "bundle_file_count": checked.file_count,
        },
        "summary": {
            "status": manifest.get("status"),
            "trade_date": manifest.get("trade_date"),
            "queue_display_key_count": checked.queue_display_key_count,
            "detail_display_key_count": checked.detail_display_key_count,
            "error_display_key_count": checked.error_display_key_count,
            "detail_complete": checked.error_display_key_count == 0,
        },
        "transport_manifest": manifest,
        "v3": base_inspection,
        "portable_items": portable_items,
        "details_by_display_key": details_by_key,
        "detail_errors": detail_errors,
        "authoritative_evidence": False,
        "writes_m4_evidence": False,
        "imports_product_state": False,
        "creates_review_events": False,
        "is_trade_instruction": False,
        "alpha_inference_allowed": False,
        "predictive_score_used": False,
        "historical_outcome_used_for_ranking": False,
    }


def build_portable_pattern_review_html(inspection: dict[str, Any]) -> str:
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
<title>HT-CN v4 便携图形复盘</title>
<style>
:root{font-family:Inter,"PingFang SC","Microsoft YaHei",sans-serif;color:#172033;background:#f4f6fa}
*{box-sizing:border-box}body{margin:0}.shell{max-width:1560px;margin:auto;padding:22px}
h1{margin:0 0 5px;font-size:28px}h2{font-size:18px;margin:0 0 12px}.muted{color:#69758a}
.banner,.card{background:#fff;border:1px solid #dfe5ef;border-radius:12px;padding:13px}
.banner{margin:14px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin:12px 0 18px}
.metric b{display:block;font-size:22px;margin-top:4px}.layout{display:grid;grid-template-columns:minmax(390px,0.9fr) minmax(650px,1.7fr);gap:14px}
@media(max-width:1080px){.layout{grid-template-columns:1fr}}.toolbar{display:flex;gap:8px;margin-bottom:10px}
input{width:100%;padding:10px 11px;border:1px solid #cbd4e2;border-radius:9px}.list{max-height:760px;overflow:auto}
.item{width:100%;text-align:left;padding:11px;border:1px solid #e2e7ef;border-radius:10px;background:#fff;margin-bottom:8px;cursor:pointer}
.item.active{outline:2px solid #75849c}.item .top{display:flex;justify-content:space-between;gap:8px}.tag{display:inline-block;padding:2px 7px;border-radius:999px;background:#eef2f7;margin:3px 4px 0 0;font-size:12px}
.detail-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:8px;margin:10px 0}.detail-grid>div{padding:9px;background:#f8fafc;border-radius:8px}
.chart{width:100%;overflow:auto;border:1px solid #e0e6ef;border-radius:12px;background:#fff}.chart svg{display:block;min-width:820px;width:100%;height:auto}
.legend{display:flex;gap:12px;flex-wrap:wrap;font-size:12px;margin:8px 0}.swatch{display:inline-block;width:22px;height:0;border-top:2px solid currentColor;vertical-align:middle;margin-right:5px}.dash{border-top-style:dashed}
.error{padding:14px;border:1px solid #e0b6b6;border-radius:10px;background:#fff8f8}.notes{white-space:pre-wrap;line-height:1.6}
footer{margin:24px 0;color:#68758a;font-size:12px}
</style>
</head>
<body>
<div class="shell">
<h1>HT-CN v4 便携图形复盘</h1>
<div class="muted">真实 transport detail · 节点价格 · Source PRZ · 生命周期事件 · 无本机行情库</div>
<div class="banner" id="verify"></div>
<div class="grid" id="metrics"></div>
<div class="layout">
  <section class="card">
    <div class="toolbar"><input id="search" placeholder="搜索证券 / 形态 / action / lifecycle / display key"></div>
    <div class="list" id="items"></div>
  </section>
  <section class="card">
    <h2 id="title">选择一个候选</h2>
    <div id="summary"></div>
    <div class="legend">
      <span><i class="swatch"></i>已发生形态腿</span>
      <span><i class="swatch dash"></i>下一关键价导引（不是预测腿）</span>
      <span>PRZ 阴影 = transported Source PRZ</span>
    </div>
    <div class="chart" id="chart"></div>
    <div class="notes" id="notes"></div>
  </section>
</div>
<footer>v4 只把当前 Queue 的真实 pattern detail 带进便携包；不改变 Queue 排名，不推断收益，不生成交易指令。</footer>
</div>
<script type="application/json" id="htcn-data">__DATA__</script>
<script>
const DATA=JSON.parse(document.getElementById("htcn-data").textContent);
const ITEMS=DATA.portable_items||[], DETAILS=DATA.details_by_display_key||{};
let selectedKey=null;
const esc=v=>String(v??"—");
const fmt=v=>v==null?"—":Number(v).toFixed(2);
const tag=v=>'<span class="tag">'+esc(v)+'</span>';
document.getElementById("verify").textContent=
 "验证："+esc(DATA.source?.verification_status)+" ｜ 状态："+esc(DATA.summary?.status)+
 " ｜ 交易日："+esc(DATA.summary?.trade_date);
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
function renderChart(detail,queue){
 const host=document.getElementById("chart"); host.innerHTML="";
 if(!detail){host.innerHTML='<div class="error">该候选没有 portable detail。</div>';return}
 const allBars=(detail.bars||[]).filter(x=>x&&x.index!=null);
 const p=detail.pattern||{}, pts=(p.points||[]).filter(x=>x&&x.index!=null&&x.price!=null);
 if(!allBars.length||!pts.length){host.innerHTML='<div class="error">图形数据不完整。</div>';return}
 const minP=Math.min(...pts.map(x=>Number(x.index))), maxP=Math.max(...pts.map(x=>Number(x.index)));
 let bars=allBars.filter(x=>Number(x.index)>=minP-20 && Number(x.index)<=maxP+45);
 if(bars.length<20) bars=allBars.slice(Math.max(0,allBars.length-120));
 const W=1120,H=520,L=62,R=20,T=24,B=42,pw=W-L-R,ph=H-T-B;
 const minI=Math.min(...bars.map(x=>Number(x.index))), maxI=Math.max(...bars.map(x=>Number(x.index))), spanI=Math.max(1,maxI-minI);
 const life=p.source_lifecycle||{}, prz=p.prz||{};
 let zprzLow=life.source_prz_low, zprzHigh=life.source_prz_high;
 if(zprzLow==null && prz.source_prz){zprzLow=prz.source_prz.price_low;zprzHigh=prz.source_prz.price_high}
 const extra=[queue?.next_key_price,zprzLow,zprzHigh,...pts.map(x=>Number(x.price))].filter(v=>v!=null&&Number.isFinite(Number(v))).map(Number);
 let lo=Math.min(...bars.map(x=>Number(x.low)),...extra), hi=Math.max(...bars.map(x=>Number(x.high)),...extra);
 const pad=Math.max((hi-lo)*.08,Math.abs(hi)*.01,.01); lo-=pad;hi+=pad; const spanP=Math.max(.01,hi-lo);
 const X=i=>L+(Number(i)-minI)/spanI*pw, Y=v=>T+(hi-Number(v))/spanP*ph;
 const svg=svgEl("svg",{viewBox:`0 0 ${W} ${H}`,role:"img","aria-label":"便携谐波K线图"});
 svg.appendChild(svgEl("rect",{x:0,y:0,width:W,height:H,fill:"#fff"}));
 for(let g=0;g<6;g++){const val=lo+spanP*g/5, yy=Y(val);svg.appendChild(svgEl("line",{x1:L,x2:W-R,y1:yy,y2:yy,stroke:"#edf0f5"}));svg.appendChild(svgEl("text",{x:L-7,y:yy+4,"text-anchor":"end","font-size":11,fill:"#677287"},fmt(val)))}
 if(zprzLow!=null&&zprzHigh!=null){const y1=Y(Math.max(zprzLow,zprzHigh)),y2=Y(Math.min(zprzLow,zprzHigh));svg.appendChild(svgEl("rect",{x:L,y:y1,width:pw,height:Math.max(2,y2-y1),fill:"#dfe7f2","fill-opacity":.65}));svg.appendChild(svgEl("text",{x:L+6,y:y1+14,"font-size":11,fill:"#53647b"},"Source PRZ "+fmt(zprzLow)+"–"+fmt(zprzHigh)))}
 const step=pw/Math.max(1,bars.length), cw=Math.max(1,Math.min(6,step*.6));
 for(const b of bars){const x=X(b.index),yo=Y(b.open),yc=Y(b.close),yh=Y(b.high),yl=Y(b.low);svg.appendChild(svgEl("line",{x1:x,x2:x,y1:yh,y2:yl,stroke:"#626f82","stroke-width":1}));svg.appendChild(svgEl("rect",{x:x-cw/2,y:Math.min(yo,yc),width:cw,height:Math.max(1,Math.abs(yc-yo)),fill:Number(b.close)>=Number(b.open)?"#ffffff":"#6d7889",stroke:"#5f6b7c","stroke-width":1}))}
 const visiblePts=pts.filter(x=>Number(x.index)>=minI&&Number(x.index)<=maxI);
 if(visiblePts.length>1){svg.appendChild(svgEl("polyline",{points:visiblePts.map(x=>X(x.index)+","+Y(x.price)).join(" "),fill:"none",stroke:"#26364d","stroke-width":2.4}))}
 for(const q of visiblePts){svg.appendChild(svgEl("circle",{cx:X(q.index),cy:Y(q.price),r:4.5,fill:"#fff",stroke:"#26364d","stroke-width":2}));svg.appendChild(svgEl("text",{x:X(q.index),y:Y(q.price)-9,"text-anchor":"middle","font-size":11,"font-weight":"600",fill:"#26364d"},esc(q.label)+" "+fmt(q.price)))}
 const events=[
  ["source_terminal_bar","T-Bar"],["execution_start_bar","T+1"],["type_i_t1_bar","T1"],["type_i_t2_bar","T2"],
  ["type_ii_terminal_bar","Type-II T-Bar"],["reversal_exit_after_type_ii_bar","II Exit"]
 ];
 for(const [field,label] of events){const idx=life[field];if(idx==null||Number(idx)<minI||Number(idx)>maxI)continue;const xx=X(idx);svg.appendChild(svgEl("line",{x1:xx,x2:xx,y1:T,y2:H-B,stroke:"#98a6b8","stroke-dasharray":"4 4"}));svg.appendChild(svgEl("text",{x:xx+4,y:T+14,"font-size":10,fill:"#6b788b"},label))}
 if(queue?.next_key_price!=null){const yy=Y(queue.next_key_price);svg.appendChild(svgEl("line",{x1:X(maxP),x2:W-R,y1:yy,y2:yy,stroke:"#64748b","stroke-width":1.6,"stroke-dasharray":"7 5"}));svg.appendChild(svgEl("text",{x:W-R-4,y:yy-5,"text-anchor":"end","font-size":11,fill:"#526176"},"下一关键价 "+fmt(queue.next_key_price)))}
 svg.appendChild(svgEl("text",{x:L,y:H-12,"font-size":11,fill:"#69758a"},esc(bars[0]?.trade_date)));
 svg.appendChild(svgEl("text",{x:W-R,y:H-12,"text-anchor":"end","font-size":11,fill:"#69758a"},esc(bars[bars.length-1]?.trade_date)));
 host.appendChild(svg);
}
function selectItem(key){
 selectedKey=key;renderList();
 const wrap=ITEMS.find(x=>x.display_key===key), q=wrap?.queue||{}, d=DETAILS[key];
 document.getElementById("title").textContent=esc(q.instrument_id)+" · "+esc(q.pattern_id)+" · S"+esc(q.scale);
 if(!d){
   document.getElementById("summary").innerHTML='<div class="error">portable detail 失败：'+esc(wrap?.detail_error)+'</div>';
   document.getElementById("notes").textContent="";
   renderChart(null,q);return;
 }
 const p=d.pattern||{}, life=p.source_lifecycle||{};
 document.getElementById("summary").innerHTML='<div class="detail-grid">'+
  '<div><span class="muted">Action / Lifecycle</span><br>'+tag(q.action_state)+tag(q.lifecycle_state)+'</div>'+
  '<div><span class="muted">当前判断</span><br>'+esc(q.current_position)+'</div>'+
  '<div><span class="muted">先看</span><br>'+esc(q.first_watch)+'</div>'+
  '<div><span class="muted">下一关键</span><br><b>'+fmt(q.next_key_price)+'</b><br>'+esc(q.next_key_price_role)+'</div>'+
  '<div><span class="muted">Source PRZ</span><br>'+fmt(life.source_prz_low)+' – '+fmt(life.source_prz_high)+'</div>'+
  '<div><span class="muted">阻断条件</span><br>'+esc(q.upgrade_blocker)+'</div></div>';
 document.getElementById("notes").textContent="节点："+(p.points||[]).map(x=>esc(x.label)+"="+fmt(x.price)).join("  ｜  ")+"\n"+
   "提醒："+esc((q.context_cautions||[]).join("；"))+"\n"+
   "说明：形成中结构只画 transport 中已经存在的真实节点；虚线仅表示下一关键价导引，不伪造未来 D 点或预测腿。";
 renderChart(d,q);
}
function hay(x){return JSON.stringify(x).toLowerCase()}
function renderList(){
 const term=document.getElementById("search").value.trim().toLowerCase();
 const filtered=ITEMS.filter(x=>!term||hay(x).includes(term));
 document.getElementById("items").innerHTML=filtered.map(x=>{const q=x.queue||{};return '<button class="item '+(x.display_key===selectedKey?'active':'')+'" data-key="'+esc(x.display_key).replace(/"/g,"&quot;")+'"><div class="top"><b>'+esc(q.instrument_id)+'</b><span>'+(x.detail_available?'图形✓':'图形×')+'</span></div><div>'+tag(q.pattern_id)+tag(q.action_state)+tag(q.lifecycle_state)+'</div><div class="muted">'+esc(q.current_position)+'</div></button>'}).join("")||'<div class="muted">无匹配候选</div>';
 for(const el of document.querySelectorAll(".item")) el.addEventListener("click",()=>selectItem(el.dataset.key));
}
document.getElementById("search").addEventListener("input",renderList);
renderList();
const first=ITEMS.find(x=>x.detail_available)||ITEMS[0]; if(first)selectItem(first.display_key);
</script>
</body></html>"""
    return template.replace("__DATA__", encoded)


def write_portable_pattern_workspace(
    *,
    bundle_path: str | Path,
    json_output: str | Path,
    html_output: str | Path,
) -> dict[str, Any]:
    inspection = build_handoff_v4_inspection(bundle_path)
    json_path = Path(json_output)
    html_path = Path(html_output)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(
            inspection,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    html_path.write_text(
        build_portable_visual_workspace_html_v2(inspection),
        encoding="utf-8",
    )
    return {
        "status": "ready",
        "bundle_path": str(bundle_path),
        "json_output": str(json_path),
        "html_output": str(html_path),
        "summary": inspection.get("summary"),
        "contract": inspection.get("contract"),
        "visual_semantics_version": 2,
    }
