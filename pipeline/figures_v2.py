"""Three English figures in the established MSDS 451 report palette."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import PercentFormatter
from . import config_v2 as c

INK, MUTED, LINE = '#1c2420', '#5c6b63', '#d5ded8'
GREEN, BLUE, GOLD, RED = '#1f6b56', '#24558a', '#a8843a', '#8e3a32'
COLORS = {'Long-short': GREEN, 'Long only': BLUE, 'Equal weight': GOLD, 'VT': MUTED}
LABELS = {'Long-short': 'Long/short', 'Long only': 'Long only', 'Equal weight': 'Equal weight', 'VT': 'VT'}
ETF_COLORS = {'VOO': '#0e2744', 'VTV': BLUE, 'VYM': '#3d6ea8', 'DGRO': '#5c83ac',
              'VOOG': '#7fa4d4', 'CNDX': '#0e2744', 'VWO': '#7dbeab',
              'IWMO': '#1f8a72', 'DIVO11': '#b8862a'}
COMPANIES = {'MICRONTECHNOLOGY': 'Micron Technology', 'NVIDIA': 'Nvidia',
             'BROADCOM': 'Broadcom', 'APPLE': 'Apple', 'MICROSOFT': 'Microsoft',
             'ALPHABET': 'Alphabet', 'JPMORGANCHASE': 'JPMorgan Chase', 'EXXONMOBIL': 'Exxon Mobil'}


def save(fig, name):
    fig.tight_layout()
    fig.savefig(c.FIG / (name + '.svg'))
    fig.savefig(c.FIG / (name + '.png'), dpi=150)
    plt.close(fig)


def run():
    c.FIG.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.family': ['Segoe UI', 'DejaVu Sans'], 'font.size': 10,
        'svg.fonttype': 'none', 'text.color': INK, 'axes.labelcolor': INK,
        'axes.edgecolor': LINE, 'xtick.color': MUTED, 'ytick.color': MUTED,
        'grid.color': LINE, 'axes.spines.top': False, 'axes.spines.right': False,
        'figure.facecolor': 'white', 'axes.facecolor': 'white', 'legend.frameon': False})
    returns = pd.read_csv(c.OUT / 'daily_returns.csv', index_col=0, parse_dates=True)
    fig, axes = plt.subplots(2, 1, figsize=(9, 6), sharex=True, gridspec_kw={'height_ratios': [2, 1]})
    for name, color in COLORS.items():
        wealth = (1 + returns[name]).cumprod()
        axes[0].plot(wealth.index, 100 * wealth, label=LABELS[name], color=color, lw=1.8)
        peak = np.maximum.accumulate(np.r_[1., wealth.to_numpy()])[1:]
        axes[1].plot(wealth.index, wealth / peak - 1, color=color, lw=1.3)
    axes[0].set_title('Growth and drawdown, after costs')
    axes[0].set_ylabel('Starting capital = 100')
    axes[0].legend(ncol=2)
    axes[1].set_ylabel('Decline from peak')
    axes[1].yaxis.set_major_formatter(PercentFormatter(1))
    for ax in axes:
        ax.grid(alpha=.5)
    save(fig, '01-history')
    allocation = pd.read_csv(c.OUT / 'allocation.csv').set_index('ticker')
    weights = allocation.weight[allocation.weight.abs() > .0001].sort_values()
    fig, ax = plt.subplots(figsize=(9, max(3, len(weights) * .24)))
    ax.barh(weights.index, weights, color=[RED if x < 0 else ETF_COLORS.get(t, GREEN) for t, x in weights.items()])
    ax.axvline(0, color=MUTED, lw=.7)
    ax.xaxis.set_major_formatter(PercentFormatter(1))
    ax.grid(axis='x', alpha=.5)
    ax.set_title('Proposed allocation: long and short positions')
    save(fig, '02-weights')
    exposures = pd.read_csv(c.OUT / 'lookthrough.csv')
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    for ax, kind, title, cap in zip(axes, ['company', 'sector'],
            ['Largest companies — gross exposure', 'Largest sectors — gross exposure'], [c.COMPANY_MAX, c.SECTOR_MAX]):
        selected = exposures.loc[exposures.kind.eq(kind) & ~exposures.name.str.startswith('Unidentified')].nlargest(8, 'gross').sort_values('gross')
        names = selected.name.str.replace('issuer:', '', regex=False).str.replace('United States:', '', regex=False)
        if kind == 'company':
            names = names.map(lambda x: COMPANIES.get(x, x))
        ax.barh(names, selected.gross, color=BLUE)
        ax.axvline(cap, color=GOLD, ls='--', lw=1, label='Cap')
        ax.xaxis.set_major_formatter(PercentFormatter(1))
        ax.set_title(title, fontsize=10)
        ax.grid(axis='x', alpha=.5)
        ax.legend()
    save(fig, '03-exposures')
