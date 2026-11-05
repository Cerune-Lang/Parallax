#!/usr/bin/env python3
"""Run ONLY within the restricted CI container."""
import json
from pathlib import Path
from codegen_eval import grade_source
data=json.loads(Path("/opt/parallax/benchmarks/llm/observations/codegen-2026-11-04.json").read_text())
results=[]
for item in data["records"]:
    result=grade_source(Path("/opt/cerune/cerune"),item["task"],item["response"],timeout=4)
    results.append({**{k:item[k] for k in ("task","condition")},**result})
    print(item["condition"],item["task"],result["passed"],"/",result["total"],"all_pass",result["all_pass"],flush=True)
Path("/results/scores.json").write_text(json.dumps(results,indent=2)+"\n")
print("SUMMARY",json.dumps({x:sum(r["all_pass"] for r in results if r["condition"]==x) for x in ("baseline","spec")}),flush=True)
