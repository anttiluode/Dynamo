import sys, json, os, numpy as np
exec(open('experiments/dynamo.py').read().split('if __name__')[0])
K,mu = float(sys.argv[1]), float(sys.argv[2])
r = run(K, mu, N=400, equil=1200, drive=3000)
path='/home/claude/dynamo_runs.json'
runs = json.load(open(path)) if os.path.exists(path) else []
runs.append(r); json.dump(runs, open(path,'w'), indent=1)
print(f"K={K} mu={mu}: phi0={r['phi0']:.3f} -> {r['phi_final']:.2f} (x{r['phi_growth']}) frac={r['phi_frac']} | r {r['r_base']}->{r['r_dyn']}")
