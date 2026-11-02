"""Independent saved-output checks for signed accounting and look-through limits."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix

from . import config_v2 as c
from .execution_v2 import self_test
from .study_v2 import prepare


def run():
    checks=[]
    def check(name,ok):
        if not bool(ok):raise AssertionError(name)
        checks.append(name)
    manifest=json.loads((c.DATA/"holdings/manifest.json").read_text())
    for name,field in [("holdings.csv","holdings_sha256"),("coverage.csv","coverage_sha256")]:
        check("Composição congelada: "+name,hashlib.sha256((c.DATA/"holdings"/name).read_bytes()).hexdigest()==manifest[field])
    source=json.loads((c.ROOT/"data/sources.json").read_text())
    for name,digest in source["hashes"].items():
        check("Preços originais: "+name,hashlib.sha256((c.ROOT/"data"/name).read_bytes()).hexdigest()==digest)
    account=self_test()
    checks.extend(account["checks"])
    study=prepare()
    meta=study.meta
    design=json.loads((c.OUT/"design.json").read_text())
    check("Histórico usou a composição final",design["holdings_sha256"]==study.exposures.source_hash)
    allocation=pd.read_csv(c.OUT/"allocation.csv").set_index("ticker")
    check("61 candidatos preservados",len(allocation)==61 and allocation.index.is_unique)
    w=allocation.weight
    check("Peso líquido de 100%",abs(w.sum()-1)<1e-8)
    check("Limites assinados e bruto atuais",w.max()<=c.LONG_MAX+1e-7 and w.min()>=-c.SHORT_MAX-1e-7 and w.abs().sum()<=c.GROSS_MAX+1e-7)
    limits=pd.read_csv(c.OUT/"limits.csv")
    check("Todos os limites look-through atuais",(limits.gross_exposure<=limits["limit"]+2e-6).all())
    # Independent row-weight aggregation, including shared company classes.
    h=study.exposures.holdings.copy()
    h["contribution"]=h.etf.map(w.abs()).fillna(0)*h.weight.abs()
    stocks=h.loc[h.asset_class.astype(str).str.lower().isin(["equity","stock","stocks","equities"])]
    company=stocks.groupby("issuer_id").contribution.sum()
    check("Empresa por soma direta das posições",company.max()<=c.COMPANY_MAX+2e-6)
    exposure=pd.read_csv(c.OUT/"lookthrough.csv")
    saved=exposure.loc[exposure.kind.eq("company")].set_index("name").gross
    overlap=company.index.intersection(saved.index)
    check("CSV de empresas reconcilia com composição original",np.allclose(company.reindex(overlap),saved.reindex(overlap),atol=1e-10))
    # Historical executed weights, not merely pre-band optimizer diagnostics.
    weights=pd.read_csv(c.OUT/"weights.csv",parse_dates=["date","signal_date"])
    trades=pd.read_csv(c.OUT/"trades.csv",parse_dates=["date","signal_date"])
    ledger=pd.read_csv(c.OUT/"accounting.csv",parse_dates=["date"])
    returns=pd.read_csv(c.OUT/"daily_returns.csv",index_col=0,parse_dates=True)
    A,b,labels=study.exposures.select(list(meta.index))
    sparse=csr_matrix(A)
    policy=["Long-short","Somente comprado","Setor 30%","Setor 40%","Aluguel 5%"]
    worst=0.
    for label in policy:
        records=weights.loc[weights.strategy.eq(label)].pivot(index="date",columns="ticker",values="weight").reindex(columns=meta.index).fillna(0)
        upper=b.copy()
        for i,name in enumerate(labels):
            if name.startswith("sector:") and label.startswith("Setor"):
                upper[i]=.30 if "30" in label else .40
        values=sparse@records.abs().to_numpy().T
        violation=float(np.max(values-upper[:,None]))
        worst=max(worst,violation)
        check(label+": concentração executada",violation<2e-6)
        check(label+": orçamento assinado executado",np.allclose(records.sum(axis=1),1,atol=1e-8) and records.max().max()<=c.LONG_MAX+1e-7 and records.min().min()>=(0 if label=="Somente comprado" else -c.SHORT_MAX)-1e-7 and records.abs().sum(axis=1).max()<=(1 if label=="Somente comprado" else c.GROSS_MAX)+1e-7)
    monthly=trades.loc[trades.event.eq("monthly")]
    check("Sinal antes da execução",(monthly.signal_date<monthly.date).all())
    for row in monthly.itertuples():
        chosen=weights.loc[weights.strategy.eq(row.strategy)&weights.date.eq(row.date)]
        held=chosen.loc[chosen.weight.abs()>1e-10,"ticker"].tolist()
        check_age=study.quote_age.loc[row.date,held]
        if (check_age!=0).any():raise AssertionError("Ordem sem cotação observada: "+str(row.date))
    checks.append("Todas as execuções têm cotação observada no dia")
    # Reconstruct dollar P&L from previous signed positions and observed prices.
    max_account_error=0.
    for strategy,rows in ledger.groupby("strategy"):
        rows=rows.sort_values("date")
        strategy_weights=weights.loc[weights.strategy.eq(strategy)]
        held=pd.Series(dtype=float);previous=None;nav=1.
        for row in rows.itertuples():
            pnl=0.
            if len(held):
                factor=study.prices.loc[row.date,held.index]/study.prices.loc[previous,held.index]
                pnl=float(held@(factor-1))
                held=held*factor
            charges=row.management_cost+row.borrow_cost+row.financing_cost-getattr(row,"collateral_credit",0.)-getattr(row,"cash_interest",0.)
            expected=nav+pnl-charges-row.trading_cost
            error=abs(expected-row.nav)
            max_account_error=max(max_account_error,error)
            if error>1e-9:raise AssertionError(f"Conservação de NAV {strategy} {row.date}: {error}")
            tx=strategy_weights.loc[strategy_weights.date.eq(row.date)]
            if len(tx):held=tx.set_index("ticker").weight*row.nav;held=held[held.abs()>1e-14]
            if row.forced_liquidation:held=pd.Series(dtype=float)
            recorded=returns.loc[row.date,strategy]
            if nav>0 and abs(recorded-(row.nav/nav-1))>1e-10:raise AssertionError("Retorno não reconcilia com NAV")
            previous=row.date;nav=row.nav
    checks.append("P&L diário reconstruído sem usar a classe Account")
    checks.append("Retornos diários reconciliam com evolução do patrimônio")
    check("Nenhuma insolvência omitida",not ledger.bankrupt.any())
    paired=json.loads((c.OUT/"mc_summary.json").read_text())
    dynamic=json.loads((c.OUT/"mc_dynamic_summary.json").read_text())
    check("Monte Carlo pareado completo",paired["paths"]==10000 and paired["horizon_months"]==300)
    check("Monte Carlo dinâmico completo",dynamic["paths"]==50 and dynamic["test_months"]==60 and dynamic["optimizer_fits"]==6000)
    for name,digest in dynamic["fingerprints"].items():
        check("Fonte da simulação: "+name,hashlib.sha256((c.ROOT/"pipeline"/name).read_bytes()).hexdigest()==digest)
    for name in ["mc_verification.json","mc_dynamic_verification.json"]:
        payload=json.loads((c.OUT/name).read_text(encoding="utf-8"))
        check("Verificação: "+name,bool(payload.get("passed")))
    temporal=json.loads((c.OUT/"temporal_control_summary.json").read_text())
    check("Controle temporal não usa fotografia atual",temporal["current_composition_used"] is False)
    output=dict(passed=True,count=len(checks),checks=checks,max_exposure_violation=worst,
                max_dollar_accounting_error=max_account_error,
                scope="Numerical/operational verification. Historical look-through is frozen retrospectively, not certified point-in-time.",
                margin_calls=int(ledger.forced_liquidation.sum()),insolvencies=int(ledger.bankrupt.sum()))
    (c.OUT/"verification.json").write_text(json.dumps(output,indent=2,ensure_ascii=False),encoding="utf-8")
    print("v2 verificações aprovadas:",len(checks),flush=True)
    return output
