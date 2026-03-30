#!/usr/bin/env python3
import argparse
import json
import random
import re
import signal
import sys
import threading
import time
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
SDK_CANDIDATES = [
    THIS_DIR,
    THIS_DIR.parents[2] / "build" / "examples" / "xApp" / "python3",
    THIS_DIR.parents[2] / "build" / "src" / "xApp" / "swig",
]
for candidate in SDK_CANDIDATES:
    candidate_str = str(candidate)
    if candidate.exists() and candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

import xapp_sdk as ric


STOP_REQUESTED = False


def _on_sigint(_sig, _frame):
    global STOP_REQUESTED
    STOP_REQUESTED = True
    print("\nStopping RL xApp gracefully...")


def _extract_rru_util(records):
    values = []
    for rec in records:
        text = str(rec)
        if "meas=RRU.PrbTotDl" not in text and "meas=RRU.PrbTotUl" not in text:
            continue
        nums = re.findall(r"[-+]?\d+(?:\.\d+)?", text)
        if not nums:
            continue
        value = abs(float(nums[-1]))
        values.append(min(value, 100.0))
    if not values:
        return None
    return round(sum(values) / len(values), 3)


class KPMCallback(ric.kpm_moni_cb):
    def __init__(self, shared_state):
        super().__init__()
        self.shared_state = shared_state

    def handle(self, msg):
        records = [str(rec) for rec in msg.records]
        util = _extract_rru_util(records)
        with self.shared_state["lock"]:
            self.shared_state["records"] = records[-20:]
            self.shared_state["last_update_ts"] = time.time()
            if util is not None:
                self.shared_state["util"] = util


def _create_slice(slice_params):
    s = ric.fr_slice_t()
    s.id = slice_params["id"]
    s.label = slice_params["label"]
    s.len_label = len(slice_params["label"])
    s.sched = slice_params["ue_sched_algo"]
    s.len_sched = len(slice_params["ue_sched_algo"])
    s.params.type = ric.SLICE_ALG_SM_V0_NVS
    s.params.u.nvs.conf = ric.SLICE_SM_NVS_V0_CAPACITY
    s.params.u.nvs.u.capacity.u.pct_reserved = slice_params["pct_rsvd"]
    return s


def _fill_slice_ctrl_msg(slice_pct_list):
    msg = ric.slice_ctrl_msg_t()
    msg.type = ric.SLICE_CTRL_SM_V0_ADD

    dl = ric.ul_dl_slice_conf_t()
    dl.sched_name = "PF"
    dl.len_sched_name = 2
    dl.len_slices = len(slice_pct_list)
    slices = ric.slice_array(len(slice_pct_list))

    for i, pct in enumerate(slice_pct_list):
        slices[i] = _create_slice(
            {
                "id": [0, 2, 5][i],
                "label": ["embb", "urllc", "best-effort"][i],
                "ue_sched_algo": "PF",
                "pct_rsvd": pct,
            }
        )
    dl.slices = slices
    msg.u.add_mod_slice.dl = dl
    return msg


def _profiles():
    return {
        "low": [0.60, 0.25, 0.15],
        "balanced": [0.45, 0.35, 0.20],
        "high": [0.25, 0.25, 0.50],
    }


def _state_bucket(util):
    if util < 35:
        return "low_load"
    if util < 70:
        return "medium_load"
    return "high_load"


