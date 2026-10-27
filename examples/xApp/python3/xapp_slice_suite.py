#!/usr/bin/env python3
import argparse
import json
import time

import xapp_sdk as ric


LAST_ASSOC_RNTI = None


def _slice_ind_to_json(ind, out_path: str) -> None:
    global LAST_ASSOC_RNTI

    slice_stats = {"RAN": {"dl": {}}, "UE": {}}
    dl_dict = slice_stats["RAN"]["dl"]

    if ind.slice_stats.dl.len_slices <= 0:
        dl_dict["num_of_slices"] = ind.slice_stats.dl.len_slices
        dl_dict["slice_sched_algo"] = "null"
        try:
            dl_dict["ue_sched_algo"] = ind.slice_stats.dl.sched_name[0]
        except Exception:
            dl_dict["ue_sched_algo"] = "unknown"
    else:
        dl_dict["num_of_slices"] = ind.slice_stats.dl.len_slices
        dl_dict["slice_sched_algo"] = "null"
        dl_dict["slices"] = []

        for s in ind.slice_stats.dl.slices:
            if s.params.type == ric.SLICE_ALG_SM_V0_STATIC:
                slice_algo = "STATIC"
            elif s.params.type == ric.SLICE_ALG_SM_V0_NVS:
                slice_algo = "NVS"
            elif s.params.type == ric.SLICE_ALG_SM_V0_EDF:
                slice_algo = "EDF"
            else:
                slice_algo = "unknown"
            dl_dict["slice_sched_algo"] = slice_algo

            d = {
                "index": s.id,
                "label": s.label[0] if len(s.label) > 0 else "",
                "ue_sched_algo": s.sched[0] if len(s.sched) > 0 else "",
            }

            if slice_algo == "STATIC":
                d["slice_algo_params"] = {
                    "pos_low": s.params.u.sta.pos_low,
                    "pos_high": s.params.u.sta.pos_high,
                }
            elif slice_algo == "NVS":
                if s.params.u.nvs.conf == ric.SLICE_SM_NVS_V0_RATE:
                    d["slice_algo_params"] = {
                        "type": "RATE",
                        "mbps_rsvd": s.params.u.nvs.u.rate.u1.mbps_required,
                        "mbps_ref": s.params.u.nvs.u.rate.u2.mbps_reference,
                    }
                elif s.params.u.nvs.conf == ric.SLICE_SM_NVS_V0_CAPACITY:
                    d["slice_algo_params"] = {
                        "type": "CAPACITY",
                        "pct_rsvd": s.params.u.nvs.u.capacity.u.pct_reserved,
                    }
            elif slice_algo == "EDF":
                d["slice_algo_params"] = {
                    "deadline": s.params.u.edf.deadline,
                    "guaranteed_prbs": s.params.u.edf.guaranteed_prbs,
                    "max_replenish": s.params.u.edf.max_replenish,
                }
            dl_dict["slices"].append(d)

    ue_dict = slice_stats["UE"]
    ue_dict["num_of_ues"] = ind.ue_slice_stats.len_ue_slice
    if ind.ue_slice_stats.len_ue_slice > 0:
        ue_dict["ues"] = []
        for u in ind.ue_slice_stats.ues:
            LAST_ASSOC_RNTI = u.rnti
            ue_dict["ues"].append(
                {
                    "rnti": hex(u.rnti),
                    "assoc_dl_slice_id": u.dl_id if u.dl_id >= 0 else "null",
                }
            )

    with open(out_path, "w") as f:
        json.dump(slice_stats, f)


class SliceCallback(ric.slice_cb):
    def __init__(self, json_out: str, verbose: bool = False):
        super().__init__()
        self.json_out = json_out
        self.verbose = verbose

    def handle(self, ind):
        _slice_ind_to_json(ind, self.json_out)
        if self.verbose:
            print(
                f"SLICE ind tstamp={ind.tstamp} dl_slices={ind.slice_stats.dl.len_slices} "
                f"ue_assoc={ind.ue_slice_stats.len_ue_slice}"
            )


def _create_slice(slice_params, slice_sched_algo):
    s = ric.fr_slice_t()
    s.id = slice_params["id"]
    s.label = slice_params["label"]
    s.len_label = len(slice_params["label"])
    s.sched = slice_params["ue_sched_algo"]
    s.len_sched = len(slice_params["ue_sched_algo"])

    if slice_sched_algo == "STATIC":
        s.params.type = ric.SLICE_ALG_SM_V0_STATIC
        s.params.u.sta.pos_low = slice_params["slice_algo_params"]["pos_low"]
        s.params.u.sta.pos_high = slice_params["slice_algo_params"]["pos_high"]
    elif slice_sched_algo == "NVS":
        s.params.type = ric.SLICE_ALG_SM_V0_NVS
        if slice_params["type"] == "SLICE_SM_NVS_V0_RATE":
            s.params.u.nvs.conf = ric.SLICE_SM_NVS_V0_RATE
            s.params.u.nvs.u.rate.u1.mbps_required = slice_params["slice_algo_params"]["mbps_rsvd"]
            s.params.u.nvs.u.rate.u2.mbps_reference = slice_params["slice_algo_params"]["mbps_ref"]
        elif slice_params["type"] == "SLICE_SM_NVS_V0_CAPACITY":
            s.params.u.nvs.conf = ric.SLICE_SM_NVS_V0_CAPACITY
            s.params.u.nvs.u.capacity.u.pct_reserved = slice_params["slice_algo_params"]["pct_rsvd"]
        else:
            raise ValueError("Unknown NVS config type")
    elif slice_sched_algo == "EDF":
        s.params.type = ric.SLICE_ALG_SM_V0_EDF
        s.params.u.edf.deadline = slice_params["slice_algo_params"]["deadline"]
        s.params.u.edf.guaranteed_prbs = slice_params["slice_algo_params"]["guaranteed_prbs"]
        s.params.u.edf.max_replenish = slice_params["slice_algo_params"]["max_replenish"]
    else:
        raise ValueError(f"Unknown slice algo type: {slice_sched_algo}")
    return s


