"""
Grid Sweep Experiment: Evaluation Failure Scaling Law
=====================================================
150 cells (15 S × 10 D), 15 seeds per cell,
error-based regression, raw + summary CSV.

Usage: python grid_sweep_final.py
"""

import numpy as np
from scipy.optimize import minimize
from scipy.stats import spearmanr
from scipy.special import expit
import os, csv, time, warnings
warnings.filterwarnings("ignore")

# ── CONFIG ──
J = 10; I = 10; K = 100; N_SEEDS = 15
S_VALUES = np.round(np.arange(0.00, 0.701, 0.05), 2)  # 15 values: 0.00..0.70
D_VALUES = np.round(np.arange(0.50, 5.01, 0.50), 2)    # 10 values
THETA_TRUE = np.linspace(-2.0, 2.0, J)
A_BASE = np.linspace(1.0, 3.0, I)
OUT = "outputs"; os.makedirs(OUT, exist_ok=True)

def gen_difficulties(D):
    return np.linspace(-D/2, D/2, I)

def gen_mask_biased(S, theta, b, rng):
    if S <= 0: return np.ones((J,I), dtype=int)
    n_obs = max(int(round(J*I*(1-S))), J*2)
    th_n = (theta-theta.min())/(theta.max()-theta.min()+1e-10)
    b_n = (b-b.min())/(b.max()-b.min()+1e-10)
    bias = np.zeros((J,I))
    for j in range(J):
        for i in range(I):
            bias[j,i] = (1.0 - abs(th_n[j]-b_n[i]))**2
    bias = bias/bias.sum()
    fp = bias.flatten()
    chosen = set()
    for j in range(J):
        pj = fp[j*I:(j+1)*I].copy(); pj /= pj.sum()
        for ii in rng.choice(I, size=2, replace=False, p=pj):
            chosen.add(j*I+ii)
    for i in range(I):
        cur = sum(1 for idx in chosen if idx%I==i)
        if cur < 3:
            avail = [jj for jj in range(J) if jj*I+i not in chosen]
            if avail:
                pi = np.array([fp[jj*I+i] for jj in avail]); pi /= pi.sum()+1e-20
                for jj in rng.choice(avail, size=min(3-cur,len(avail)), replace=False, p=pi):
                    chosen.add(jj*I+i)
    rem = n_obs - len(chosen)
    if rem > 0:
        cands = [idx for idx in range(J*I) if idx not in chosen]
        if cands:
            cp = np.array([fp[c] for c in cands]); cp /= cp.sum()+1e-20
            for idx in rng.choice(cands, size=min(rem,len(cands)), replace=False, p=cp):
                chosen.add(idx)
    mask = np.zeros((J,I),dtype=int)
    for idx in chosen: mask[idx//I, idx%I] = 1
    return mask

def gen_mask_mcar(S, rng):
    if S <= 0: return np.ones((J,I), dtype=int)
    n_obs = max(int(round(J*I*(1-S))), J*2)
    chosen = set()
    for j in range(J):
        for ii in rng.choice(I, size=2, replace=False): chosen.add(j*I+ii)
    for i in range(I):
        cur = sum(1 for idx in chosen if idx%I==i)
        if cur < 3:
            avail = [jj for jj in range(J) if jj*I+i not in chosen]
            if avail:
                for jj in rng.choice(avail, size=min(3-cur,len(avail)), replace=False):
                    chosen.add(jj*I+i)
    rem = n_obs - len(chosen)
    if rem > 0:
        cands = [idx for idx in range(J*I) if idx not in chosen]
        if cands:
            for idx in rng.choice(cands, size=min(rem,len(cands)), replace=False):
                chosen.add(idx)
    mask = np.zeros((J,I),dtype=int)
    for idx in chosen: mask[idx//I, idx%I] = 1
    return mask

def gen_responses(theta, a, b, mask, rng):
    scores = np.full((J,I), np.nan)
    for j in range(J):
        for i in range(I):
            if mask[j,i]:
                p = expit(a[i]*(theta[j]-b[i]))
                scores[j,i] = rng.binomial(K, p)/K
    return scores

def rank_avg(scores, mask):
    m = np.zeros(J)
    for j in range(J):
        obs = scores[j, mask[j]==1]
        m[j] = np.mean(obs) if len(obs)>0 else 0.5
    return m

def fit_irt(scores, mask):
    JJ, II = scores.shape
    def nll(params):
        th = params[:JJ]; b = params[JJ:JJ+II]
        la = params[JJ+II:]; a = np.exp(np.clip(la,-3,3))
        cost = 0.5*np.sum(th**2) + 0.5*np.sum(b**2)/4 + 0.5*np.sum(la**2)/0.25
        p = expit(a[None,:] * (th[:,None] - b[None,:]))
        p = np.clip(p, 1e-10, 1-1e-10)
        ll = scores*K*np.log(p) + (1-scores)*K*np.log(1-p)
        ll = np.where(np.isnan(ll), 0, ll)
        cost -= np.sum(ll * mask)
        return cost
    x0 = np.zeros(JJ+2*II)
    bounds = [(-4,4)]*JJ + [(-5,5)]*II + [(-3,3)]*II
    res = minimize(nll, x0, method='L-BFGS-B', bounds=bounds,
                   options={'maxiter':80,'ftol':1e-7})
    return res.x[:JJ], res.x[JJ:JJ+II]

def spear(est, true):
    r, _ = spearmanr(est, true)
    return 0.0 if np.isnan(r) else r

# ── MAIN ──
def run():
    print(f"Grid: {len(S_VALUES)}×{len(D_VALUES)}={len(S_VALUES)*len(D_VALUES)} cells, "
          f"{N_SEEDS} seeds, {len(S_VALUES)*len(D_VALUES)*N_SEEDS} total runs")
    
    raw_rows = []
    summary = []
    total = len(S_VALUES)*len(D_VALUES)
    t0 = time.time()
    cell = 0
    true_top = np.argmax(THETA_TRUE)

    for S in S_VALUES:
        for D in D_VALUES:
            cell += 1
            b = gen_difficulties(D)
            ra, ri, rm = [], [], []
            misrank_b, misrank_m = 0, 0
            irt_ok = 0

            for seed in range(N_SEEDS):
                rng = np.random.default_rng(seed*10000+cell)
                # Biased
                mb = gen_mask_biased(S, THETA_TRUE, b, rng)
                resp = gen_responses(THETA_TRUE, A_BASE, b, mb, rng)
                avg_s = rank_avg(resp, mb)
                rho_a = spear(avg_s, THETA_TRUE)
                ra.append(rho_a)
                if np.argmax(avg_s)!=true_top: misrank_b+=1
                raw_rows.append({'S':S,'D':D,'SD':round(S*D,4),'seed':seed,
                    'miss':'biased','method':'avg','rho':round(rho_a,4),
                    'top_misrank':int(np.argmax(avg_s)!=true_top)})
                try:
                    if S > 0:
                        th_e, _ = fit_irt(resp, mb)
                        rho_i = spear(th_e, THETA_TRUE)
                    else:
                        rho_i = 1.0  # Full coverage → both methods perfect
                        th_e = THETA_TRUE
                    ri.append(rho_i); irt_ok+=1
                    raw_rows.append({'S':S,'D':D,'SD':round(S*D,4),'seed':seed,
                        'miss':'biased','method':'irt','rho':round(rho_i,4),
                        'top_misrank':int(np.argmax(th_e)!=true_top)})
                except:
                    ri.append(np.nan)
                # MCAR
                rng2 = np.random.default_rng(seed*10000+cell+50000)
                mm = gen_mask_mcar(S, rng2)
                resp2 = gen_responses(THETA_TRUE, A_BASE, b, mm, rng2)
                avg_m = rank_avg(resp2, mm)
                rho_m = spear(avg_m, THETA_TRUE)
                rm.append(rho_m)
                if np.argmax(avg_m)!=true_top: misrank_m+=1
                raw_rows.append({'S':S,'D':D,'SD':round(S*D,4),'seed':seed,
                    'miss':'mcar','method':'avg','rho':round(rho_m,4),
                    'top_misrank':int(np.argmax(avg_m)!=true_top)})

            ra=np.array(ra); ri_clean=np.array([x for x in ri if not np.isnan(x)]); rm=np.array(rm)
            n_irt = len(ri_clean)
            summary.append({
                'S':S,'D':D,'SD':round(S*D,4),
                'rho_avg_biased_mean':round(np.mean(ra),4),
                'rho_avg_biased_std':round(np.std(ra),4),
                'rho_avg_biased_mcse':round(np.std(ra)/np.sqrt(N_SEEDS),4),
                'rho_irt_biased_mean':round(np.mean(ri_clean),4) if n_irt>0 else None,
                'rho_irt_biased_std':round(np.std(ri_clean),4) if n_irt>0 else None,
                'rho_irt_biased_mcse':round(np.std(ri_clean)/np.sqrt(n_irt),4) if n_irt>0 else None,
                'delta_rho_mean':round(np.mean(ri_clean)-np.mean(ra),4) if n_irt>0 else None,
                'rho_avg_mcar_mean':round(np.mean(rm),4),
                'rho_avg_mcar_std':round(np.std(rm),4),
                'rho_avg_mcar_mcse':round(np.std(rm)/np.sqrt(N_SEEDS),4),
                'top_misrank_rate_biased':round(misrank_b/N_SEEDS,2),
                'top_misrank_rate_mcar':round(misrank_m/N_SEEDS,2),
                'n_seeds':N_SEEDS, 'n_irt_converged':n_irt
            })
            el=time.time()-t0; eta=el/cell*(total-cell)
            rho_i_show = summary[-1]['rho_irt_biased_mean'] or 0
            print(f"  [{cell:3d}/{total}] S={S:.2f} D={D:.1f} | "
                  f"ρ_avg={summary[-1]['rho_avg_biased_mean']:.3f} "
                  f"ρ_IRT={rho_i_show:.3f} "
                  f"ρ_MCAR={summary[-1]['rho_avg_mcar_mean']:.3f} | {eta:.0f}s")

    print(f"\nDone in {time.time()-t0:.1f}s")

    # Save CSVs
    with open(f"{OUT}/grid_raw_runs.csv",'w',newline='') as f:
        w=csv.DictWriter(f, fieldnames=raw_rows[0].keys()); w.writeheader(); w.writerows(raw_rows)
    with open(f"{OUT}/grid_summary.csv",'w',newline='') as f:
        w=csv.DictWriter(f, fieldnames=summary[0].keys()); w.writeheader(); w.writerows(summary)
    print("Saved CSVs")

    # ── FIGURES ──
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap

    s_list=sorted(set(r['S'] for r in summary))
    d_list=sorted(set(r['D'] for r in summary))
    ns,nd=len(s_list),len(d_list)
    def grid(key):
        g=np.full((nd,ns),np.nan)
        for r in summary:
            si=s_list.index(r['S']); di=d_list.index(r['D'])
            g[di,si]=r[key] if r[key] is not None else np.nan
        return g

    ga=grid('rho_avg_biased_mean'); gi=grid('rho_irt_biased_mean')
    gm=grid('rho_avg_mcar_mean'); gd=grid('delta_rho_mean')

    cmap_rho=LinearSegmentedColormap.from_list('r',['#b71c1c','#e53935','#ff9800','#ffeb3b','#66bb6a','#1b5e20'],N=256)
    cmap_delta=LinearSegmentedColormap.from_list('d',['#e3f2fd','#42a5f5','#1565c0','#0d47a1'],N=256)
    sl=[f"{s:.2f}" for s in s_list]; dl=[f"{d:.1f}" for d in d_list]

    VMIN=0.20; VMAX=1.0  # includes actual minimum (~0.24)

    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    panels = [
        (ga,"A. Simple Average (Biased Missingness)",cmap_rho,VMIN,VMAX,"ρ"),
        (gi,"B. IRT (Biased Missingness)",cmap_rho,VMIN,VMAX,"ρ"),
        (gm,"C. Simple Average (MCAR Missingness)",cmap_rho,VMIN,VMAX,"ρ"),
        (gd,"D. IRT Advantage (Δρ = ρ_IRT − ρ_avg)",cmap_delta,0.0,0.6,"Δρ"),
    ]
    for ax,(g,title,cm,vn,vx,lb) in zip(axes.flat,panels):
        im=ax.imshow(g,cmap=cm,vmin=vn,vmax=vx,aspect='auto',origin='lower')
        ax.set_xticks(range(ns)); ax.set_xticklabels(sl,fontsize=7)
        ax.set_yticks(range(nd)); ax.set_yticklabels(dl,fontsize=8)
        ax.set_xlabel("Sparsity S (fraction missing)",fontsize=10)
        ax.set_ylabel("Difficulty Gap D",fontsize=10)
        ax.set_title(title,fontsize=11,fontweight='bold')
        for di in range(nd):
            for si in range(ns):
                v=g[di,si]
                if not np.isnan(v):
                    mid=(vn+vx)/2
                    c='white' if (cm==cmap_delta and v>mid) or (cm!=cmap_delta and v<mid) else 'black'
                    ax.text(si,di,f"{v:.2f}",ha='center',va='center',fontsize=5,color=c)
        plt.colorbar(im,ax=ax,shrink=0.8,label=lb)

    plt.suptitle(f"Evaluation Failure Surface: Grid Sweep Over Sparsity × Difficulty Gap\n"
                 f"({N_SEEDS} seeds/cell, J={J} systems, I={I} items, K={K} trials)",
                 fontsize=13,fontweight='bold',y=1.01)
    plt.tight_layout()
    plt.savefig(f"{OUT}/figure2_composite_annotated.png",dpi=300,bbox_inches='tight')
    plt.close(); print("Saved figure2_composite_annotated.png")

    # Clean version (no cell numbers) for paper
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    for ax,(g,title,cm,vn,vx,lb) in zip(axes.flat,panels):
        im=ax.imshow(g,cmap=cm,vmin=vn,vmax=vx,aspect='auto',origin='lower')
        ax.set_xticks(range(ns)); ax.set_xticklabels(sl,fontsize=7)
        ax.set_yticks(range(nd)); ax.set_yticklabels(dl,fontsize=8)
        ax.set_xlabel("Sparsity S (fraction missing)",fontsize=10)
        ax.set_ylabel("Difficulty Gap D",fontsize=10)
        ax.set_title(title,fontsize=11,fontweight='bold')
        plt.colorbar(im,ax=ax,shrink=0.8,label=lb)
    plt.suptitle(f"Evaluation Failure Surface: Grid Sweep Over Sparsity × Difficulty Gap\n"
                 f"({N_SEEDS} seeds/cell, J={J} systems, I={I} items, K={K} trials)",
                 fontsize=13,fontweight='bold',y=1.01)
    plt.tight_layout()
    plt.savefig(f"{OUT}/figure2_composite.png",dpi=300,bbox_inches='tight')
    plt.close(); print("Saved figure2_composite.png (clean)")

    # Scaling fit scatter
    fig,ax=plt.subplots(figsize=(8,5.5))
    sd_b,err_b,err_m=[],[],[]
    for r in summary:
        if r['SD']>0:
            sd_b.append(r['SD']); err_b.append(1-r['rho_avg_biased_mean'])
            err_m.append(1-r['rho_avg_mcar_mean'])
    sd_b=np.array(sd_b); err_b=np.array(err_b); err_m=np.array(err_m)
    ax.scatter(sd_b,err_b,c='#d32f2f',s=30,alpha=0.7,label='Biased missingness',zorder=5)
    ax.scatter(sd_b,err_m,c='#1565c0',s=20,alpha=0.5,marker='x',label='MCAR',zorder=4)
    # Power-law fit
    mask_p = err_b > 1e-4
    if mask_p.sum()>5:
        c=np.polyfit(np.log(sd_b[mask_p]),np.log(err_b[mask_p]),1)
        beta_pw=c[0]; alpha_pw=np.exp(c[1])
        xs=np.linspace(sd_b.min(),sd_b.max(),100)
        ax.plot(xs,alpha_pw*xs**beta_pw,'r--',alpha=0.7,
                label=f'Fit: {alpha_pw:.3f}·(S·D)^{beta_pw:.2f}')
        pred=alpha_pw*sd_b[mask_p]**beta_pw
        ss_r=np.sum((err_b[mask_p]-pred)**2); ss_t=np.sum((err_b[mask_p]-err_b[mask_p].mean())**2)
        r2_pw=1-ss_r/ss_t if ss_t>0 else 0
    else: alpha_pw=beta_pw=r2_pw=None
    ax.set_xlabel("S × D",fontsize=12); ax.set_ylabel("Ranking Error (1 − ρ)",fontsize=12)
    ax.set_title("Evaluation Failure Surface: S×D vs Ranking Error",fontsize=13,fontweight='bold')
    ax.legend(fontsize=9); ax.set_xlim(left=0); ax.set_ylim(bottom=-0.01); ax.grid(True,alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{OUT}/scaling_fit.png",dpi=300,bbox_inches='tight')
    plt.close(); print("Saved scaling_fit.png")

    # ── REGRESSION ──
    rep = []
    rep.append("="*60)
    rep.append("STATISTICAL ANALYSIS: Evaluation Failure Surface")
    rep.append(f"Grid: {ns}×{nd}={ns*nd} cells, {N_SEEDS} seeds/cell")
    rep.append("="*60)

    S_arr=np.array([r['S'] for r in summary])
    D_arr=np.array([r['D'] for r in summary])
    err_avg=1-np.array([r['rho_avg_biased_mean'] for r in summary])
    err_mcar_arr=1-np.array([r['rho_avg_mcar_mean'] for r in summary])

    # Centered interaction regression on ERROR
    Sc=S_arr-S_arr.mean(); Dc=D_arr-D_arr.mean()
    X=np.column_stack([np.ones(len(Sc)),Sc,Dc,Sc*Dc])
    for label,y in [("BIASED",err_avg),("MCAR",err_mcar_arr)]:
        rep.append(f"\n--- {label}: error = γ0 + γ1·S_c + γ2·D_c + γ3·S_c·D_c ---")
        bh=np.linalg.lstsq(X,y,rcond=None)[0]
        pred=X@bh; res=y-pred
        ss_r=np.sum(res**2); ss_t=np.sum((y-y.mean())**2)
        r2=1-ss_r/ss_t if ss_t>0 else 0
        n=len(y); p=4; mse=ss_r/(n-p)
        try:
            se=np.sqrt(np.diag(mse*np.linalg.inv(X.T@X)))
            ts=bh/se
        except: se=ts=np.full(p,np.nan)
        for nm,b,s,t in zip(['γ0(intercept)','γ1(S_c)','γ2(D_c)','γ3(S_c×D_c)'],bh,se,ts):
            rep.append(f"  {nm:20s}: {b:+.5f} ± {s:.5f}  (t={t:+.2f})")
        rep.append(f"  R² = {r2:.4f}, n = {n}")
        if label=="BIASED":
            rep.append(f"  Interpretation: γ3 {'IS' if abs(ts[3])>2 else 'is NOT'} significant (|t|={abs(ts[3]):.1f})")

    # Power-law
    rep.append(f"\n--- POWER-LAW: error = α·(S·D)^β ---")
    if r2_pw is not None:
        rep.append(f"  α={alpha_pw:.4f}, β={beta_pw:.4f}, R²={r2_pw:.4f}")
        rep.append(f"  → {'Reasonable' if r2_pw>0.7 else 'Weak'} fit. "
                   f"{'Use scaling law.' if r2_pw>0.7 else 'Use failure surface phrasing.'}")
    
    # Key comparisons
    rep.append(f"\n--- KEY RESULTS ---")
    high_s = S_arr>=0.40
    if high_s.sum()>0:
        rep.append(f"At S≥0.40: mean error(biased)={np.mean(err_avg[high_s]):.3f}, "
                   f"mean error(MCAR)={np.mean(err_mcar_arr[high_s]):.3f}")
        rep.append(f"  → Biased missingness adds {np.mean(err_avg[high_s])-np.mean(err_mcar_arr[high_s]):.3f} extra error")
    rep.append(f"Worst case: error(biased)={np.max(err_avg):.3f}, error(MCAR)={np.max(err_mcar_arr):.3f}")
    irt_vals=[r['rho_irt_biased_mean'] for r in summary if r['rho_irt_biased_mean'] is not None]
    rep.append(f"IRT range: min ρ={min(irt_vals):.3f}, max ρ={max(irt_vals):.3f}")
    rep.append(f"IRT maintains ρ ≥ {min(irt_vals):.3f} across ALL {ns*nd} conditions")

    report = '\n'.join(rep)
    with open(f"{OUT}/regression_report.txt",'w') as f: f.write(report)
    print(f"\n{report}")

if __name__=="__main__":
    run()
    print("\n✅ Complete.")
