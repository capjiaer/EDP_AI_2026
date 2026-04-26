#!/usr/bin/env python3
"""EDP tab-completion helper for tcsh backtick-driven completion.

Called at Tab-press time by tcsh's complete rules.  Reads the bash-format
cache to get dynamic values (projects, nodes, steps) and outputs
space-separated completions on stdout.
"""

import os
import sys
from pathlib import Path


def usage():
    sys.stderr.write("Usage: edp_complete_helper.py <type>\n")
    sys.stderr.write("Types: subcommands steps projects nodes versions formats tools\n")
    sys.stderr.write("       flags:init flags:run flags:retry flags:graph\n")
    sys.stderr.write("       flags:doctor flags:flowcreate tutor_subcommands all_flags\n")
    sys.exit(2)


def read_cache(edp_root):
    """Read the bash-format completion cache (simpler to parse than csh)."""
    cache_file = Path(edp_root) / ".edp_completion_cache"
    projects, nodes, steps = [], [], []
    if cache_file.exists():
        try:
            for line in cache_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("PROJECTS="):
                    projects = line.split("=", 1)[1].split()
                elif line.startswith("NODES="):
                    nodes = line.split("=", 1)[1].split()
                elif line.startswith("STEPS="):
                    steps = line.split("=", 1)[1].split()
        except Exception:
            pass
    return projects or ["dongting"], nodes or ["S4"], steps or [
        "init", "floorplan", "place", "route", "postroute", "cts", "drc", "lvs", "perc"
    ]


def output(words):
    """Print completions space-separated."""
    if words:
        print(" ".join(words))


def main():
    if len(sys.argv) < 2:
        usage()

    req = sys.argv[1]
    edp_root = os.environ.get("EDP_ROOT", "")
    projects, nodes, steps = read_cache(edp_root)

    if req == "subcommands":
        output(["init", "run", "status", "retry", "graph", "doctor",
                "flowcreate", "tutor"])
    elif req == "steps":
        output(steps)
    elif req == "projects":
        output(projects)
    elif req == "nodes":
        output(nodes)
    elif req == "versions":
        output(["P85", "P95", "P100"])
    elif req == "formats":
        output(["ascii", "dot", "table"])
    elif req == "tools":
        output(["pnr_innovus", "pv_calibre", "sta_pt"])
    elif req == "tutor_subcommands":
        output(["quickstart", "model", "diagnose"])
    elif req == "flags:init":
        output(["-prj", "--project", "-w", "--work-path", "-n", "--node",
                "-ver", "--version", "-blk", "--block", "-br", "--branch",
                "--link", "--no-link", "-h", "--help"])
    elif req == "flags:run":
        output(["-fr", "--from", "-to", "--to", "-skip", "--skip",
                "-dr", "--dry-run", "--force", "-debug", "--debug",
                "-info", "--info", "-h", "--help"])
    elif req == "flags:retry":
        output(["-dr", "--dry-run", "-debug", "--debug",
                "-info", "--info", "-h", "--help"])
    elif req == "flags:graph":
        output(["-f", "--format", "-o", "--output", "-select", "--select",
                "-h", "--help"])
    elif req == "flags:doctor":
        output(["--strict", "--json", "-h", "--help"])
    elif req == "flags:flowcreate":
        output(["--tool", "--step", "--sub-steps", "--invoke", "-h", "--help"])
    elif req == "all_flags":
        output(["-fr", "--from", "-to", "--to", "-skip", "--skip",
                "-dr", "--dry-run", "--force", "-debug", "--debug",
                "-info", "--info", "--strict", "--json",
                "-prj", "--project", "-w", "--work-path", "-n", "--node",
                "-ver", "--version", "-blk", "--block", "-br", "--branch",
                "--link", "--no-link",
                "-f", "--format", "-o", "--output", "-select", "--select",
                "--tool", "--step", "--sub-steps", "--invoke",
                "-h", "--help"])
    elif req == "run_steps_and_flags":
        output(steps + ["-fr", "--from", "-to", "--to", "-skip", "--skip",
                         "-dr", "--dry-run", "--force", "-debug", "--debug",
                         "-info", "--info", "-h", "--help"])
    else:
        usage()


if __name__ == "__main__":
    main()
