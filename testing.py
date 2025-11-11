# from langsmith import Client
# from dotenv import load_dotenv
# import json

# load_dotenv()
# client = Client()

# # Your known trace ID
# # trace_id = "019a3693-3357-72bd-bcfc-ceaf1a272bad"
# trace_id = "019a3732-021b-76ef-b120-14dada44d408"

# # 1. Get the root run
# root_run = client.read_run(run_id=trace_id)
# if not root_run:
#     raise ValueError(f"No run found with trace_id {trace_id}")

# # 2. Compute E2E latency
# e2e_latency = (root_run.end_time - root_run.start_time).total_seconds()

# # 3. Get *all* runs for this trace (root + nested)
# all_runs = list(client.list_runs(trace_id=trace_id))

# # 4. Compute tool latencies (any run that’s not the root)
# tool_latencies = []
# for run in all_runs:
#     if run.id != root_run.id and run.end_time and run.start_time:
#         latency = (run.end_time - run.start_time).total_seconds()
#         tool_latencies.append({
#             "name": run.name,
#             "id": str(run.id),
#             "parent_id": str(run.parent_run_id) if run.parent_run_id else None,
#             "latency_sec": latency
#         })

# # 5. Optionally, group by tool name (e.g., multiple Tavily calls)
# latency_by_tool = {}
# for r in tool_latencies:
#     latency_by_tool.setdefault(r["name"], []).append(r["latency_sec"])

# latency_summary = {
#     name: {
#         "count": len(times),
#         "total_latency_sec": sum(times),
#         "avg_latency_sec": sum(times) / len(times)
#     }
#     for name, times in latency_by_tool.items()
# }

# # 6. Aggregate totals
# total_tool_latency = sum(sum(times) for times in latency_by_tool.values())
# percentage = (total_tool_latency / e2e_latency * 100) if e2e_latency > 0 else None

# overview = {
#     "trace_id": str(trace_id),
#     "e2e_latency_sec": e2e_latency,
#     "total_tool_latency_sec": total_tool_latency,
#     "tool_to_e2e_ratio_percent": percentage,
#     "tool_breakdown": latency_summary,
# }

# print(json.dumps(overview, indent=2, default=str))

# with open("langsmith_latency_summary.json", "w") as f:
#     json.dump(overview, f, indent=2, default=str)

from langsmith import Client
from dotenv import load_dotenv
import json
load_dotenv()

client = Client()
trace_id = "019a3693-3357-72bd-bcfc-ceaf1a272bad"

# 1) Get root run
root_runs = list(client.list_runs(trace_id=trace_id, is_root=True))
if not root_runs:
    raise ValueError(f"No root run found for trace {trace_id}")
root_run = root_runs[0]
e2e_latency = (root_run.end_time - root_run.start_time).total_seconds()
# 2) Get all runs in this trace
all_runs = list(client.list_runs(trace_id=trace_id))
# 3) Filter for *all Tavily Search* runs
tool_runs = [
    r for r in all_runs
    if r.name == "tavily_search" and r.start_time and r.end_time
]
# Safety check: print all found Tavily run IDs
print(f":jigsaw: Found {len(tool_runs)} Tavily Search runs in trace {trace_id}:")
for r in tool_runs:
    print(f"  - {r.id}  ({r.start_time.isoformat()} → {r.end_time.isoformat()})")
# 4) Extract and sort intervals
intervals = sorted(
    [
        {
            "name": r.name,
            "id": str(r.id),
            "start_time_iso": r.start_time.isoformat(),
            "end_time_iso": r.end_time.isoformat(),
            "start_ts": r.start_time.timestamp(),
            "end_ts": r.end_time.timestamp(),
            "duration_sec": (r.end_time - r.start_time).total_seconds(),
        }
        for r in tool_runs
    ],
    key=lambda x: x["start_ts"],
)
# 5) Merge
merged = []
for item in intervals:
    start, end = item["start_ts"], item["end_ts"]
    if not merged:
        merged.append([start, end])
    else:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1][1] = max(last_end, end)
        else:
            merged.append([start, end])
# 6) Compute totals
total_tool_latency = sum(end - start for start, end in merged)
percentage = (total_tool_latency / e2e_latency * 100) if e2e_latency > 0 else None
# 7) Save summary + run IDs for verification
overview = {
    "trace_id": trace_id,
    "root_run_id": str(root_run.id),
    "e2e_latency_sec": e2e_latency,
    "total_tool_latency_sec": total_tool_latency,
    "tool_to_e2e_ratio_percent": percentage,
    "tool_runs_count": len(intervals),
    "tavily_run_ids": [r["id"] for r in intervals],
    "intervals": intervals,
    "merged_intervals": merged
}
output_file = "langsmith_tool_intervals.json"
with open(output_file, "w") as f:
    json.dump(overview, f, indent=2)
print(f"\n:white_check_mark: Saved {len(intervals)} Tavily runs ({len(merged)} merged intervals) to {output_file}")