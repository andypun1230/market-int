#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
BACKEND_ROOT=Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path: sys.path.insert(0,str(BACKEND_ROOT))
from app.securities.registry import SECTOR_BY_ID, canonical_sector_id
from app.sector_snapshots.service import get_sector_snapshot_service, reset_sector_snapshot_service

parser=argparse.ArgumentParser(description="Validate Phase 4.4C durable sector intelligence")
parser.add_argument("--test",action="store_true"); parser.add_argument("--live",action="store_true"); parser.add_argument("--warm",action="store_true"); parser.add_argument("--restart",action="store_true"); parser.add_argument("--json-output",type=Path)
args=parser.parse_args(); failures=[]; conditions=[]; checks={}
aliases={"Technology":"information_technology","Information Technology":"information_technology","Tech":"information_technology","Consumer Cyclical":"consumer_discretionary","Consumer Discretionary":"consumer_discretionary","Healthcare":"health_care","Health Care":"health_care","Communication Services":"communication_services","Communications":"communication_services"}
checks["taxonomy"] = len(SECTOR_BY_ID)==11 and all(canonical_sector_id(name)==expected for name,expected in aliases.items())
if not checks["taxonomy"]: failures.append("taxonomy_or_aliases_invalid")
if args.test:
    result=subprocess.run([sys.executable,"-m","unittest","discover","-s","tests","-p","test_sector_snapshot.py"],cwd=BACKEND_ROOT,capture_output=True,text=True)
    checks["sector_snapshot_tests"]={"passed":result.returncode==0,"output":result.stdout[-1000:]+result.stderr[-1000:]}
    if result.returncode: failures.append("sector_snapshot_regressions_failed")
if args.live:
    snapshot=get_sector_snapshot_service().latest()
    checks["live_snapshot"]={"snapshot_id":snapshot.snapshot_id if snapshot else None,"status":snapshot.status if snapshot else "unavailable","source_state":snapshot.source_state if snapshot else "unavailable","coverage":snapshot.coverage if snapshot else None}
    if not snapshot or snapshot.source_state!="live" or snapshot.status not in {"complete","partial"}: failures.append("live_snapshot_not_ready")
    elif snapshot.coverage["etf_coverage_ratio"]<1: failures.append("etf_history_not_ready")
    elif snapshot.coverage["constituent_coverage_ratio"]<.5: failures.append("constituent_coverage_below_partial")
    elif snapshot.status!="complete": conditions.append("snapshot_partial")
    if snapshot:
        periods=("return_1d","return_1w","return_1m","return_3m","return_6m","return_1y")
        checks["canonical_sector_rows"]={"schema_version":snapshot.schema_version,"count":len(snapshot.sectors),"ranks":[row.get("rank") for row in snapshot.sectors],"returns_complete":all(all(row.get("price_metrics",{}).get(period) is not None for period in periods) for row in snapshot.sectors)}
        if snapshot.schema_version<2 or len(snapshot.sectors)!=11 or [row.get("rank") for row in snapshot.sectors]!=list(range(1,12)) or not checks["canonical_sector_rows"]["returns_complete"]: failures.append("canonical_snapshot_fields_invalid")
if args.restart:
    before=get_sector_snapshot_service().latest(); reset_sector_snapshot_service(); after=get_sector_snapshot_service().latest()
    checks["restart"]={"before":before.snapshot_id if before else None,"after":after.snapshot_id if after else None}
    if not before or not after or before.snapshot_id!=after.snapshot_id: failures.append("restart_persistence_failed")
