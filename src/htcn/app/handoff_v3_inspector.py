from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
import zipfile
import io

from htcn.app.daily_handoff_v3 import verify_daily_handoff_bundle_v3


INSPECTOR_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class HandoffV3InspectorContract:
    version: int = 1
    semantics: str = "portable_read_only_review_workspace"
    source_bundle_schema: int = 3
    requires_market_database: bool = False
    imports_product_state: bool = False
    writes_operator_queue: bool = False
    writes_operator_history: bool = False
    writes_review_journal: bool = False
    writes_m4_evidence: bool = False
    creates_review_events: bool = False
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


def _role_map(manifest: dict[str, Any]) -> dict[str, list[str]]:
    roles: dict[str, list[str]] = {}
    for record in manifest.get("files") or []:
        if not isinstance(record, dict):
            continue
        role = str(record.get("role") or "")
        arcname = str(record.get("arcname") or "")
        if role and arcname:
            roles.setdefault(role, []).append(arcname)
    return roles


def _single_role(
    archive: zipfile.ZipFile,
    roles: dict[str, list[str]],
    role: str,
    *,
    required: bool = False,
) -> tuple[str, bytes] | None:
    members = roles.get(role, [])
    if not members:
        if required:
            raise RuntimeError(f"required_role_missing:{role}")
        return None
    if len(members) != 1:
        raise RuntimeError(f"role_not_singleton:{role}")
    name = members[0]
    return name, archive.read(name)


def _json_role(
    archive: zipfile.ZipFile,
    roles: dict[str, list[str]],
    role: str,
    *,
    required: bool = False,
) -> dict[str, Any] | None:
    member = _single_role(archive, roles, role, required=required)
    if member is None:
        return None
    name, data = member
    return _read_json_bytes(data, label=role + ":" + name)


def _nested_v2_payload(data: bytes) -> tuple[dict[str, Any], dict[str, Any]]:
    with zipfile.ZipFile(io.BytesIO(data), "r") as archive:
        manifest = _read_json_bytes(
            archive.read("daily-handoff-manifest.json"),
            label="nested_v2_manifest",
        )
        roles = _role_map(manifest)
        current_snapshot = _json_role(
            archive,
            roles,
            "m5_current_product_snapshot",
            required=manifest.get("m5_product_ready") is True,
        )
        previous_snapshot = _json_role(
            archive,
            roles,
            "m5_previous_product_snapshot",
        )
        product_report = _json_role(
            archive,
            roles,
            "m5_final_product_report",
        )
        pipeline = _json_role(
            archive,
            roles,
            "pipeline_summary",
            required=True,
        )
    return manifest, {
        "pipeline": pipeline,
        "product_report": product_report,
        "current_product_snapshot": current_snapshot,
        "previous_product_snapshot": previous_snapshot,
    }


