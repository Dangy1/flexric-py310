#!/usr/bin/env bash
# Regression test for the uePositionFile input of scenario-zero (APPWEAVER_SETUP.md §11, fix 7).
# Two short runs (2 gNB + LTE eNB, 4 UEs, simTime 2 s, no xApp):
#   1) ue_index,x,y,z file (0-based, rows out of order, one row without z)
#   2) imsi,x,y file
# Expected: the t=0 rows of ns3_out/ue_position.txt equal the file (x, y within 0.01 m) and the
# UEs still move afterwards (random walk). Usage: tools/regress_ue_positions.sh  (logs in $LOG_DIR)
set -u
export LC_ALL=C
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export LOG_DIR="${LOG_DIR:-/tmp/ns_oran_regress_pos}"
fail=0
check() { if eval "$2"; then echo "PASS $1"; else echo "FAIL $1"; fail=1; fi; }

run() {  # name pos_file
  local name=$1 pos=$2
  "$HERE/stop_sim_stack.sh" >/dev/null 2>&1
  rm -rf "$LOG_DIR/$name"; mkdir -p "$LOG_DIR"
  LOG_DIR="$LOG_DIR/$name" "$HERE/start_sim_stack.sh" -g 2 -u 4 -t 2 -x none -P "$pos" >/dev/null || return 1
  local pid; pid=$(cat "$LOG_DIR/$name/ns3.pid")
  while kill -0 "$pid" 2>/dev/null; do sleep 2; done
  LOG_DIR="$LOG_DIR/$name" "$HERE/stop_sim_stack.sh" >/dev/null 2>&1
  check "$name: ns-3 read the file" "grep -q 'UE positions from $pos' $LOG_DIR/$name/ns3.log"
  # expected imsi,x,y from the input file
  python3 - "$pos" "$LOG_DIR/$name/ns3_out/ue_position.txt" <<'EOF'
import csv, sys
pos_file, trace = sys.argv[1:]
rows = [r for r in csv.reader(open(pos_file)) if r and not r[0].startswith('#')]
off = 0
if not rows[0][0][0].isdigit():
    off = 1 if rows[0][0] == "imsi" else 0
    rows = rows[1:]
want = {int(r[0]) + 1 - off: (float(r[1]), float(r[2])) for r in rows}
t0, later = {}, {}
for r in csv.DictReader(open(trace)):
    if not r["timestamp"].isdigit():
        continue
    t = int(r["timestamp"]) - int(r["simid"])   # sim ms
    (t0 if t == 0 else later).setdefault(int(r["id"]), []).append((float(r["x"]), float(r["y"])))
ok = set(t0) == set(want) and all(abs(t0[i][0][0] - want[i][0]) < 0.01 and abs(t0[i][0][1] - want[i][1]) < 0.01 for i in want)
moved = all(any(abs(x - want[i][0]) > 0.01 or abs(y - want[i][1]) > 0.01 for x, y in later.get(i, [])) for i in want)
for i in sorted(want):
    print(f"  IMSI {i}: file {want[i]}  trace t=0 {t0.get(i, [None])[0]}  last {later.get(i, [None])[-1]}")
print("T0_MATCH" if ok else "T0_MISMATCH")
print("MOVED" if moved else "NOT_MOVED")
EOF
}

P1="$LOG_DIR/pos_index.csv"; P2="$LOG_DIR/pos_imsi.csv"
mkdir -p "$LOG_DIR"
cat > "$P1" <<'EOF'
ue_index,x,y,z
2,2300.5,1800.25,1.5
0,1700,2100,1.5
3,2050.75,2400
1,1950,1950.5,1.5
EOF
cat > "$P2" <<'EOF'
imsi,x,y
1,2600,2000
2,1400,2000
3,2000,2600
4,2000,1400
EOF
out1=$(run index "$P1"); echo "$out1"
grep -q '^FAIL' <<<"$out1" && fail=1
check "index file: t=0 positions equal the file" "grep -q T0_MATCH <<<\"\$out1\""
check "index file: UEs move after t=0" "grep -q '^MOVED' <<<\"\$out1\""
out2=$(run imsi "$P2"); echo "$out2"
grep -q '^FAIL' <<<"$out2" && fail=1
check "imsi file: t=0 positions equal the file" "grep -q T0_MATCH <<<\"\$out2\""
check "imsi file: UEs move after t=0" "grep -q '^MOVED' <<<\"\$out2\""
[[ $fail -eq 0 ]] && echo "ALL PASS" || echo "SOME CHECKS FAILED"
exit $fail
