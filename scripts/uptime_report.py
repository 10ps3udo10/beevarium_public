#!/usr/bin/env python3
"""Tableau mensuel de disponibilite a partir de la base SQLite d'Uptime Kuma 1.x.

Lecture seule (`mode=ro`). Tables utilisees : `monitor` (id, name) et
`heartbeat` (monitor_id, status, time UTC, ping en ms).
Statuts Kuma : 0 hors service, 1 en service, 2 en attente (compte comme en
service : nouvelle tentative), 3 maintenance (exclue du calcul).

Methode : chaque mesure vaut jusqu'a la suivante, plafonne a GAP_MAX secondes ;
au-dela, l'intervalle est "sans donnees" (Kuma arrete ?) et exclu du calcul.
La derniere mesure du mois vaut LAST_SEGMENT secondes.

Usage : python3 scripts/uptime_report.py <kuma.db> AAAA-MM [--json]
"""

from __future__ import annotations

import json
import math
import sqlite3
import sys
from datetime import datetime, timezone
from urllib.parse import quote

GAP_MAX = 900
LAST_SEGMENT = 60


def month_bounds(month: str) -> tuple[datetime, datetime]:
    start = datetime.strptime(month, "%Y-%m").replace(tzinfo=timezone.utc)
    end = start.replace(year=start.year + 1, month=1) if start.month == 12 else start.replace(month=start.month + 1)
    return start, end


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.split(".")[0].replace("T", " ")).replace(tzinfo=timezone.utc)


def p95(values: list[int]) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[math.ceil(0.95 * len(ordered)) - 1]


def analyse(beats: list[tuple[datetime, int, int | None]], end: datetime) -> dict:
    up = down = maint = 0.0
    outages: list[float] = []
    current = 0.0
    pings: list[int] = []
    for i, (when, status, ping) in enumerate(beats):
        following = beats[i + 1][0] if i + 1 < len(beats) else None
        raw = (following - when).total_seconds() if following else min(LAST_SEGMENT, (end - when).total_seconds())
        seg = min(raw, GAP_MAX)
        broken = raw > GAP_MAX
        if status == 0:
            down += seg
            current += seg
        else:
            if current:
                outages.append(current)
                current = 0.0
            if status == 3:
                maint += seg
            else:
                up += seg
                if status == 1 and ping is not None:
                    pings.append(ping)
        if broken and current:
            outages.append(current)
            current = 0.0
    if current:
        outages.append(current)
    measured = up + down
    return {
        "disponibilite_pct": round(100 * up / measured, 3) if measured else None,
        "mesures": len(beats),
        "secondes_mesurees": int(measured),
        "secondes_maintenance": int(maint),
        "indisponibilites": len(outages),
        "indisponibilite_totale_s": int(down),
        "plus_longue_coupure_s": int(max(outages, default=0)),
        "ping_moyen_ms": round(sum(pings) / len(pings), 1) if pings else None,
        "ping_p95_ms": p95(pings),
    }


def build_report(db_path: str, month: str) -> dict:
    start, end = month_bounds(month)
    uri = f"file:{quote(db_path)}?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    try:
        monitors = con.execute("SELECT id, name FROM monitor ORDER BY name").fetchall()
        report = {"mois": month, "moniteurs": {}}
        for monitor_id, name in monitors:
            rows = con.execute(
                "SELECT time, status, ping FROM heartbeat WHERE monitor_id = ? AND time >= ? AND time < ? ORDER BY time",
                (monitor_id, start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S")),
            ).fetchall()
            beats = [(parse_time(t), s, p) for t, s, p in rows]
            report["moniteurs"][name] = analyse(beats, end)
        return report
    finally:
        con.close()


def fmt_duration(seconds: int) -> str:
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours} h {minutes:02d} min {secs:02d} s" if hours else f"{minutes} min {secs:02d} s"


def fmt_ping(value: float | None) -> str:
    return "-" if value is None else f"{value} ms"


def to_markdown(report: dict) -> str:
    lines = [
        f"# Disponibilite {report['mois']}",
        "",
        "| Moniteur | Disponibilite | Coupures | Indisponibilite totale | Plus longue coupure | Ping moyen | Ping p95 |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, m in report["moniteurs"].items():
        dispo = "sans donnees" if m["disponibilite_pct"] is None else f"{m['disponibilite_pct']:.3f} %"
        lines.append(
            f"| {name} | {dispo} | {m['indisponibilites']} | {fmt_duration(m['indisponibilite_totale_s'])} "
            f"| {fmt_duration(m['plus_longue_coupure_s'])} | {fmt_ping(m['ping_moyen_ms'])} | {fmt_ping(m['ping_p95_ms'])} |"
        )
    lines += [
        "",
        f"Methode : mesures Uptime Kuma (UTC), chaque mesure vaut jusqu'a la suivante (plafond {GAP_MAX // 60} min, "
        "au-dela : sans donnees, exclu) ; maintenance exclue ; ping sur les mesures en service.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    report = build_report(args[0], args[1])
    print(json.dumps(report, indent=2, ensure_ascii=False) if "--json" in sys.argv else to_markdown(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