def _queue_from_snapshot(snapshot: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(snapshot, dict):
        return None
    queue = snapshot.get("queue")
    return dict(queue) if isinstance(queue, dict) else None


def _item_key(item: dict[str, Any]) -> tuple[str, str]:
    return (
        str(item.get("instrument_id") or ""),
        str(item.get("display_key") or ""),
    )


def _flatten_digest_items(digest: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(digest, dict):
        return []
    rows: list[dict[str, Any]] = []
    for section in digest.get("workflow_sections") or []:
        if not isinstance(section, dict):
            continue
        workflow = str(section.get("workflow") or section.get("action_state") or "")
        for item in section.get("items") or []:
            if isinstance(item, dict):
                row = dict(item)
                row["_workflow"] = workflow
                rows.append(row)
    return rows


def _review_items(session: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(session, dict):
        return []
    rows: list[dict[str, Any]] = []
    for section in session.get("workflow_sections") or []:
        if not isinstance(section, dict):
            continue
        for item in section.get("items") or []:
            if isinstance(item, dict):
                rows.append(dict(item))
    return rows


def build_handoff_v3_inspection(bundle_path: str | Path) -> dict[str, Any]:
    """Verify and inspect a Phase-14 v3 handoff using only bytes inside the ZIP.

    This function never imports transported state into local product stores. The existing
    v3 verifier remains the authority gate; inspection begins only after it returns valid.
    """

    source = Path(bundle_path)
    checked = verify_daily_handoff_bundle_v3(source)
    if checked.status != "valid":
        raise RuntimeError(
            "handoff_v3_invalid:" + ",".join(checked.errors)
        )

    with zipfile.ZipFile(source, "r") as archive:
        manifest = _read_json_bytes(
            archive.read("daily-handoff-v3-manifest.json"),
            label="handoff_v3_manifest",
        )
        roles = _role_map(manifest)
        base = _single_role(
            archive,
            roles,
            "m5_handoff_v2_base",
            required=True,
        )
        assert base is not None
        _, base_bytes = base
        nested_manifest, nested = _nested_v2_payload(base_bytes)

        current_history = _json_role(
            archive,
            roles,
            "m5_current_history_record",
        )
        previous_history = _json_role(
            archive,
            roles,
            "m5_previous_history_record",
        )
        previous_same_day_history = _json_role(
            archive,
            roles,
            "m5_previous_same_day_history_record",
        )
        digest = _json_role(
            archive,
            roles,
            "m5_daily_review_digest",
        )
        review_session = _json_role(
            archive,
            roles,
            "m5_review_session_snapshot",
        )
        review_events = [
            _read_json_bytes(
                archive.read(name),
                label="m5_review_journal_event:" + name,
            )
            for name in roles.get("m5_review_journal_event", [])
        ]

    current_snapshot = nested.get("current_product_snapshot")
    previous_snapshot = nested.get("previous_product_snapshot")
    current_queue = _queue_from_snapshot(current_snapshot)
    previous_queue = _queue_from_snapshot(previous_snapshot)

    if current_queue is None and isinstance(current_history, dict):
        queue = current_history.get("queue_snapshot")
        if isinstance(queue, dict):
            current_queue = dict(queue)

    current_items = list((current_queue or {}).get("items") or [])
    digest_items = _flatten_digest_items(digest)
    session_items = _review_items(review_session)
    active_follow_ups = list(
        (review_session or {}).get("active_follow_ups") or []
    )
    m4_summary = nested_manifest.get("m4_nested_bundle_verification")

    summary = {
        "transport_status": manifest.get("status"),
        "trade_date": (
            (current_queue or {}).get("as_of_trade_date")
            or (manifest.get("history_binding") or {}).get("trade_date")
            or (nested_manifest.get("product_binding") or {}).get("trade_date")
        ),
        "m5_product_ready": manifest.get("m5_product_ready") is True,
        "m5_history_ready": manifest.get("m5_history_ready") is True,
        "m5_review_digest_ready": manifest.get("m5_review_digest_ready") is True,
        "m4_research_ready": manifest.get("m4_research_ready") is True,
        "candidate_count": len(current_items),
        "candidate_instrument_count": len({
            str(item.get("instrument_id") or "")
            for item in current_items
            if isinstance(item, dict) and item.get("instrument_id")
        }),
        "action_state_counts": dict(
            (current_queue or {}).get("action_state_counts") or {}
        ),
        "lifecycle_state_counts": dict(
            (current_queue or {}).get("lifecycle_state_counts") or {}
        ),
        "daily_change_count": (
            None if not isinstance(digest, dict)
            else digest.get("change_count")
        ),
        "review_state_counts": dict(
            (review_session or {}).get("review_state_counts") or {}
        ),
        "active_follow_up_count": len(active_follow_ups),
        "current_history_observation_id": (
            None if not isinstance(current_history, dict)
            else current_history.get("observation_id")
        ),
        "previous_history_observation_id": (
            None if not isinstance(previous_history, dict)
            else previous_history.get("observation_id")
        ),
        "review_event_count": len(review_events),
        "m4_nested_status": (
            None if not isinstance(m4_summary, dict)
            else m4_summary.get("status")
        ),
    }

    return {
        "schema_version": INSPECTOR_SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "contract": HandoffV3InspectorContract().as_payload(),
        "source": {
            "bundle_path": str(source),
            "bundle_schema_version": checked.schema_version,
            "bundle_file_count": checked.file_count,
            "verification_status": checked.status,
            "verification_errors": list(checked.errors),
            "verification_warnings": list(checked.warnings),
        },
        "summary": summary,
        "transport_manifest": manifest,
        "nested_v2_manifest": nested_manifest,
        "pipeline": nested.get("pipeline"),
        "product_report": nested.get("product_report"),
        "current_product_snapshot": current_snapshot,
        "previous_product_snapshot": previous_snapshot,
        "current_queue": current_queue,
        "previous_queue": previous_queue,
        "current_history": current_history,
        "previous_history": previous_history,
        "previous_same_day_history": previous_same_day_history,
        "daily_review_digest": digest,
        "review_session": review_session,
        "review_events": review_events,
        "indexes": {
            "current_queue_items": current_items,
            "digest_items": digest_items,
            "review_items": session_items,
            "active_follow_ups": active_follow_ups,
        },
        "authoritative_evidence": False,
        "writes_m4_evidence": False,
        "imports_product_state": False,
        "creates_review_events": False,
        "is_trade_instruction": False,
        "alpha_inference_allowed": False,
        "predictive_score_used": False,
        "historical_outcome_used_for_ranking": False,
    }


def filter_handoff_v3_inspection(
    inspection: dict[str, Any],
    *,
    instrument_id: str | None = None,
    display_key: str | None = None,
) -> dict[str, Any]:
    """Add a read-only drill-down selection without mutating the inspection payload."""

    result = deepcopy(inspection)
    normalized_instrument = str(instrument_id or "").strip()
    normalized_key = str(display_key or "").strip()

    def selected(item: object) -> bool:
        if not isinstance(item, dict):
            return False
        if normalized_instrument and str(item.get("instrument_id") or "") != normalized_instrument:
            return False
        if normalized_key and str(item.get("display_key") or "") != normalized_key:
            return False
        return bool(normalized_instrument or normalized_key)

    indexes = inspection.get("indexes") or {}
    result["drilldown"] = {
        "instrument_id": normalized_instrument or None,
        "display_key": normalized_key or None,
        "queue_items": [
            deepcopy(item)
            for item in indexes.get("current_queue_items") or []
            if selected(item)
        ],
        "digest_items": [
            deepcopy(item)
            for item in indexes.get("digest_items") or []
            if selected(item)
        ],
        "review_items": [
            deepcopy(item)
            for item in indexes.get("review_items") or []
            if selected(item)
        ],
        "active_follow_ups": [
            deepcopy(item)
            for item in indexes.get("active_follow_ups") or []
            if selected(item)
        ],
    }
    return result


def build_portable_review_html(inspection: dict[str, Any]) -> str:
    """Render a self-contained Chinese read-only workspace with no external assets."""

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
<title>HT-CN Handoff v3 便携复盘工作区</title>
<style>
:root{font-family:Inter,"PingFang SC","Microsoft YaHei",sans-serif;color:#172033;background:#f5f7fb}
*{box-sizing:border-box}body{margin:0}.shell{max-width:1500px;margin:auto;padding:24px}
h1{margin:0 0 6px;font-size:28px}h2{margin:0 0 12px;font-size:18px}p{line-height:1.55}
.muted{color:#657089}.banner{padding:12px 14px;border:1px solid #d8deea;border-radius:12px;background:#fff;margin:14px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:14px 0}
.card{background:#fff;border:1px solid #dfe4ee;border-radius:12px;padding:14px;min-width:0}.card b{font-size:22px}
.toolbar{display:flex;gap:10px;flex-wrap:wrap;margin:18px 0}.toolbar input{flex:1;min-width:280px;padding:11px 12px;border:1px solid #cbd3e1;border-radius:9px}
button{padding:10px 14px;border:1px solid #cbd3e1;background:#fff;border-radius:9px;cursor:pointer}
section{margin:18px 0}.table-wrap{overflow:auto;background:#fff;border:1px solid #dfe4ee;border-radius:12px}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:9px 10px;border-bottom:1px solid #edf0f5;text-align:left;vertical-align:top}th{position:sticky;top:0;background:#f9fafc}
.tag{display:inline-block;padding:2px 7px;border-radius:999px;background:#eef2f8;margin:2px 4px 2px 0;font-size:12px}
.detail{white-space:pre-wrap;word-break:break-word}.empty{padding:18px;color:#7a8498}
.follow{border-left:3px solid #98a7bd;padding-left:10px;margin:8px 0}
footer{margin:28px 0;color:#657089;font-size:12px}
</style>
</head>
<body>
<div class="shell">
<h1>HT-CN Handoff v3 便携复盘工作区</h1>
<div class="muted">只读 Inspector · 不依赖本机行情库 · 不导入 Queue/History/Review Journal</div>
<div class="banner" id="verify"></div>
<div class="grid" id="summary"></div>
<div class="toolbar">
<input id="search" placeholder="按证券代码、display key、形态、状态搜索">
<button id="clear">清空</button>
</div>
<section><h2>当前 Operator Queue</h2><div class="table-wrap"><table><thead><tr>
<th>证券</th><th>形态</th><th>Action / Lifecycle</th><th>当前判断</th><th>先看</th><th>下一关键</th><th>阻断/提醒</th>
</tr></thead><tbody id="queue"></tbody></table></div></section>
<section><h2>今日变化 / Digest</h2><div id="digest" class="card"></div></section>
<section><h2>持续跟踪</h2><div id="followups" class="card"></div></section>
<section><h2>历史与证据链</h2><div id="history" class="card detail"></div></section>
<footer>本工作区仅展示 transport 中已冻结的产品观察信息；不生成评分、收益推断或买卖指令。</footer>
</div>
<script type="application/json" id="htcn-data">__DATA__</script>
<script>
const DATA=JSON.parse(document.getElementById("htcn-data").textContent);
const I=DATA.indexes||{}, S=DATA.summary||{}, C=DATA.contract||{};
const esc=v=>String(v??"—");
const money=v=>v==null?"—":Number(v).toFixed(2);
const tag=v=>'<span class="tag">'+esc(v)+'</span>';
document.getElementById("verify").textContent =
  "验证状态："+esc(DATA.source?.verification_status)+" ｜ v3 文件："+esc(DATA.source?.bundle_file_count)+
  " ｜ Transport："+esc(S.transport_status)+" ｜ 交易日："+esc(S.trade_date);
const cards=[
 ["候选",S.candidate_count],["涉及证券",S.candidate_instrument_count],
 ["今日变化",S.daily_change_count],["持续跟踪",S.active_follow_up_count],
 ["History",S.m5_history_ready?"READY":"降级"],["M4 research",S.m4_research_ready?"READY":"未就绪"]
];
document.getElementById("summary").innerHTML=cards.map(x=>'<div class="card"><div class="muted">'+x[0]+'</div><b>'+esc(x[1])+'</b></div>').join("");
function hay(x){return JSON.stringify(x).toLowerCase()}
function render(){
 const q=document.getElementById("search").value.trim().toLowerCase();
 const items=(I.current_queue_items||[]).filter(x=>!q||hay(x).includes(q));
 document.getElementById("queue").innerHTML=items.length?items.map(x=>'<tr>'+
  '<td><b>'+esc(x.instrument_id)+'</b><div class="muted">'+esc(x.display_key)+'</div></td>'+
  '<td>'+tag(x.pattern_id)+tag(x.direction)+'<div>S'+esc(x.scale)+' · '+esc(x.pattern_state)+'</div></td>'+
  '<td>'+tag(x.action_state)+tag(x.lifecycle_state)+'</td>'+
  '<td>'+esc(x.current_position)+'</td>'+
  '<td>'+esc(x.first_watch)+'</td>'+
  '<td>'+money(x.next_key_price)+'<div class="muted">'+esc(x.next_key_price_role)+'</div><div>'+esc(x.next_watch)+'</div></td>'+
  '<td>'+esc(x.upgrade_blocker)+'<div class="muted">'+esc((x.context_cautions||[]).join("；"))+'</div></td></tr>').join("")
  :'<tr><td colspan="7" class="empty">没有匹配项目</td></tr>';
 const changes=(I.digest_items||[]).filter(x=>!q||hay(x).includes(q));
 document.getElementById("digest").innerHTML=changes.length?changes.map(x=>
  '<div class="follow"><b>'+esc(x.instrument_id||x.display_key)+'</b> '+tag(x._workflow)+
  '<div>'+esc((x.change_types||[]).join(" / ")||x.summary||x.change_type)+'</div>'+
  '<div class="muted">'+esc(x.display_key)+'</div></div>').join("")
  :'<div class="empty">当前筛选下无变化</div>';
 const follows=(I.active_follow_ups||[]).filter(x=>!q||hay(x).includes(q));
 document.getElementById("followups").innerHTML=follows.length?follows.map(x=>
  '<div class="follow"><b>'+esc(x.instrument_id)+'</b> '+tag(x.review_state||"follow_up")+
  '<div>'+esc(x.note)+'</div><div class="muted">'+esc(x.display_key)+' ｜ 来源 '+esc(x.source_trade_date)+'</div></div>').join("")
  :'<div class="empty">当前没有持续跟踪项</div>';
}
document.getElementById("search").addEventListener("input",render);
document.getElementById("clear").addEventListener("click",()=>{document.getElementById("search").value="";render()});
document.getElementById("history").textContent =
 "当前 observation: "+esc(S.current_history_observation_id)+"\n"+
 "上一交易日 observation: "+esc(S.previous_history_observation_id)+"\n"+
 "Review event 数: "+esc(S.review_event_count)+"\n"+
 "M4 nested status: "+esc(S.m4_nested_status)+"\n"+
 "Inspector contract: read-only="+esc(!C.imports_product_state)+", market DB required="+esc(C.requires_market_database);
render();
</script>
</body></html>"""
    return template.replace("__DATA__", encoded)


def write_portable_review_workspace(
    *,
    bundle_path: str | Path,
    json_output: str | Path,
    html_output: str | Path,
) -> dict[str, Any]:
    inspection = build_handoff_v3_inspection(bundle_path)
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
        ) + "\n",
        encoding="utf-8",
    )
    html_path.write_text(
        build_portable_review_html(inspection),
        encoding="utf-8",
    )
    return {
        "status": "ready",
        "bundle_path": str(bundle_path),
        "json_output": str(json_path),
        "html_output": str(html_path),
        "summary": inspection.get("summary"),
        "contract": inspection.get("contract"),
    }