if args.warm:
    from fastapi.testclient import TestClient
    from unittest.mock import patch
    from main import app
    import time
    paths=["/market/sectors/snapshot/latest","/market/sectors","/market/sectors/rotation","/market/sectors/alerts","/market/sector-dashboard","/market/sectors/summary","/market/sectors/energy","/market/sectors/materials","/market/sectors/Technology"]
    latencies={}
    with TestClient(app) as client, patch("app.providers.polygon_provider.PolygonMarketDataProvider.get_history",side_effect=AssertionError("warm read called provider")):
        for path in paths:
            start=time.perf_counter(); response=client.get(path); latencies[path]={"status":response.status_code,"latency_ms":round((time.perf_counter()-start)*1000,2),"snapshot_id":response.json().get("snapshot_id")}
    checks["warm_reads"]=latencies
    ids={row["snapshot_id"] for row in latencies.values() if row["snapshot_id"]}
    if any(row["status"]!=200 or row["latency_ms"]>=500 for row in latencies.values()) or len(ids)>1: failures.append("warm_read_failed")
    detail_checks={}
    with TestClient(app) as client:
        for sector in ("energy","materials","Technology"):
            body=client.get(f"/market/sectors/{sector}").json()
            detail_checks[sector]={"snapshot_id":body.get("snapshot_id"),"sector_id":(body.get("sector") or {}).get("sector_id"),"constituents":len(body.get("constituents") or []),"has_all_periods":all(period in ((body.get("sector") or {}).get("price_metrics") or {}) for period in ("return_1d","return_1w","return_1m","return_3m","return_6m","return_1y"))}
    checks["detail_routes"]=detail_checks
    if not all(value["snapshot_id"] and value["sector_id"] and value["constituents"] and value["has_all_periods"] for value in detail_checks.values()) or detail_checks["Technology"]["sector_id"]!="information_technology": failures.append("sector_detail_contract_failed")
    with TestClient(app) as client:
        rotation=client.get("/market/sectors/rotation").json()
        breadth=client.get("/market/breadth").json().get("market") or {}
        market_snapshot=client.get("/market/snapshot/latest").json()
        structure=client.get("/market/details/structure").json()
        home=client.get("/home/dashboard").json()
    trails=rotation.get("trails") or {}; series=rotation.get("series") or []
    trail_lengths=[len(item.get("trail_points") or []) for item in series if isinstance(item,dict)]
    checks["rotation_ux"]={"published_source":rotation.get("trail_source"),"series_source":rotation.get("market_trail_source"),"formula_version":rotation.get("formula_version"),"sector_points":len(trails),"series_count":len(series),"history_point_count":rotation.get("history_point_count"),"movement_available":rotation.get("movement_available"),"trail_lengths":trail_lengths}
    if rotation.get("market_trail_source")!="durable_polygon_adjusted_daily_history" or rotation.get("formula_version")!="relative-return-momentum-v1" or len(series)!=33 or not trail_lengths or any(length!=5 for length in trail_lengths): failures.append("rotation_history_contract_failed")
    if any(item.get("current_point") != (item.get("trail_points") or [None])[-1] or any(point.get("is_synthetic") or point.get("source_provider")!="polygon" for point in item.get("trail_points") or []) for item in series if isinstance(item,dict)): failures.append("rotation_series_integrity_failed")
    breadth_id=breadth.get("snapshot_id")
    market_breadth=((market_snapshot.get("sections") or {}).get("breadth") or {}).get("payload") or {}
    structure_breadth=((structure.get("breadth") or {}).get("market") or {})
    home_breadth=((home.get("core") or {}).get("breadth_summary") or {})
    checks["breadth_consistency"]={"breadth_snapshot_id":breadth_id,"market_snapshot_id":market_breadth.get("snapshot_id"),"structure_id":structure_breadth.get("snapshot_id"),"home_id":home_breadth.get("snapshot_id"),"coverage_percent":breadth.get("coverage_percent")}
    if not breadth_id or breadth.get("coverage_percent",0)<=0 or {breadth_id,market_breadth.get("snapshot_id"),structure_breadth.get("snapshot_id"),home_breadth.get("snapshot_id")}!={breadth_id}: failures.append("breadth_snapshot_consistency_failed")
report={"phase":"4.4c","passed":not failures,"failures":failures,"conditions":conditions,"checks":checks}
rendered=json.dumps(report,indent=2,sort_keys=True); print(rendered)
if args.json_output: args.json_output.write_text(rendered+"\n")
raise SystemExit(1 if failures else 0)