class RLController:
    def __init__(self, node_id, target_util, alpha, gamma, epsilon, log_path, qtable_path):
        self.node_id = node_id
        self.target_util = target_util
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.log_path = Path(log_path)
        self.qtable_path = Path(qtable_path)
        self.actions = list(_profiles().keys())
        self.qtable = self._load_qtable()
        self.last_state = None
        self.last_action = None
        self.current_action = None

    def _load_qtable(self):
        if self.qtable_path.exists():
            try:
                return json.loads(self.qtable_path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_qtable(self):
        self.qtable_path.parent.mkdir(parents=True, exist_ok=True)
        self.qtable_path.write_text(json.dumps(self.qtable, indent=2), encoding="utf-8")

    def _get_value(self, state, action):
        return float(self.qtable.get(state, {}).get(action, 0.0))

    def _set_value(self, state, action, value):
        self.qtable.setdefault(state, {})[action] = round(float(value), 6)

    def choose_action(self, state):
        if random.random() < self.epsilon:
            return random.choice(self.actions)
        values = {action: self._get_value(state, action) for action in self.actions}
        return max(values, key=values.get)

    def apply_action(self, action):
        msg = _fill_slice_ctrl_msg(_profiles()[action])
        ric.control_slice_sm(self.node_id, msg)
        self.current_action = action

    def learn(self, util, records):
        state = _state_bucket(util)
        action = self.choose_action(state)
        switch_penalty = 2.0 if self.current_action and self.current_action != action else 0.0
        reward = -abs(util - self.target_util) - switch_penalty

        if self.last_state is not None and self.last_action is not None:
            current = self._get_value(self.last_state, self.last_action)
            future = max(self._get_value(state, a) for a in self.actions)
            updated = current + self.alpha * (reward + self.gamma * future - current)
            self._set_value(self.last_state, self.last_action, updated)

        self.apply_action(action)
        event = {
            "ts": time.time(),
            "util": util,
            "state": state,
            "action": action,
            "reward": reward,
            "records": records[-6:],
            "qtable": self.qtable,
        }
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event) + "\n")
        print(
            f"[RL_XAPP] util={util:.2f} state={state} action={action} "
            f"reward={reward:.2f} profile={_profiles()[action]}"
        )
        self.last_state = state
        self.last_action = action
        self._save_qtable()


def main():
    parser = argparse.ArgumentParser(description="RL-based FlexRIC xApp using KPM observations and slice control")
    parser.add_argument("--period-ms", type=int, default=1000)
    parser.add_argument("--duration-s", type=int, default=180)
    parser.add_argument("--decision-s", type=float, default=5.0)
    parser.add_argument("--epsilon", type=float, default=0.20)
    parser.add_argument("--alpha", type=float, default=0.30)
    parser.add_argument("--gamma", type=float, default=0.85)
    parser.add_argument("--target-util", type=float, default=55.0)
    parser.add_argument("--log-path", default="/tmp/flexric_rl_xapp/events.jsonl")
    parser.add_argument("--qtable-path", default="/tmp/flexric_rl_xapp/qtable.json")
    args = parser.parse_args()

    signal.signal(signal.SIGINT, _on_sigint)
    shared_state = {"lock": threading.Lock(), "util": None, "records": [], "last_update_ts": 0.0}

    ric.init()
    time.sleep(1)
    nodes = ric.conn_e2_nodes()
    if len(nodes) == 0:
        raise RuntimeError("No E2 nodes connected")

    node = nodes[0]
    controller = RLController(
        node_id=node.id,
        target_util=args.target_util,
        alpha=args.alpha,
        gamma=args.gamma,
        epsilon=args.epsilon,
        log_path=args.log_path,
        qtable_path=args.qtable_path,
    )
    kpm_handle = ric.report_kpm_sm_auto_py(node.id, args.period_ms, KPMCallback(shared_state))
    if kpm_handle < 0:
        raise RuntimeError("Failed to subscribe to KPM monitoring")

    print(
        f"RL xApp subscribed: period_ms={args.period_ms} duration_s={args.duration_s} "
        f"decision_s={args.decision_s} target_util={args.target_util}"
    )
    started = time.time()
    try:
        while STOP_REQUESTED is False:
            time.sleep(args.decision_s)
            now = time.time()
            if args.duration_s > 0 and (now - started) >= args.duration_s:
                print(f"Auto-stop after {args.duration_s}s")
                break
            with shared_state["lock"]:
                util = shared_state["util"]
                records = list(shared_state["records"])
            if util is None:
                print("[RL_XAPP] Waiting for KPM RRU indications...")
                continue
            controller.learn(util, records)
    finally:
        try:
            ric.rm_report_kpm_sm(kpm_handle)
        except Exception as exc:
            print(f"Warning: failed to remove KPM subscription: {exc}")
        while ric.try_stop() is False:
            time.sleep(0.1)


if __name__ == "__main__":
    main()
