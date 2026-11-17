#!/usr/bin/env python3
"""LEDGER trace generator. Given file: see appendix D of the subject.

Reads JUnit XML reports (Surefire, and the XML of your source and delivery
checks) and prints the moulinette trace: parts, tests, percentage, score and
failed tests with their messages.

    python3 acceptance/report/trace.py                    # plain text, for a terminal
    python3 acceptance/report/trace.py --markdown         # for $GITHUB_STEP_SUMMARY
    python3 acceptance/report/trace.py --output trace.md  # also write it to a file

Environment variables (all optional):
    BUILD_OUTCOME, START_OUTCOME   outcomes of the build and start steps
                                   (success, failure, cancelled, skipped)
    GITHUB_REF_NAME, GITHUB_SHA    tag and commit, set by GitHub Actions

Python 3.9+, standard library only. Always exits 0: the grade is in the
trace, not in the exit code.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_REPORT_DIRS = ["acceptance/target/surefire-reports", "acceptance/target/checks"]

# Scale of section 1.2: (part, points, points with the CSV fallback), in display order.
PARTS = [
    ("Delivery", 5, 5),
    ("Architecture", 10, 10),
    ("Level 0", 5, 5),
    ("Level 1", 20, 20),
    ("Level 2", 30, 30),
    ("Level 3", 15, 9),
    ("Level 4", 15, 8),
]
OTHER = "Other"

# A testcase with any of these children did not pass. Skipped tests count as
# failed, so that @Disabled cannot hide a test; flaky ones too (section 7.6).
NOT_PASSED = ("failure", "error", "skipped", "flakyFailure", "flakyError", "rerunFailure", "rerunError")

MESSAGE_LINES = 3
MESSAGE_WIDTH = 160


@dataclass
class Case:
    part: str
    classname: str
    name: str
    passed: bool
    kind: str = ""
    message: str = ""

    @property
    def scenario(self) -> str:
        """'h1_isHealthy' -> 'H1'; '' when the name has no prefix."""
        return self.name.split("_", 1)[0].upper() if "_" in self.name else ""

    @property
    def simple_class(self) -> str:
        return self.classname.rsplit(".", 1)[-1]


def part_of(classname: str) -> str:
    """Map a test class to a part of the scale."""
    segments = [s.lower() for s in classname.split(".")]
    simple = classname.rsplit(".", 1)[-1]
    if "delivery" in segments or simple.lower().startswith("delivery"):
        return "Delivery"
    if "architecture" in segments or simple.lower().startswith("architecture"):
        return "Architecture"
    m = re.match(r"Level(\d)", simple)
    if m and any(p == f"Level {m.group(1)}" for p, _, _ in PARTS):
        return f"Level {m.group(1)}"
    return OTHER


def read_reports(dirs: list[str]) -> tuple[list[Case], list[str]]:
    cases: list[Case] = []
    problems: list[str] = []
    files = sorted({p for d in dirs for p in Path(d).glob("*.xml")})
    for f in files:
        try:
            root = ET.parse(f).getroot()
        except ET.ParseError as e:
            problems.append(f"unreadable report {f}: {e}")
            continue
        for tc in root.iter("testcase"):
            classname = tc.get("classname") or tc.get("class") or "?"
            name = re.sub(r"\(.*\)$", "", tc.get("name") or "?")
            bad = next((child for child in tc if child.tag in NOT_PASSED), None)
            if bad is None:
                cases.append(Case(part_of(classname), classname, name, True))
                continue
            message = bad.get("message") or (bad.text or "").strip() or bad.get("type") or bad.tag
            cases.append(Case(part_of(classname), classname, name, False, bad.tag, message))
    return cases, problems


def short_message(message: str) -> list[str]:
    lines = [l.rstrip() for l in message.strip().splitlines() if l.strip()][:MESSAGE_LINES]
    return [l if len(l) <= MESSAGE_WIDTH else l[:MESSAGE_WIDTH - 3] + "..." for l in lines] or ["(no message)"]


def commit_id() -> str:
    sha = os.environ.get("GITHUB_SHA", "")
    if sha:
        return sha[:7]
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=5)
        return out.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def header() -> str:
    tag = os.environ.get("GITHUB_REF_NAME") or "local run"
    when = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"LEDGER moulinette · tag {tag} · commit {commit_id()} · {when}"


def aborted_reason() -> str | None:
    build = os.environ.get("BUILD_OUTCOME", "")
    start = os.environ.get("START_OUTCOME", "")
    if build and build != "success":
        return "build failed"
    if start and start != "success":
        return "server did not start"
    return None


def build_trace(cases: list[Case], problems: list[str], csv: bool, markdown: bool) -> str:
    max_score = sum(csv_pts if csv else pts for _, pts, csv_pts in PARTS)
    out: list[str] = []
    title = header()
    out.append(f"**{title}**" if markdown else title)
    out.append("")

    reason = aborted_reason()
    if reason:
        out.append(f"No test was run: {reason}.")
        out.append("")
        out.append(f"Score: 0/{max_score}" if not markdown else f"**Score: 0/{max_score}**")
        return "\n".join(out) + "\n"

    rows = []
    score = 0
    part_names = [p for p, _, _ in PARTS] + ([OTHER] if any(c.part == OTHER for c in cases) else [])
    for part in part_names:
        pts = next((csv_pts if csv else p for name, p, csv_pts in PARTS if name == part), 0)
        mine = [c for c in cases if c.part == part]
        passed = sum(c.passed for c in mine)
        if not mine:
            state, earned = "not started", 0
        elif passed == len(mine):
            state, earned = "PASS", pts
        else:
            state, earned = "FAIL", 0
        score += earned
        rows.append((part, f"{passed}/{len(mine)}", state, f"{earned}/{pts}"))

    total = len(cases)
    passed_total = sum(c.passed for c in cases)
    percent = 100.0 * passed_total / total if total else 0.0
    failed = [c for c in cases if not c.passed]

    if markdown:
        out.append("| Part | Tests | State | Points |")
        out.append("|---|---|---|---|")
        for part, tests, state, pts in rows:
            shown = f"**{state}**" if state == "FAIL" else state
            out.append(f"| {part} | {tests} | {shown} | {pts} |")
        out.append("")
        out.append(f"**Tests passed: {passed_total}/{total} ({percent:.1f} %)**  ")
        out.append(f"**Score: {score}/{max_score}**")
    else:
        out.append(f"{'Part':<14} {'Tests':>7}    {'State':<12} {'Points':>7}")
        for part, tests, state, pts in rows:
            out.append(f"{part:<14} {tests:>7}    {state:<12} {pts:>7}")
        out.append("")
        out.append(f"{'Tests passed':<14} {passed_total}/{total} ({percent:.1f} %)")
        out.append(f"{'Score':<14} {score}/{max_score}")

    if not cases:
        out.append("")
        out.append("No test report found. Did the acceptance suite run?")

    if failed or problems:
        out.append("")
        out.append("**Failed tests**" if markdown else "Failed tests")
        block = []
        for c in failed:
            sid = c.scenario or "-"
            block.append(f"  {sid:<6} {c.name} · {c.simple_class} ({c.kind})")
            block.extend(f"         {line}" for line in short_message(c.message))
        for p in problems:
            block.append(f"  !      {p}")
        if markdown:
            out.append("```")
            out.extend(block)
            out.append("```")
        else:
            out.extend(block)
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="LEDGER trace generator")
    ap.add_argument("--reports", action="append", metavar="DIR",
                    help="directory of JUnit XML reports (repeatable; default: the Surefire "
                         "reports and the checks of the acceptance project)")
    ap.add_argument("--markdown", action="store_true", help="Markdown output, for the job summary")
    ap.add_argument("--csv", action="store_true", help="CSV fallback scale: levels 3 and 4 worth 9 and 8")
    ap.add_argument("--output", metavar="FILE", help="also write the trace to this file")
    args = ap.parse_args()

    cases, problems = read_reports(args.reports or DEFAULT_REPORT_DIRS)
    trace = build_trace(cases, problems, args.csv, args.markdown)
    print(trace, end="")
    if args.output:
        Path(args.output).write_text(trace, encoding="utf-8")


if __name__ == "__main__":
    main()