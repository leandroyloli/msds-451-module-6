"""Revised block C study using local data without publication or Git operations."""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import json
import sys

ROOT=Path(__file__).resolve().parent
sys.dont_write_bytecode = True


def supplements():
    import pandas as pd
    from pipeline.utilities import metrics
    r=pd.read_csv(ROOT/"output/daily_returns.csv",index_col=0,parse_dates=True)
    rows=[]
    for name in ["Long-short","Long only","Equal weight","VT"]:
        values=metrics((1+r[name])*(1+r.FX)-1,r.RF*0)
        values.pop("sharpe")
        rows.append(dict(strategy=name,**values))
    pd.DataFrame(rows).to_csv(ROOT/"output/metrics_brl.csv",index=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true",help="Verify saved data, accounting and results")
    parser.add_argument("--report-only",action="store_true",help="Rebuild figures and HTML from saved results")
    args=parser.parse_args()
    if args.check:
        from pipeline.verify_v2 import run
        run()
        return
    if not args.report_only:
        from pipeline.study_v2 import run,run_temporal_control
        study=run()
        run_temporal_control(study)
        from pipeline.simulation_v2 import paired,dynamic
        paired()
        dynamic(study=study)
        supplements()
        from pipeline.verify_v2 import run as verify
        verify()
    else:
        supplements()
    from pipeline.figures_v2 import run as figures
    from pipeline.report_v2 import run as report
    figures();report()
    packages=["numpy","pandas","scipy","scikit-learn","cvxpy","clarabel","matplotlib","requests"]
    (ROOT/"output/environment.json").write_text(json.dumps(dict(python=sys.version,packages={p:importlib.metadata.version(p) for p in packages}),indent=2),encoding="utf-8")
    files=(list((ROOT/"pipeline").glob("*.py"))+list((ROOT/"pipeline").glob("*.css"))
           +list((ROOT/"report").glob("*.html"))+[ROOT/"run.py",ROOT/"requirements.txt",ROOT/"README.md"])
    (ROOT/"output/artifact_manifest.json").write_text(json.dumps({str(f.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(f.read_bytes()).hexdigest() for f in files},indent=2),encoding="utf-8")


if __name__=="__main__":main()