def _fill_slice_ctrl_msg(ctrl_type, ctrl_msg):
    msg = ric.slice_ctrl_msg_t()

    if ctrl_type == "ADDMOD":
        msg.type = ric.SLICE_CTRL_SM_V0_ADD
        dl = ric.ul_dl_slice_conf_t()
        ue_sched_algo = ctrl_msg.get("sched_name", "PF")
        dl.sched_name = ue_sched_algo
        dl.len_sched_name = len(ue_sched_algo)

        dl.len_slices = ctrl_msg["num_slices"]
        slices = ric.slice_array(ctrl_msg["num_slices"])
        for i in range(ctrl_msg["num_slices"]):
            slices[i] = _create_slice(ctrl_msg["slices"][i], ctrl_msg["slice_sched_algo"])
        dl.slices = slices
        msg.u.add_mod_slice.dl = dl
        return msg

    if ctrl_type == "DEL":
        msg.type = ric.SLICE_CTRL_SM_V0_DEL
        msg.u.del_slice.len_dl = ctrl_msg["num_dl_slices"]
        del_dl_id = ric.del_dl_array(ctrl_msg["num_dl_slices"])
        for i in range(ctrl_msg["num_dl_slices"]):
            del_dl_id[i] = ctrl_msg["delete_dl_slice_id"][i]
        msg.u.del_slice.dl = del_dl_id
        return msg

    if ctrl_type == "ASSOC_UE_SLICE":
        global LAST_ASSOC_RNTI
        if LAST_ASSOC_RNTI is None:
            raise RuntimeError("No UE RNTI observed yet from slice indication; cannot associate UE to slice.")
        msg.type = ric.SLICE_CTRL_SM_V0_UE_SLICE_ASSOC
        msg.u.ue_slice.len_ue_slice = ctrl_msg["num_ues"]
        assoc = ric.ue_slice_assoc_array(ctrl_msg["num_ues"])
        for i in range(ctrl_msg["num_ues"]):
            a = ric.ue_slice_assoc_t()
            a.rnti = LAST_ASSOC_RNTI
            a.dl_id = ctrl_msg["ues"][i]["assoc_dl_slice_id"]
            assoc[i] = a
        msg.u.ue_slice.ues = assoc
        return msg

    raise ValueError(f"Unsupported ctrl_type: {ctrl_type}")


def _profile_static():
    return {
        "num_slices": 3,
        "slice_sched_algo": "STATIC",
        "slices": [
            {"id": 0, "label": "s1", "ue_sched_algo": "PF", "slice_algo_params": {"pos_low": 0, "pos_high": 2}},
            {"id": 2, "label": "s2", "ue_sched_algo": "PF", "slice_algo_params": {"pos_low": 3, "pos_high": 10}},
            {"id": 5, "label": "s3", "ue_sched_algo": "PF", "slice_algo_params": {"pos_low": 11, "pos_high": 13}},
        ],
    }


def _profile_nvs_rate():
    return {
        "num_slices": 2,
        "slice_sched_algo": "NVS",
        "slices": [
            {
                "id": 0,
                "label": "s1",
                "ue_sched_algo": "PF",
                "type": "SLICE_SM_NVS_V0_RATE",
                "slice_algo_params": {"mbps_rsvd": 60, "mbps_ref": 120},
            },
            {
                "id": 2,
                "label": "s2",
                "ue_sched_algo": "PF",
                "type": "SLICE_SM_NVS_V0_RATE",
                "slice_algo_params": {"mbps_rsvd": 60, "mbps_ref": 120},
            },
        ],
    }


def _profile_nvs_cap():
    return {
        "num_slices": 3,
        "slice_sched_algo": "NVS",
        "slices": [
            {
                "id": 0,
                "label": "s1",
                "ue_sched_algo": "PF",
                "type": "SLICE_SM_NVS_V0_CAPACITY",
                "slice_algo_params": {"pct_rsvd": 0.5},
            },
            {
                "id": 2,
                "label": "s2",
                "ue_sched_algo": "PF",
                "type": "SLICE_SM_NVS_V0_CAPACITY",
                "slice_algo_params": {"pct_rsvd": 0.3},
            },
            {
                "id": 5,
                "label": "s3",
                "ue_sched_algo": "PF",
                "type": "SLICE_SM_NVS_V0_CAPACITY",
                "slice_algo_params": {"pct_rsvd": 0.2},
            },
        ],
    }


