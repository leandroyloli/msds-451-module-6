"""English Checkpoint B report, using the project's established visual style."""
import html
import hashlib
import io
import json
import re

import numpy as np
import pandas as pd
from matplotlib import rc_context
from matplotlib.font_manager import FontProperties
from matplotlib.mathtext import math_to_image

from . import config_v2 as c

LABELS = {'Long-short': 'Long/short', 'Somente comprado': 'Long only',
          'Pesos iguais': 'Equal weight', 'VT': 'VT', 'Setor 30%': 'Sector cap 30%',
          'Setor 40%': 'Sector cap 40%', 'Aluguel 5%': 'Borrow fee 5%'}
ROLES = {'VOO': 'Broad US equities', 'VTV': 'US value', 'VYM': 'US dividends',
         'DGRO': 'US dividend growth', 'VOOG': 'S&P 500 growth',
         'VWO': 'Emerging-market equities', 'CNDX': 'Nasdaq-100',
         'IWMO': 'Developed-market momentum', 'DIVO11': 'Brazilian dividends'}


def pct(x, d=2):
    return '—' if pd.isna(x) else f'{x:.{d}%}'


def num(x, d=3):
    return '—' if pd.isna(x) else f'{x:.{d}f}'


def esc(x):
    return html.escape(str(x))


def table(df):
    return '<div class="scroll">' + df.to_html(index=False, border=0, escape=True) + '</div>'


def figure(name, caption):
    svg = (c.FIG / (name + '.svg')).read_text(encoding='utf-8')
    svg = svg[svg.index('<svg'):]
    svg = re.sub(r'<!--.*?-->|<metadata>.*?</metadata>', '', svg, flags=re.S)
    svg = re.sub(r'>\s+<', '><', svg)
    def compact(match):
        value = re.sub(r'-?\d+\.\d+', lambda x: f'{float(x.group()):.3f}'.rstrip('0').rstrip('.'), match.group(1))
        return 'd="' + re.sub(r'\s+', ' ', value) + '"'
    svg = re.sub(r'\bd="([^"]+)"', compact, svg)
    for identifier in sorted(set(re.findall(r'\bid="([^"]+)"', svg)), key=len, reverse=True):
        unique = name + '-' + identifier
        svg = svg.replace('id="' + identifier + '"', 'id="' + unique + '"')
        svg = svg.replace('url(#' + identifier + ')', 'url(#' + unique + ')')
        svg = svg.replace('href="#' + identifier + '"', 'href="#' + unique + '"')
    return '<figure>' + svg + '<figcaption>' + caption + '</figcaption></figure>'


def latex_equation(tex):
    """Typeset LaTeX as embedded SVG, following the earlier report convention."""
    buffer = io.BytesIO()
    with rc_context({'mathtext.fontset': 'cm', 'svg.hashsalt': 'msds451',
                     'savefig.transparent': True}):
        math_to_image('$' + tex + '$', buffer, prop=FontProperties(size=16),
                      format='svg', color='#1c2420')
    svg = buffer.getvalue().decode('utf-8')
    svg = svg[svg.index('<svg'):]
    svg = re.sub(r'<metadata>.*?</metadata>|<!--.*?-->', '', svg, flags=re.S)
    prefix = 'eq-' + hashlib.sha256(tex.encode()).hexdigest()[:10] + '-'
    for identifier in set(re.findall(r'\bid="([^"]+)"', svg)):
        svg = svg.replace('id="' + identifier + '"', 'id="' + prefix + identifier + '"')
        svg = svg.replace('href="#' + identifier + '"', 'href="#' + prefix + identifier + '"')
        svg = svg.replace('url(#' + identifier + ')', 'url(#' + prefix + identifier + ')')
    svg = svg.replace('#1c2420', 'currentColor')
    return '<div class="equation" role="img" aria-label="' + esc(tex) + '">' + svg + '</div>'


