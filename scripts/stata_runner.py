"""Plan and run isolated Stata specification searches (Python standard library).

Windows Stata 18 tested. Does not install packages or edit input datasets.
Only typed, bounded configuration is accepted; arbitrary Stata code is not an input.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone

SKILL = Path(__file__).resolve().parents[1]
PINNED_ADO = "fbd5fa55b3be12e3364c8ae940544d8b582d964bb3ce8d7ad2a938d716c85a80"
NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,31}\Z")
TERM = re.compile(r"(?:(?:i|c)\.)?([A-Za-z_][A-Za-z0-9_]{0,31})\Z")
RESERVED = {"_all", "_n", "_N", "_cons", "_b", "_se", "_coef", "_rc", "_pi", "_pred", "_skip", "_weight",
            "if", "in", "using", "with", "byte", "int", "long", "float", "double", "strL"}
KEYS = {"engine", "data_source", "data_path", "outcome", "target", "candidates",
        "fixed_controls", "method", "fixed_effects", "panel_id", "time_var",
        "panel_model", "vce", "min_controls", "max_controls", "sample_policy",
        "alpha", "max_models", "zvalue", "full", "best", "max_original_slots"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def name(value, label):
    if (not isinstance(value, str) or not NAME.fullmatch(value) or value in RESERVED
            or re.fullmatch(r"str[0-9]+", value)):
        raise ValueError(f"{label}: expected a simple Stata variable name")
    return value


def names(value, label, factors=False):
    if not isinstance(value, list):
        raise ValueError(f"{label}: expected a list")
    for v in value:
        if factors:
            if not isinstance(v, str) or not TERM.fullmatch(v):
                raise ValueError(f"{label}: only simple names, i.name and c.name supported")
            name(TERM.fullmatch(v).group(1), label)
        else:
            name(v, label)
    if len(set(value)) != len(value):
        raise ValueError(f"{label}: duplicate entries")
    return value


def integer(value, label, lower=0, upper=100000):
    if type(value) is not int or not lower <= value <= upper:
        raise ValueError(f"{label}: integer in [{lower}, {upper}] required")
    return value


def stata_path(path):
    value = str(Path(path).resolve()).replace("\\", "/")
    if any(c in value for c in ('"', '`', '$', '\n', '\r')):
        raise ValueError("Stata path contains unsupported quoting/macro characters")
    return value


def validate(raw, base=None, require_data=True):
    if not isinstance(raw, dict) or set(raw) - KEYS:
        raise ValueError(f"unknown configuration keys: {sorted(set(raw) - KEYS) if isinstance(raw, dict) else 'not object'}")
    c = dict(raw)
    c.setdefault("engine", "fullspec")
    if not isinstance(c["engine"], str) or c["engine"] not in {"fullspec", "oneclick"}:
        raise ValueError("engine must be fullspec or oneclick")
    data_fields = int("data_path" in c) + int("data_source" in c)
    if data_fields > 1 or (require_data and data_fields != 1):
        raise ValueError("run requires exactly one of data_path or data_source; plan may leave both unspecified")
    if "data_source" in c and c["data_source"] != "auto":
        raise ValueError("the only bundled data_source is auto")
    if "data_path" in c:
        if not isinstance(c["data_path"], str):
            raise ValueError("data_path must be a file path string")
        p = Path(c["data_path"]).expanduser()
        if not p.is_absolute():
            p = (base or Path.cwd()) / p
        p = p.resolve(strict=require_data)
        if p.suffix.lower() != ".dta" or (p.exists() and not p.is_file()):
            raise ValueError("data_path must name a local .dta file")
        if require_data and not p.is_file():
            raise ValueError("run requires an existing local .dta file")
        stata_path(p)
        c["data_path"] = str(p)
    name(c.get("outcome"), "outcome")
    name(c.get("target"), "target")
    c["candidates"] = names(c.get("candidates", []), "candidates")
    c["fixed_controls"] = names(c.get("fixed_controls", []), "fixed_controls", True)
    c["fixed_effects"] = names(c.get("fixed_effects", []), "fixed_effects")
    fixed_base = [TERM.fullmatch(t).group(1) for t in c["fixed_controls"]]
    role_vars = [c["outcome"], c["target"], *c["candidates"], *fixed_base]
    if len(set(role_vars)) != len(role_vars):
        raise ValueError("outcome, target, candidates and fixed controls must be distinct")
    if set(c["fixed_effects"]) & set(role_vars):
        raise ValueError("fixed_effects must be distinct from regression variables")
    c.setdefault("method", "regress")
    if not isinstance(c["method"], str) or c["method"] not in {"regress", "xtreg", "reghdfe", "logit", "probit"}:
        raise ValueError("unsupported estimator")
    if c["fixed_effects"] and c["method"] != "reghdfe":
        raise ValueError("fixed_effects is only for reghdfe; use i.year in fixed_controls otherwise")
    if c["method"] == "reghdfe" and not c["fixed_effects"]:
        raise ValueError("reghdfe requires fixed_effects")
    if c["method"] == "xtreg":
        name(c.get("panel_id"), "panel_id")
        if "time_var" in c:
            name(c["time_var"], "time_var")
        if not isinstance(c.get("panel_model"), str) or c["panel_model"] not in {"fe", "re"}:
            raise ValueError("xtreg requires panel_model fe or re")
    elif any(k in c for k in ("panel_id", "time_var", "panel_model")):
        raise ValueError("panel settings require xtreg")
    if set(c["candidates"]) & {c.get("panel_id"), c.get("time_var")}:
        raise ValueError("panel identifiers cannot be candidate controls")
    c.setdefault("vce", {"type": "conventional"})
    v = c["vce"]
    if not isinstance(v, dict) or set(v) - {"type", "cluster_var"}:
        raise ValueError("vce must contain type and optional cluster_var")
    if not isinstance(v.get("type"), str) or v["type"] not in {"conventional", "robust", "cluster"}:
        raise ValueError("unsupported vce type")
    if v["type"] == "cluster":
        name(v.get("cluster_var"), "cluster_var")
        if v["cluster_var"] in c["candidates"]:
            raise ValueError("cluster_var cannot be a candidate control")
    elif "cluster_var" in v:
        raise ValueError("cluster_var requires cluster vce")
    c.setdefault("sample_policy", "common")
    if not isinstance(c["sample_policy"], str) or c["sample_policy"] not in {"common", "per_spec"}:
        raise ValueError("sample_policy must be common or per_spec")
    c.setdefault("alpha", 0.05)
    if isinstance(c["alpha"], bool) or not isinstance(c["alpha"], (int, float)) or not 0 < c["alpha"] < 1:
        raise ValueError("alpha must be strictly between 0 and 1")
    k = len(c["candidates"])
    integer(k, "candidate count", 0, 30)
    c.setdefault("min_controls", 1 if c["engine"] == "oneclick" else 0)
    integer(c["min_controls"], "min_controls", 0, k)
    c.setdefault("max_models", 256)
    integer(c["max_models"], "max_models", 1, 100000)
    if c["engine"] == "oneclick":
        if k < 2 or c["min_controls"] < 1:
            raise ValueError("original OneClick requires >=2 candidates and min_controls>=1")
        if "max_controls" in c:
            raise ValueError("original OneClick has no max_controls option")
        c.setdefault("max_original_slots", 65536)
        integer(c["max_original_slots"], "max_original_slots", 4, 1048576)
        if 2 ** k > c["max_original_slots"]:
            raise ValueError("original OneClick combination storage exceeds max_original_slots")
        for key, default in (("zvalue", False), ("full", True), ("best", False)):
            c.setdefault(key, default)
            if type(c[key]) is not bool:
                raise ValueError(f"{key} must be boolean")
        if c["method"] in {"logit", "probit"} and not c["zvalue"]:
            raise ValueError("original OneClick with logit/probit requires explicit zvalue=true")
        count = sum(math.comb(k, j) for j in range(c["min_controls"], k + 1))
    else:
        if any(key in c for key in ("zvalue", "full", "best", "max_original_slots")):
            raise ValueError("zvalue/full/best/max_original_slots are original OneClick options")
        c.setdefault("max_controls", k)
        integer(c["max_controls"], "max_controls", c["min_controls"], k)
        count = sum(math.comb(k, j) for j in range(c["min_controls"], c["max_controls"] + 1))
    if count > c["max_models"]:
        raise ValueError(f"planned {count} models exceed max_models={c['max_models']}")
    # Check before enumerating; invalid paths or long commands cannot produce a partial plan.
    if len(command(c, c["candidates"])) > 1800:
        raise ValueError("generated estimator command exceeds 1800 characters")
    return c


def options(c):
    opts = []
    if c["method"] == "xtreg":
        opts.append(c["panel_model"])
    if c["method"] == "reghdfe":
        opts.append("absorb(" + " ".join(c["fixed_effects"]) + ")")
    if c["vce"]["type"] == "robust":
        opts.append("vce(robust)")
    elif c["vce"]["type"] == "cluster":
        opts.append("vce(cluster " + c["vce"]["cluster_var"] + ")")
    return " ".join(opts)


def command(c, subset):
    cmd = " ".join([c["method"], c["outcome"], c["target"], *c["fixed_controls"], *subset])
    return cmd + (", " + options(c) if options(c) else "")


def plan(c):
    upper = c.get("max_controls", len(c["candidates"]))
    return [{"spec_id": i, "controls": list(s), "command": command(c, s)}
            for i, s in enumerate(itertools.chain.from_iterable(
                itertools.combinations(c["candidates"], j)
                for j in range(c["min_controls"], upper + 1)), 1)]


def find_stata(explicit=None):
    if explicit or os.environ.get("STATA_EXE"):
        requested = str(explicit or os.environ["STATA_EXE"])
        on_path = shutil.which(requested)
        p = Path(on_path or requested).expanduser().resolve(strict=True)
        if not p.is_file():
            raise ValueError("Stata executable is not a file")
        return p
    for binary in ("StataMP-64.exe", "StataSE-64.exe", "Stata-64.exe", "stata-mp", "stata-se", "stata"):
        p = shutil.which(binary)
        if p:
            return Path(p)
    if os.name == "nt":
        import winreg
        root = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
        for access in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, root, 0, winreg.KEY_READ | access) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        with winreg.OpenKey(key, winreg.EnumKey(key, i)) as sub:
                            try:
                                title = winreg.QueryValueEx(sub, "DisplayName")[0]
                                location = winreg.QueryValueEx(sub, "InstallLocation")[0]
                            except OSError:
                                continue
                            if str(title).lower().startswith("stata"):
                                for binary in ("StataMP-64.exe", "StataSE-64.exe", "Stata-64.exe"):
                                    p = Path(location) / binary
                                    if p.is_file():
                                        return p
            except OSError:
                pass
    raise ValueError("Stata not found; pass --stata with the licensed executable path")


def render_do(c, specs, ado_dir=None, run_directory=None):
    lines = ["version 14", "set more off", "set varabbrev off"]
    if run_directory is not None:
        lines.append(f'cd "{stata_path(run_directory)}"')
    lines += ["capture program drop oc_job", "program define oc_job"]
    if ado_dir:
        lines.append(f'    adopath ++ "{stata_path(ado_dir)}"')
    if "data_path" in c:
        lines.append(f'    use "{stata_path(c["data_path"])}", clear')
    elif c.get("data_source") == "auto":
        lines.append("    sysuse auto, clear")
    else:
        lines += ['    display as error "Plan only: provide data_path or data_source before running"',
                  "    exit 601"]
    numeric = {c["outcome"], c["target"], *c["candidates"],
               *(TERM.fullmatch(v).group(1) for v in c["fixed_controls"])}
    extra = set(c["fixed_effects"])
    extra.update(c[k] for k in ("panel_id", "time_var") if k in c)
    if c["vce"]["type"] == "cluster":
        extra.add(c["vce"]["cluster_var"])
    for v in sorted(numeric):
        lines.append(f"    confirm numeric variable {v}, exact")
    for v in sorted(extra):
        lines.append(f"    confirm variable {v}, exact")
    if c["engine"] == "oneclick":
        for v in ("subset", "direction", "coef", "p", "r2"):
            lines.append(f"    confirm new variable {v}")
    if c["sample_policy"] == "common":
        lines += ["    tempvar complete", "    generate byte `complete' = 1"]
        for v in sorted(numeric | extra):
            lines.append(f"    replace `complete' = 0 if missing({v})")
        lines.append("    keep if `complete'")
    lines += ["    if _N == 0 {", "        display as error \"No observations in the input sample pool\"", "        exit 2000", "    }"]
    if c["method"] == "xtreg":
        lines.append("    xtset " + c["panel_id"] + (" " + c["time_var"] if "time_var" in c else ""))
    lines += [f"    which {c['method']}", "    file open pool using input_status.txt, write text",
              "    file write pool \"sample_pool_N=\" (_N) _n", "    file close pool"]
    if c["engine"] == "fullspec":
        lines += [f'    do "{stata_path(SKILL / "assets" / "oc_collect.ado")}"', "    tempname ph",
                  "    postfile `ph' long spec_id int control_count str1024 subset str2045 command ///",
                  "        str12 sample_policy long estimation_rc inference_rc str28 status ///",
                  "        double N double b double se double statistic double df_r double df_test ///",
                  "        double p_value double ci_low double ci_high double r2 double r2_a ///",
                  "        double r2_p double ll double converged double sample_used_N ///",
                  "        double common_pool_complete double passes_alpha ///",
                  "        using all_specs.dta"]
        for s in specs:
            subset = " ".join(s["controls"])
            lines.append(f'    oc_collect, handle(`ph\') spec({s["spec_id"]}) target({c["target"]}) ///')
            lines.append(f'        controls("{subset}") command("{s["command"]}") ///')
            lines.append(f'        policy({c["sample_policy"]}) alpha({c["alpha"]})')
        lines += ["    postclose `ph'", "    use all_specs.dta, clear", "    format b se statistic df_r df_test p_value ci_low ci_high r2 r2_a r2_p ll %24.17g",
                  "    save all_specs.dta, replace", "    export delimited using all_specs.csv, datafmt"]
    else:
        fixed = " ".join([c["target"], *c["fixed_controls"]])
        cmd = f'    oneclick {c["outcome"]} {" ".join(c["candidates"])}, method({c["method"]}) pvalue({c["alpha"]}) fixvar({fixed})'
        if options(c):
            cmd += f' options({options(c)})'
        cmd += f' threshold({c["min_controls"]}) saveplace(oneclick_selected.dta)'
        cmd += " zvalue" if c["zvalue"] else ""
        cmd += " full" if c["full"] else ""
        cmd += " best" if c["best"] else ""
        lines += ["    which oneclick", cmd, "    confirm file oneclick_selected.dta",
                  "    use oneclick_selected.dta, clear", "    export delimited using oneclick_selected.csv"]
    lines += ["end", "capture noisily oc_job", "local job_rc = _rc",
              "file open finish using run_status.txt, write text",
              "file write finish \"job_rc=`job_rc'\" _n",
              "file write finish \"stata_version=`c(stata_version)'\" _n",
              "file write finish \"stata_flavor=`c(flavor)'\" _n",
              "file write finish \"terminal_marker=1\" _n", "file close finish", "exit, clear"]
    return "\n".join(lines) + "\n"


def read_status(path):
    if not path.exists():
        return {}
    return dict(line.split("=", 1) for line in path.read_text(encoding="utf-8-sig").splitlines() if "=" in line)


def verify_output(c, specs, directory):
    filename = "all_specs.csv" if c["engine"] == "fullspec" else "oneclick_selected.csv"
    with (directory / filename).open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if c["engine"] == "fullspec":
        expected = [str(s["spec_id"]) for s in specs]
        if [r["spec_id"] for r in rows] != expected:
            raise ValueError("output specifications do not match the complete ordered plan")
        for row, spec in zip(rows, specs):
            if row["command"] != spec["command"] or row["subset"] != " ".join(spec["controls"]):
                raise ValueError("output command/subset differs from plan")
            if row["status"] == "ok":
                pv = float(row["p_value"])
                if not 0 <= pv <= 1 or float(row["se"]) <= 0:
                    raise ValueError("invalid inference in an ok row")
            elif row["p_value"] not in {"", "."}:
                raise ValueError("non-ok specification must not have a p value")
    elif not rows:
        raise ValueError("original OneClick reported success but selected output is empty")
    counts = {}
    for row in rows:
        key = row.get("status", "selected_by_original")
        counts[key] = counts.get(key, 0) + 1
    return {"output_rows": len(rows), "status_counts": counts}


def run(config_path, output_root, execute=False, stata=None, ado_dir=None, timeout=300):
    config_path = Path(config_path).expanduser().resolve(strict=True)
    c = validate(json.loads(config_path.read_text(encoding="utf-8-sig")), config_path.parent,
                 require_data=execute)
    specs = plan(c)
    ado = None
    if c["engine"] == "oneclick":
        if execute and not ado_dir:
            raise ValueError("original engine requires --ado-dir containing the verified OneClick 6.0 source")
        if ado_dir:
            ado = Path(ado_dir).expanduser()
            if not ado.is_absolute():
                ado = config_path.parent / ado
            ado = ado.resolve(strict=execute)
        if execute and sha256(ado / "oneclick.ado") != PINNED_ADO:
            raise ValueError("oneclick.ado differs from the pinned source; review the version before running")
    exe = find_stata(stata) if execute else None
    root = Path(output_root).expanduser()
    if not root.is_absolute():
        root = config_path.parent / root
    root = root.resolve()
    stata_path(root)
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    directory = root / ("run-" + stamp + "-" + uuid.uuid4().hex[:10])
    directory.mkdir(exist_ok=False)
    (directory / "config.json").write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")
    (directory / "plan.json").write_text(json.dumps(specs, ensure_ascii=False, indent=2), encoding="utf-8")
    (directory / "job.do").write_text(render_do(c, specs, ado, directory), encoding="utf-8")
    original_hash = sha256(c["data_path"]) if execute and "data_path" in c else None
    manifest = {"state": "planned", "executed_stata": False, "engine": c["engine"],
                "planned_models": len(specs), "includes_empty": c["min_controls"] == 0,
                "sample_policy": c["sample_policy"], "input_sha256": original_hash,
                "original_combination_slots": 2 ** len(c["candidates"]) if c["engine"] == "oneclick" else None,
                "oneclick_sha256": PINNED_ADO if execute and ado else None,
                "oneclick_expected_sha256": PINNED_ADO if c["engine"] == "oneclick" else None,
                "collector_sha256": sha256(SKILL / "assets" / "oc_collect.ado") if c["engine"] == "fullspec" else None,
                "execution_environment_checked": execute,
                "data_configured": "data_path" in c or "data_source" in c,
                "planning_note": None if execute else "Plan only: data contents, Stata, license and estimator dependencies were not checked; run performs its own preflight.",
                "job_sha256": sha256(directory / "job.do"), "output_directory": str(directory)}

    def save():
        (directory / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    save()
    if not execute:
        return manifest
    job_path = str(directory / "job.do")
    launch = [str(exe), "/e", "/q", "do", job_path] if os.name == "nt" else [str(exe), "-b", "do", job_path]
    kwargs = {}
    if os.name == "nt":
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = subprocess.SW_HIDE
        kwargs["startupinfo"] = startup
    manifest.update(state="running", executed_stata=True, executable=str(exe), launch=launch)
    save()
    start = time.monotonic()
    try:
        with (directory / "process_output.txt").open("wb") as stream:
            process = subprocess.Popen(launch, cwd=directory, stdout=stream, stderr=subprocess.STDOUT, **kwargs)
            manifest["child_pid"] = process.pid
            save()
            try:
                manifest["process_rc"] = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                manifest["state"] = "timed_out"
                raise RuntimeError("timeout: stopped only this runner's Stata process; results are incomplete")
        status = read_status(directory / "run_status.txt")
        manifest["stata_status"] = status
        manifest["input_status"] = read_status(directory / "input_status.txt")
        if manifest["process_rc"] != 0 or status.get("terminal_marker") != "1" or status.get("job_rc") != "0":
            raise RuntimeError("Stata job failed or completion marker missing; inspect job.log and run_status.txt")
        manifest.update(verify_output(c, specs, directory))
        if original_hash and sha256(c["data_path"]) != original_hash:
            raise RuntimeError("input file hash changed during run")
        manifest["state"] = "completed"
    except Exception as exc:
        if manifest["state"] != "timed_out":
            manifest["state"] = "failed"
        manifest["error"] = str(exc)
    finally:
        manifest["elapsed_seconds"] = round(time.monotonic() - start, 3)
        save()
    return manifest


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=("plan", "run"))
    ap.add_argument("config", type=Path)
    ap.add_argument("--output-root", type=Path, required=True)
    ap.add_argument("--stata", type=Path)
    ap.add_argument("--ado-dir", type=Path)
    ap.add_argument("--timeout", type=int, default=300)
    args = ap.parse_args()
    if not 1 <= args.timeout <= 86400:
        ap.error("--timeout must be between 1 and 86400 seconds")
    try:
        result = run(args.config, args.output_root, args.action == "run", args.stata, args.ado_dir, args.timeout)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"state": "rejected", "executed_stata": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["state"] in {"planned", "completed"} else 1


if __name__ == "__main__":
    sys.exit(main())
