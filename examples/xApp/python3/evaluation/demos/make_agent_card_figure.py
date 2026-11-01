#!/usr/bin/env python3
"""Fig. 3(a): the Agent Card of one registry entry, drawn from the registry itself (rapps/catalog.json),
in the visual style of the original panel. Every field shown is a field of the card; nothing is added.

  python make_agent_card_figure.py [--id rapp.qoe_prediction] [--out ../../paper/Pictures/agent_card_v2]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

HERE = Path(__file__).resolve().parent
CATALOG = HERE.parents[1] / "rapps" / "catalog.json"
GREEN, KEY, VAL, BLUE_BG, BLUE_EDGE, BORDER = "#3b6d11", "#5a7d2a", "#222222", "#eaf2fb", "#9cc2e5", "#9fc27f"
plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans", "Helvetica", "Arial"], "pdf.fonttype": 42})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", default="rapp.qoe_prediction")
    ap.add_argument("--out", default=str(HERE.parents[1] / "paper" / "Pictures" / "agent_card_v2"))
    args = ap.parse_args()
    card = next(c for c in json.loads(CATALOG.read_text()) if c["id"] == args.id)
    scope = ", ".join(f"{s['target']} ({s['mode']})" for s in card["control_scopes"]) or "none"
    sections = [
        ("Identity", [("id", card["id"]), ("version", card["version"]), ("vendor", card["vendor"]),
                      ("lifecycle", card["status"])]),
        ("O-RAN profile", [("type", "rApp, Non-RT RIC"), ("interfaces", ", ".join(card["interfaces"])),
                           ("consumes", ", ".join(card["consumes"])), ("produces", ", ".join(card["produces"])),
                           ("control scope", scope), ("timescale", f"{card['timescale_s']} s"),
                           ("requires", ", ".join(card["requires"]) or "none"),
                           ("conflicts with", ", ".join(card["conflicts_with"]) or "none")]),
        ("A2A: discovery", [("capabilities", ", ".join(card["capabilities"])), ("role", card["workflow_role"])]),
        ("MCP: tool access", [("tools", ", ".join(t["id"] for t in card["tools"]))]),
    ]
    W, line, gap = 2.3, 0.128, 0.05
    wrap = lambda s, n: [s[i:i + n] for i in range(0, len(s), n)] if len(s) > n else [s]  # noqa: E731
    rows = []
    for title, kv in sections:
        rows.append(("title", title))
        for k, v in kv:
            parts = []
            for chunk in v.split(", "):
                if parts and len(parts[-1]) + len(chunk) + 2 <= 30:
                    parts[-1] += ", " + chunk
                else:
                    parts += wrap(chunk, 30)
            rows.append(("kv", (k, parts)))
        rows.append(("gap", None))
    H = 0.62 + sum(line * (len(r[1][1]) if r[0] == "kv" else 1) + (0.03 if r[0] == "title" else 0) for r in rows if r[0] != "gap") + gap * len(sections)
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")
    ax.add_patch(FancyBboxPatch((0.04, 0.04), W - 0.08, H - 0.08, boxstyle="round,pad=0,rounding_size=0.08", fc="#fbfdf8", ec=BORDER, lw=0.8))
    y = H - 0.2
    ax.text(0.16, y, "Agent Card", fontsize=8.5, color=GREEN, va="center", weight="bold")
    ax.text(0.16, y - 0.15, "A2A identity + O-RAN profile", fontsize=5.2, color=KEY, va="center")
    y -= 0.36
    for kind, payload in rows:
        if kind == "title":
            if payload.startswith("MCP"):
                n = sum(len(r[1][1]) for r in rows[rows.index((kind, payload)) + 1:] if r[0] == "kv" and r[1][0] == "tools")
                ax.add_patch(FancyBboxPatch((0.1, y - line * (n + 0.75)), W - 0.2, line * (n + 1.35), boxstyle="round,pad=0,rounding_size=0.04",
                                            fc=BLUE_BG, ec=BLUE_EDGE, lw=0.6))
            ax.text(0.14, y, payload, fontsize=5.8, color=GREEN, va="center", weight="bold")
            y -= line + 0.03
        elif kind == "kv":
            k, parts = payload
            ax.text(0.22, y, k, fontsize=5.0, color=KEY, va="center")
            for i, p in enumerate(parts):
                ax.text(0.8, y - i * line, p, fontsize=5.0, color=VAL, va="center", family="monospace" if k in ("id", "tools", "consumes", "produces") else None)
            y -= line * len(parts)
        else:
            y -= gap
    for ext in ("pdf", "png"):
        fig.savefig(f"{args.out}.{ext}", dpi=300)
    print(args.out, round(W, 2), round(H, 2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