def run():
    metrics = pd.read_csv(c.OUT / 'metrics.csv', index_col=0)
    allocation = pd.read_csv(c.OUT / 'allocation.csv').set_index('ticker')
    design = json.loads((c.OUT / 'design.json').read_text(encoding='utf-8'))
    mc = json.loads((c.OUT / 'mc_summary.json').read_text(encoding='utf-8'))
    dynamic = json.loads((c.OUT / 'mc_dynamic_summary.json').read_text(encoding='utf-8'))
    temporal = json.loads((c.OUT / 'temporal_control_summary.json').read_text(encoding='utf-8'))
    coverage = pd.read_csv(c.DATA / 'holdings/coverage.csv')
    brl = pd.read_csv(c.OUT / 'metrics_brl.csv').set_index('strategy')
    references = json.loads((c.ROOT / 'resources/references-v2.json').read_text(encoding='utf-8'))['references']
    references.extend([
        dict(authors='Markowitz, Harry', year=1952, title='Portfolio Selection',
             url='../resources/reading-notes.md#markowitz',
             access='Course copy; introduction and mean–variance framework inspected.',
             limits='The frontier depends on estimated returns and covariances.'),
        dict(authors='Ross, Sheldon M.', year=2011,
             title='An Elementary Introduction to Mathematical Finance, Chapter 9, pp. 165–192',
             url='../resources/reading-notes.md#ross',
             access='Required reading; utility and portfolio-selection passages, mainly pp. 166–176, consulted.',
             limits='The study does not estimate the investor’s personal utility function.'),
        dict(authors='Sharpe, William F.', year=1994, title='The Sharpe Ratio',
             url='https://web.stanford.edu/~wfsharpe/art/sr/sr.htm',
             access='Author’s original text accessed.',
             limits='A variability ratio does not summarize tail losses or recovery time.')])
    weights = allocation.weight[allocation.weight.abs() > .0001].sort_values(ascending=False)
    short = float(-weights.clip(upper=0).sum())
    long = float(weights.clip(lower=0).sum())
    if short > .0001:
        short_text = f'The solution holds {pct(long, 1)} long and {pct(short, 1)} short: 100% net and {pct(long + short, 1)} gross exposure.'
    else:
        short_text = 'The current solution has no short positions. They were allowed; the estimates, costs and limits did not justify opening them at this decision.'
    weight_table = table(pd.DataFrame({'ETF': weights.index,
        'Exposure': [ROLES.get(t, str(allocation.loc[t, 'name'])) for t in weights.index],
        'Weight': [pct(x) for x in weights], 'Position': ['Long' if x > 0 else 'Short' for x in weights]}))
    main = metrics.loc['Long-short']
    comparison = ('undefined' if pd.isna(main.sharpe) or pd.isna(metrics.loc['Somente comprado', 'sharpe'])
                  else 'higher than' if main.sharpe > metrics.loc['Somente comprado', 'sharpe'] else 'no higher than')
    def performance(names):
        return table(pd.DataFrame([{'Strategy': LABELS.get(t, t), 'CAGR': pct(metrics.loc[t, 'cagr']),
            'Volatility': pct(metrics.loc[t, 'volatility']), 'Sharpe': num(metrics.loc[t, 'sharpe']),
            'Maximum drawdown': pct(metrics.loc[t, 'max_drawdown'])} for t in names]))
    def simulation_table(rows, insolvencies=False):
        values = []
        for row in rows:
            value = {'Strategy': LABELS.get(row['strategy'], row['strategy']),
                     'Median CAGR': pct(row['cagr']['p50']),
                     'CAGR p05–p95': pct(row['cagr']['p05']) + ' to ' + pct(row['cagr']['p95']),
                     'Median max. drawdown': pct(row['max_drawdown']['p50'])}
            if insolvencies:
                value['Insolvencies'] = row['insolvent_paths']
            values.append(value)
        return table(pd.DataFrame(values))
    limits = table(pd.DataFrame([
        ('Long / short ETF weight', 'Up to +20% / down to −5%'),
        ('Net / gross exposure', '100% / up to 140%'),
        ('Issuer: share classes of one company', 'Up to 5% gross'),
        ('Sector / subindustry', 'Up to 35% / 20% gross'),
        ('United States / each other country', 'Up to 75% / 25% gross'),
        ('Underlying securities’ quotation currency', 'Up to 85% gross per currency'),
        ('Unidentified exposure', 'Up to 2% in each dimension'),
        ('Monthly CVaR at 95%', 'Up to 15% in estimated scenarios')], columns=['Constraint', 'Rule']))
    catalog = allocation.reset_index().merge(coverage[['etf', 'status', 'as_of']], left_on='ticker', right_on='etf', how='left')
    catalog['weight'] = catalog.weight.map(pct)
    catalog['status'] = catalog.status.map({'complete_issuer': 'Complete source file',
                                          'not_recovered': 'Not recovered'}).fillna('Not recovered')
    for name in ['eligible', 'representative']:
        catalog[name] = catalog[name].map({True: 'Yes', False: 'No'})
    catalog_table = table(catalog[['ticker', 'name', 'quote_currency', 'status', 'as_of', 'eligible', 'representative', 'weight']]
        .rename(columns={'ticker': 'ETF', 'name': 'Name', 'quote_currency': 'ETF currency',
                         'status': 'Holdings source', 'as_of': 'As of', 'eligible': 'Eligible',
                         'representative': 'Representative', 'weight': 'Weight'}).fillna('Not recovered'))
    historical_weights = pd.read_csv(c.OUT / 'weights.csv')
    shorts = historical_weights.loc[historical_weights.strategy.eq('Long-short')].groupby('date').weight.apply(lambda x: -x.clip(upper=0).sum())
    full_sources = int(coverage.status.astype(str).str.contains('complete|derived', regex=True).sum())
    gate = dynamic.get('probability_sharpe_gain_point_one_over_both', np.nan)
    sources = ''.join(f'<li>{esc(r["authors"])} ({r["year"]}). <a href="{esc(r["url"])}">{esc(r["title"])}</a>.<small>{esc(r["access"])} {esc(r["limits"])}</small></li>' for r in references)
    css = (c.ROOT / 'pipeline/report_style.css').read_text(encoding='utf-8')
    optimization = ''.join(latex_equation(tex) for tex in [
        r'\max_{\mathbf{w}}\quad\frac{\boldsymbol{\mu}^{\top}\mathbf{w}-r_f-C(\mathbf{w})}{\sqrt{\mathbf{w}^{\top}\Sigma\mathbf{w}}}',
        r'\mathbf{1}^{\top}\mathbf{w}=1,\qquad -s\mathbf{1}\leq\mathbf{w}\leq\ell\mathbf{1}',
        r'\Vert\mathbf{w}\Vert_1\leq G,\qquad A\left|\mathbf{w}\right|\leq\mathbf{b}',
        r'\operatorname{CVaR}_{95\%}(\mathrm{monthly\ loss})\leq 15\%'
    ])
    body = f'''
<div class="layout">
<nav aria-label="Report sections"><p class="nav-label">Checkpoint B</p><a href="#intro">01 · Introduction</a><a href="#literature">02 · Literature</a><a href="#methods">03 · Methods</a><a href="#results">04 · Results</a><a href="#conclusions">05 · Conclusions</a><a href="#data">Data &amp; sources</a></nav>
<main>
<header><p class="eyebrow">Northwestern University · MSDS 451 · Fall 2026</p>
<h1>A portfolio of ETFs for the growth block</h1>
<p class="dek">Long and short positions, with concentration limits based on the companies and sectors inside the funds.</p>
<dl class="facts"><div><dt>Author</dt><dd>Leandro Loli</dd></div><div><dt>Term project</dt><dd>Checkpoint B</dd></div><div><dt>Market-data cutoff</dt><dd>October 23, 2026</dd></div></dl>
<div class="notice"><p><strong>The proposal.</strong> Select ETFs and weights for block C. Positive weights are purchases; negative weights are short sales when the rule chooses them. VT and equal weight remain benchmarks.</p></div>
<div class="notice warning"><p><strong>Main evidence limit.</strong> Holdings are snapshots from September/October 2026, frozen in the historical experiment. Prices and signals respect time order, but the test <strong>does not establish that company and sector limits would have held with the ETFs’ actual historical holdings.</strong></p></div></header>
<section id="intro"><h2>1. Introduction — what I want to solve</h2>
<p>My aim is to grow wealth over many years, participate in rising markets and understand the losses I may face. This study chooses ETFs and weights only for the growth block. The safety and inflation blocks stay outside its decisions, collateral and financing.</p>
<p>The first users are investors like me: people who spend in reais, protect dated expenses separately and want the remaining capital to grow without picking individual stocks. The application is the program that applies the allocation rule.</p>
<p>The question is whether controlled short sales improve net results over the same long-only rule, without hiding concentration or leverage. Long market histories matter because a rule that works during an expansion may fail in a downturn.</p></section>
<section id="literature"><h2>2. Literature review — what supports the rule</h2>
<p>Markowitz connects weights, expected returns and covariance. Jorion motivates reducing error in estimated means; Ledoit–Wolf does this for the risk matrix. Rockafellar and Uryasev provide the CVaR framework for controlling modeled tail losses. Company classifications use issuer records and the available sector hierarchy.</p>
<p>The previous assignment found higher maximum returns when shorts were allowed, together with higher risk and incomplete costs. This study adds borrowing, financing and collateral. None of these references establishes a universally optimal concentration percentage.</p></section>
<section id="methods"><h2>3. Methods — the rule in a few steps</h2>
<p>Of 61 candidates, {full_sources} have complete source files; {design['complete_composition_tickers']} meet the equity-coverage requirement. At the latest decision, {design['eligible_latest']} pass the filters and {design['representatives_latest']} remain after selecting one representative for equivalent exposures. Eligibility requires 60 complete monthly returns and trailing six-month median daily dollar volume of at least US$1 million, with at least 100 observations.</p>
<p>Adjusted prices and exchange rates come from Yahoo Finance, with a cutoff of October 23, 2026 and complete months through September. Holdings come from Vanguard, BlackRock, State Street and CVM. Distributions are already reflected in adjusted prices and are not added twice. Price movements are described by 100 × ln(P<sub>t</sub>/P<sub>t−1</sub>); wealth and weights use simple USD returns.</p>
<p>There are no 25 common years of actual data for this rule and selected universe. The July 2019–September 2026 experiment includes COVID and 2022, but not the 2001 or 2008 crises.</p>
{limits}
<p>These are study policies. A 5% company position limits the direct impact of an isolated 50% shock to 2.5 percentage points of wealth; other assets may fall together. Share classes are combined by issuer, but wider corporate groups need further mapping. A security’s quotation currency is an exchange-rate proxy. Monthly CVaR is not a maximum drawdown guarantee.</p>
<div class="math">{optimization}</div>
<p class="meta">w: weights; μ: expected returns; r<sub>f</sub>: cash rate; Σ: covariance; A: underlying exposures; b: limits; C: costs; s/ℓ: short/long bounds; G: gross-exposure cap.</p>
<p><strong>Sharpe</strong> measures return above cash per unit of volatility. <strong>Shrinkage</strong> reduces confidence in noisy estimates. <strong>CVaR</strong> measures average loss in the bad tail of the scenarios. Means use an adaptation inspired by Bayes–Stein; covariance uses Ledoit–Wolf.</p>
<p>The signal is monthly. Orders wait for the first later day with observed quotes for the ETFs involved. Existing holdings may carry a prior quote for valuation only, for at most 14 calendar days, with quote age recorded. Three-percentage-point bands use the decision snapshot, never the execution-day return. If no positive expected excess return is feasible, the rule uses constrained minimum variance.</p>
<p>Limits apply to the target and monthly rebalance; prices may cause drift between decisions. Simplified maintenance margin is monitored daily.</p>
<p>Assumed costs are 0.10% of traded value, 0.25% annual management, 2% annual borrowing on shorts, and financing at cash plus one percentage point. Collateral is separate from debt and earns no rebate. Projected monthly trading cost is annualized in the objective; the account charges only costs incurred. Internal fund expenses already reflected in prices are not deducted again. Actual borrow availability, spreads and individual taxes remain unverified.</p></section>
<section id="results"><h2>4. Results — allocation and behavior</h2><h3>The model’s proposed allocation</h3>
<p>{short_text} All weights belong to block C. Return estimates end in September; holdings files have their own dates. Any short position would require a confirmed borrow before execution.</p>
{weight_table}
<p>ETF and country caps help shape this solution. These weights are not a universal optimum.</p>
{figure('02-pesos', 'Rounded weights; the CSV retains full precision and all 61 candidates. Permission to short does not require a short position.')}
<h3>Historical experiment, after costs</h3>
{performance(['Long-short', 'Somente comprado', 'Pesos iguais', 'VT'])}
<p>From July 2019 to September 2026, the long/short Sharpe is {comparison} the long-only Sharpe. Shorts appeared in {int((shorts > .0001).sum())} of {len(shorts)} decisions, reaching {pct(shorts.max(), 1)} of wealth. These results describe the frozen-holdings experiment.</p>
<p>Against VT over the same period, long/short regression alpha is {num(main.get('alpha_annual', np.nan) * 100, 2)} percentage points per year and beta is {num(main.get('beta', np.nan), 2)}. These are descriptive historical estimates, not causal effects or evidence of skill.</p>
{figure('01-historico', 'Net returns, equal starting capital and no invented contributions. Current holdings are frozen throughout the retrospective experiment.')}
<p>Converted to reais, the portfolio’s nominal CAGR is {pct(brl.loc['Long-short', 'cagr'])}, with a maximum drawdown of {pct(brl.loc['Long-short', 'max_drawdown'])}. This is the same portfolio translated through FX, before inflation and individual taxes. BRL Sharpe is not computed against US cash.</p>
{figure('03-exposicoes', 'Gross exposure adds long and short exposures instead of netting away concentration. Countries, currencies and the full limits are retained in the CSV files.')}
<h3>Monte Carlo — other sequences of market returns</h3>
<p class="meta">CAGR is compound annual growth. The p05–p95 range contains the central 90% of simulated outcomes.</p>
<p>The paired bootstrap uses {mc['paths']:,} paths, sampling the same blocks for strategies, cash and FX. It resamples net returns without charging costs twice. A separate experiment generates ETF returns and repeats the decisions: {dynamic['paths']} paths, {dynamic['test_months']} evaluated months and {dynamic['optimizer_fits']:,} optimizations.</p>
<details><summary>Paired replay: 25 synthetic years</summary>{simulation_table([s for s in mc['strategies'] if s['currency'] == 'USD'])}<p>These are resampled net returns, without new allocation decisions. Drawdown is measured at month-end and is not directly comparable with daily historical drawdown. Twenty-five years of bootstrap do not replace an actual 1999–2024 history.</p></details>
{simulation_table(dynamic['strategies'], insolvencies=True)}
<p>These are sample-conditional scenarios, not calibrated future probabilities. The replay spans {mc['horizon_months'] // 12} synthetic years; the reoptimized test spans {dynamic['test_months'] // 12}. Frozen holdings and approximate monthly execution still limit both. The synthetic experiment used the minimum-variance safeguard in {dynamic.get('minimum_risk_safeguard_fits', 0)} fits.</p>
<details><summary>Sensitivities and verification files</summary>{performance(metrics.index)}<p>The 30%/40% sector caps and 5% borrow-fee cases do not replace the base rule after seeing their results. A separate price/liquidity control, without current holdings, obtained CAGR {pct(temporal['cagr'])} and Sharpe {num(temporal['sharpe'])}. It checks market-data time order, not historical company limits; its universe and constraints differ.</p><p><a href="../output/limits.csv">All limits</a> · <a href="../output/trades.csv">Trades</a> · <a href="../output/accounting.csv">Accounting</a> · <a href="../output/mc_dynamic_verification.json">Synthetic checks</a> · <a href="../output/temporal_control_summary.json">Temporal control</a></p></details></section>
<section id="conclusions"><h2>5. Conclusions — what the evidence supports</h2>
<p>The proposal is the ETF portfolio found for block C, with the risks and costs of maintaining it. Benchmarks measure its advantage; missing a performance target does not automatically replace the mandate with one ETF.</p>
<p>Short sales did not demonstrate a net improvement over the long-only version in this test. The Checkpoint A target of a 0.1 Sharpe advantage over both VT and equal weight was not demonstrated in the history or replay. It appears in {pct(gate, 1)} of dynamic paths: a conditional simulation frequency, not a future success probability. Shorts are not forced to change this conclusion.</p>
<p>Underlying concentration limits improve on ticker-only limits. The evidence remains research evidence: complete historical holdings and actual borrowing terms are still needed for operational validation. A rule can compound well and still lose heavily in a crisis.</p>
<p>For Checkpoint C, the next steps are historical snapshots or prospective validation using then-known holdings, confirmation of borrowing and margin by market, and continued net comparison with the long-only rule. A launch decision should wait for that work.</p></section>
<section id="data"><h2>Data, sources and reproduction</h2>
<details><summary>All 61 candidates and holdings coverage</summary>{catalog_table}</details>
<p><a href="../output/allocation.csv">Exact weights</a> · <a href="../output/lookthrough.csv">Underlying exposures</a> · <a href="../output/design.json">Assumptions</a> · <a href="../resources/holdings-v2.md">Holdings audit</a> · <a href="../resources/execution-v2.md">Account and financing</a> · <a href="../README.md">Run the study</a></p>
<p>The <a href="../resources/assignment.md">assignment instructions</a> allocate ten points to each of the five report sections. Backtests and simulations go beyond Checkpoint B’s minimum preliminary findings. The requested GitHub deposit awaits the author’s review; nothing has been published or submitted.</p>
<details><summary>References and access limits</summary><ol class="refs">{sources}</ol></details></section>
<footer>MSDS 451 · Term Project Checkpoint B · Local research report for author review.</footer>
</main></div>
'''
    document = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Term Project Checkpoint B | Leandro Loli</title><style>' + css + '</style></head><body>' + body + '</body></html>'
    path = c.ROOT / 'report/checkpoint-b.html'
    path.write_text(document, encoding='utf-8')
    print('English HTML:', path, len(document), 'characters', flush=True)
    return path


if __name__ == '__main__':
    run()
