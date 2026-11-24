import sys, pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt, matplotlib.dates as mdates
df = pd.read_csv(sys.argv[1], parse_dates=["Date"]).set_index("Date").sort_index()
df.columns = ["close", "pos"]
df["qqq_ret"] = df.close.pct_change()
df["optex_ret"] = df.pos.shift(1) / 100 * df.qqq_ret   # position held from prior close
d = df.loc["2025-01-01":].copy()
d.iloc[0, d.columns.get_loc("optex_ret")] = d.iloc[0].optex_ret  # first day uses 2024-12-31 position
d["optex_cum"] = (1 + d.optex_ret).cumprod() - 1
d["qqq_cum"] = (1 + d.qqq_ret).cumprod() - 1
def stats(r):
    eq = (1 + r).cumprod(); yrs = len(r) / 252
    return dict(total=eq.iloc[-1]-1, cagr=eq.iloc[-1]**(1/yrs)-1, vol=r.std()*np.sqrt(252),
                sharpe=r.mean()/r.std()*np.sqrt(252), mdd=(eq/eq.cummax()-1).min())
s_o, s_q = stats(d.optex_ret), stats(d.qqq_ret)
for k in s_o: print(f"{k:7s} OPTEX {s_o[k]:8.2%}  QQQ {s_q[k]:8.2%}" if k!="sharpe" else f"{k:7s} OPTEX {s_o[k]:8.2f}  QQQ {s_q[k]:8.2f}")
for y in (2025, 2026):
    print(y, f"OPTEX {(1+d.optex_ret[str(y)]).prod()-1:.2%}  QQQ {(1+d.qqq_ret[str(y)]).prod()-1:.2%}")
d.to_csv("optex_returns_2025.csv")

ink, ink2, grid, surf = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
c_o, c_q = "#2a78d6", "#eb6834"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": grid, "axes.labelcolor": ink2,
                     "xtick.color": ink2, "ytick.color": ink2, "axes.facecolor": surf, "figure.facecolor": surf})
fig, (a1, a2, a3) = plt.subplots(3, 1, figsize=(12, 9), sharex=True,
                                 gridspec_kw={"height_ratios": [3, 1.3, 1.3], "hspace": 0.12})
a1.plot(d.index, d.optex_cum*100, c=c_o, lw=2, label="OPTEX")
a1.plot(d.index, d.qqq_cum*100, c=c_q, lw=2, label="QQQ buy & hold")
for col, c, lab in [("optex_cum", c_o, "OPTEX"), ("qqq_cum", c_q, "QQQ")]:
    a1.annotate(f"{lab} {d[col].iloc[-1]:+.1%}", (d.index[-1], d[col].iloc[-1]*100), xytext=(6, 0),
                textcoords="offset points", va="center", color=ink, fontsize=10, fontweight="bold")
a1.axhline(0, c=ink2, lw=0.8)
a1.set_ylabel("Cumulative return (%)"); a1.legend(frameon=False, loc="upper left")
a1.set_title(f"OPTEX vs QQQ — cumulative returns since 1 Jan 2025 (through {d.index[-1]:%d %b %Y})",
             loc="left", color=ink, fontsize=13, fontweight="bold", pad=22)
a1.text(0, 1.01, f"OPTEX: CAGR {s_o['cagr']:.1%} · vol {s_o['vol']:.1%} · Sharpe {s_o['sharpe']:.2f} · max DD {s_o['mdd']:.1%}     "
        f"QQQ: CAGR {s_q['cagr']:.1%} · vol {s_q['vol']:.1%} · Sharpe {s_q['sharpe']:.2f} · max DD {s_q['mdd']:.1%}",
        transform=a1.transAxes, color=ink2, fontsize=9)
for col, c in [("optex_ret", c_o), ("qqq_ret", c_q)]:
    eq = (1 + d[col]).cumprod(); a2.plot(d.index, (eq/eq.cummax()-1)*100, c=c, lw=1.5)
a2.set_ylabel("Drawdown (%)")
a3.step(d.index, d.pos, where="post", c=c_o, lw=1.5); a3.axhline(0, c=ink2, lw=0.8)
a3.set_ylabel("QQQ exposure (%)")
for a in (a1, a2, a3):
    a.grid(axis="y", c=grid, lw=0.8); a.spines[["top", "right"]].set_visible(False)
a3.xaxis.set_major_locator(mdates.MonthLocator(interval=2)); a3.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
a1.margins(x=0.01); fig.subplots_adjust(right=0.88)
fig.savefig("/home/user/main/optex_returns_2025.png", dpi=150, bbox_inches="tight")