def _profile_edf():
    return {
        "num_slices": 3,
        "slice_sched_algo": "EDF",
        "slices": [
            {
                "id": 0,
                "label": "s1",
                "ue_sched_algo": "PF",
                "slice_algo_params": {"deadline": 10, "guaranteed_prbs": 20, "max_replenish": 0},
            },
            {
                "id": 2,
                "label": "s2",
                "ue_sched_algo": "RR",
                "slice_algo_params": {"deadline": 20, "guaranteed_prbs": 20, "max_replenish": 0},
            },
            {
                "id": 5,
                "label": "s3",
                "ue_sched_algo": "MT",
                "slice_algo_params": {"deadline": 40, "guaranteed_prbs": 10, "max_replenish": 0},
            },
        ],
    }


def _delete_msg(slice_ids):
    return {"num_dl_slices": len(slice_ids), "delete_dl_slice_id": list(slice_ids)}


def _assoc_msg(dl_slice_id):
    return {"num_ues": 1, "ues": [{"assoc_dl_slice_id": dl_slice_id}]}


def _safe_stop():
    while ric.try_stop() is False:
        time.sleep(0.1)


def main():
    ap = argparse.ArgumentParser(description="Unified Slice xApp monitor/control suite")
    ap.add_argument("--profile", choices=["monitor", "static", "nvs-rate", "nvs-cap", "edf", "all"], default="monitor")
    ap.add_argument("--duration-s", type=int, default=180)
    ap.add_argument("--json-out", default="rt_slice_stats.json")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--assoc-dl-id", type=int, default=2, help="DL slice ID used in UE association step (profile=all)")
    args = ap.parse_args()

    ric.init()
    conn = ric.conn_e2_nodes()
    if len(conn) <= 0:
        raise RuntimeError("No E2 nodes connected")
    node = conn[0]

    print(f"Connected E2 nodes = {len(conn)}")
    try:
        ran_ids = [str(x) for x in ric.get_ran_func_ids(node)]
        print(f"Node 0 RAN functions: {', '.join(ran_ids)}")
    except Exception:
        print("Node 0 RAN functions: unavailable (SWIG raw object)")

    cb = SliceCallback(args.json_out, verbose=args.verbose)
    hnd = ric.report_slice_sm(node.id, ric.Interval_ms_5, cb)
    print(f"Slice monitor subscribed (handle={hnd})")

    try:
        if args.profile == "monitor":
            print(f"Monitor-only mode for {args.duration_s}s")
            time.sleep(args.duration_s)
        elif args.profile == "static":
            ric.control_slice_sm(node.id, _fill_slice_ctrl_msg("ADDMOD", _profile_static()))
            print(f"Applied STATIC slice profile; monitoring for {args.duration_s}s")
            time.sleep(args.duration_s)
        elif args.profile == "nvs-rate":
            ric.control_slice_sm(node.id, _fill_slice_ctrl_msg("ADDMOD", _profile_nvs_rate()))
            print(f"Applied NVS RATE slice profile; monitoring for {args.duration_s}s")
            time.sleep(args.duration_s)
        elif args.profile == "nvs-cap":
            ric.control_slice_sm(node.id, _fill_slice_ctrl_msg("ADDMOD", _profile_nvs_cap()))
            print(f"Applied NVS CAPACITY slice profile; monitoring for {args.duration_s}s")
            time.sleep(args.duration_s)
        elif args.profile == "edf":
            ric.control_slice_sm(node.id, _fill_slice_ctrl_msg("ADDMOD", _profile_edf()))
            print(f"Applied EDF slice profile; monitoring for {args.duration_s}s")
            time.sleep(args.duration_s)
        elif args.profile == "all":
            print("Running full slice demo sequence: add(static) -> assoc UE -> del slice 5")
            ric.control_slice_sm(node.id, _fill_slice_ctrl_msg("ADDMOD", _profile_static()))
            time.sleep(5)
            try:
                ric.control_slice_sm(node.id, _fill_slice_ctrl_msg("ASSOC_UE_SLICE", _assoc_msg(args.assoc_dl_id)))
                print(f"Associated observed UE to DL slice {args.assoc_dl_id}")
            except Exception as e:
                print(f"Skipped UE association: {e}")
            time.sleep(5)
            ric.control_slice_sm(node.id, _fill_slice_ctrl_msg("DEL", _delete_msg([5])))
            print("Deleted DL slice id 5")
            time.sleep(max(0, args.duration_s))
        else:
            raise ValueError(f"Unsupported profile {args.profile}")
    except KeyboardInterrupt:
        pass
    finally:
        try:
            ric.rm_report_slice_sm(hnd)
        except Exception:
            pass
        _safe_stop()
        print("Slice suite finished")


if __name__ == "__main__":
    main()
