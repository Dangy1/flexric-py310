#!/bin/bash
# Called by tc_dp_agent_gnb (sm_tc_dp.c) for every E2SM-TC queue control:
#   tc_hook.sh fifo | codel <target_ms> <interval_ms> | ecn_codel <target_ms> <interval_ms>
# Replaces the child qdisc under the bottleneck shaper on dev v0 of the demo's user/network namespace
# (pid in $TC_DP_NS_PID), and logs the change with a wall-clock timestamp to $TC_DP_LOG.
set -u
ns() { nsenter -t "$TC_DP_NS_PID" -U -n --preserve-credentials "$@"; }
# This kernel rejects "qdisc replace" across kinds (pfifo -> codel): delete the child, then add the new one.
swap() { ns tc qdisc del dev v0 parent 1:1 handle 10: 2>/dev/null; ns tc qdisc add dev v0 parent 1:1 handle 10: "$@"; }
case "${1:-}" in
  fifo)      swap pfifo limit "${TC_DP_FIFO_LIMIT:-2000}" ;;
  codel)     swap codel target "${2}ms" interval "${3}ms" noecn ;;
  ecn_codel) swap codel target "${2}ms" interval "${3}ms" ecn ;;
  *) echo "unknown queue control: $*" >&2; exit 2 ;;
esac
rc=$?
printf '%s %s rc=%d\n' "$(date +%s.%N)" "$*" "$rc" >> "${TC_DP_LOG:-/dev/null}"
exit $rc
