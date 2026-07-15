"""
DYNAMO -- can the frustrated Clockfield spin up its own gauge field?
===================================================================
The ultimate question of the U(1) thread. Mittari proved the Clockfield is
a GLOBAL-U(1) matter theory in a BACKGROUND connection: the flux that lifts
it GOE->GUE was imposed by hand. This asks whether the connection can be
DYNAMICAL -- whether the phase glass, started at exactly zero flux, will
generate its own Wilson-loop flux from its own frustration, and lift its
own spectrum, with nothing imposed.

===================== THE ACTION (one functional, everything derived) =====
Gauge-covariant XY matter + Maxwell cost on plaquette flux:

  E[th,A] = sum_edges A_g[i,j] (1 - cos(th_i - th_j - A_ij))        (matter)
          + (K/2) sum_tri (curl A)_tri^2                             (Maxwell)
          + (mu/2) sum_edges A_ij^2                                  (regulator)

  curl on a triangle (i,j,k):  F_ijk = A_ij + A_jk + A_ki   (lattice B-field,
  gauge invariant: invariant under th_i->th_i+chi_i, A_ij->A_ij+(chi_i-chi_j)
  because curl of a gradient is 0 -- this is Mittari's G3 made dynamical).

===================== EQUATIONS OF MOTION (gradient flow from E) ===========
Matter (Clockfield gamma-modulated, now COVARIANT in A):
  beta_i  = sum_j A_g[i,j] (th_i - th_j - A_ij)^2       covariant frustration
  gamma_i = 1/(1 + tau beta_i)^2
  th_ddot_i = gamma_i^2 sum_j A_g[i,j] sin(th_j - th_i + A_ij) - eta th_dot_i

Connection (Maxwell/Ampere -- the NEW physics):
  J_ij = A_g[i,j] sin(th_i - th_j - A_ij)      the U(1) matter current (source)
  (curlcurl A)_ij = sum_{tri containing edge ij} +/- F_tri   discrete d*dA
  A_dot_ij = J_ij - K (curlcurl A)_ij - mu A_ij + sqrt(2 T) xi   (+antisym)
  A_ij = -A_ji enforced every step (connection lives on oriented edges)

The current term is the dynamo: frustrated phases push on A; A pushes back
on the phases through the covariant coupling. Maxwell spreads/penalizes flux.

===================== REGISTERED PREDICTIONS (before any run) ==============
Setup: BirthOfClockfield Watts-Strogatz graph, N=400, tau=2.737. Equilibrate
the phases first (frozen A=0) so the glass is frustrated, THEN switch on A
dynamics from A=0 exactly. Sweep the Maxwell stiffness K (cheap flux vs dear
flux). Measure: total Wilson-flux magnitude Phi(t) = sum_tri |F_tri|; the
r-statistic of the covariant spectrum vs frozen-A GOE baseline; energy.

D1  ZERO IS A FIXED POINT ONLY IF UNSOURCED. With mu large / K large (dear
    flux) A stays ~0: Phi(inf)/Phi_scale < 0.05. Control that the integrator
    doesn't manufacture flux from nothing.
D2  THE DYNAMO (the real question). For some K in the swept range, starting
    from A=0, the frustration sources NONZERO steady flux:
    Phi(inf) > 10x its t=0 value AND stable (not a transient). 
    -> the connection is dynamical; the arrow is EMERGENT.
    KILL: Phi(inf) < 2x Phi(0) at every K -> flux always relaxes to zero;
    the connection is NOT dynamical; Rajapinta must impose it as a boundary
    condition. Clean negative, the honest headline stays "background gauge".
D3  SELF-LIFT. IF D2 fires, does the SELF-GENERATED flux lift the spectrum?
    r(dynamical A, steady state) >= GOE_cal + 0.3(GUE_cal - GOE_cal).
    This is the whole prize: GUE-ward motion with NOTHING imposed.
    (If D2 fails, D3 is void and reported as such.)
D4  GAUGE SANITY. Total flux Phi and energy E are gauge-invariant; a random
    local gauge kick th_i+=chi_i, A_ij+=(chi_i-chi_j) must leave both
    unchanged (< 1e-9). Guards that "flux" measures field, not gauge.

Interpretation locked in advance:
  D2 fires + D3 fires -> "the Clockfield is a DYNAMICAL U(1) gauge theory;
    the arrow is emergent" (drops Mittari's qualifier).
  D2 fails            -> "the connection is non-dynamical; flux is a
    boundary condition imposed by the Rajapinta" (Mittari's headline final).
  D2 fires + D3 fails -> flux self-generates but is spectrally inert; a
    partial, honestly weird result that gets its own autopsy.

Do not hype. Do not lie. Just show. And: this is still on the near side of
the RH cliff -- self-generated GUE statistics are still not primes (alkuluku).
"""
import numpy as np, json
import networkx as nx
from numpy.linalg import eigvalsh

TAU, DT = 2.737, 0.02

# ---------------------------------------------------------------- graph
def make(N=400, k=8, p=0.15, seed=1):
    G = nx.watts_strogatz_graph(N, k, p, seed=seed)
    A = nx.to_numpy_array(G)
    tris = [tuple(c) for c in nx.enumerate_all_cliques(G) if len(c) == 3]
    # edge->triangle incidence with orientation, for curl and curl-curl
    return G, A, tris

# ---------------------------------------------------------------- curl ops
def flux_per_triangle(Aconn, tris):
    """F_tri = A_ij + A_jk + A_ki (oriented)."""
    return np.array([Aconn[i, j] + Aconn[j, k] + Aconn[k, i] for i, j, k in tris])

_TRI_IDX = {}
def _tri_arrays(tris, N):
    key = (id(tris), N)
    if key not in _TRI_IDX:
        I = np.array([t[0] for t in tris]); J = np.array([t[1] for t in tris]); Kk = np.array([t[2] for t in tris])
        _TRI_IDX[key] = (I, J, Kk)
    return _TRI_IDX[key]

def flux_per_triangle_v(Aconn, tris, N):
    I,J,Kk=_tri_arrays(tris,N)
    return Aconn[I,J]+Aconn[J,Kk]+Aconn[Kk,I]

def curlcurl(Aconn, tris, N):
    """Vectorized co-boundary of the plaquette flux -> antisymmetric matrix."""
    I,J,Kk=_tri_arrays(tris,N)
    F=Aconn[I,J]+Aconn[J,Kk]+Aconn[Kk,I]
    out=np.zeros((N,N))
    np.add.at(out,(I,J),F); np.add.at(out,(J,Kk),F); np.add.at(out,(Kk,I),F)
    out=out-out.T
    return out

# ---------------------------------------------------------------- dynamics
def clock_phase_step(th, th_old, Aconn, Ag, eta):
    d = th[:, None] - th[None, :] - Aconn          # covariant difference
    dd = np.arctan2(np.sin(d), np.cos(d))
    beta = np.sum(Ag * dd**2, axis=1)
    gamma = 1.0 / (1.0 + TAU * beta + 1e-12)**2
    force = np.sum(Ag * np.sin(-dd), axis=1)        # sin(th_j-th_i+A_ij)
    v = (1.0 - eta * DT) * (th - th_old)
    new = th + v + DT**2 * (gamma**2) * force
    return np.mod(new, 2 * np.pi), th.copy()

def connection_step(Aconn, th, Ag, tris, N, K, mu, T, rng):
    d = th[:, None] - th[None, :] - Aconn
    J = Ag * np.sin(d)                              # matter current, antisym
    J = 0.5 * (J - J.T)
    cc = curlcurl(Aconn, tris, N)
    noise = 0.0
    if T > 0:
        w = rng.standard_normal((N, N)); w = (w - w.T) / np.sqrt(2)
        noise = np.sqrt(2 * T * DT) * w * (Ag != 0)
    dA = (J - K * cc - mu * Aconn) * (Ag != 0)
    Anew = Aconn + DT * dA + noise
    Anew = 0.5 * (Anew - Anew.T) * (Ag != 0)        # keep antisymmetric, on-edge
    return Anew

def spectrum_r(th, Aconn, Ag, trim=0.05):
    d = th[:, None] - th[None, :] - Aconn
    M = -Ag * np.cos(d) * np.exp(1j * Aconn)        # covariant hopping (Peierls)
    M = 0.5 * (M + M.conj().T)
    np.fill_diagonal(M, np.sum(Ag * np.cos(d), axis=1))
    ev = np.sort(eigvalsh(M).real); n = len(ev)
    ev = ev[int(trim * n):int((1 - trim) * n)]
    s = np.diff(ev); s = s[s > 1e-12]
    r = np.minimum(s[1:], s[:-1]) / np.maximum(s[1:], s[:-1])
    return float(r.mean())

def calibrate(N=400, n=10, seed0=555):
    rg, ru = [], []
    for m in range(n):
        rng = np.random.default_rng(seed0 + m)
        a = rng.standard_normal((N, N)); H = (a + a.T) / np.sqrt(2)
        e = np.sort(eigvalsh(H)); e = e[int(.05*N):int(.95*N)]
        s = np.diff(e); rg.append(float((np.minimum(s[1:],s[:-1])/np.maximum(s[1:],s[:-1])).mean()))
        b = rng.standard_normal((N,N))+1j*rng.standard_normal((N,N)); Hc=(b+b.conj().T)/2
        e = np.sort(eigvalsh(Hc)); e = e[int(.05*N):int(.95*N)]
        s = np.diff(e); ru.append(float((np.minimum(s[1:],s[:-1])/np.maximum(s[1:],s[:-1])).mean()))
    return float(np.mean(rg)), float(np.mean(ru))

def run(K, mu, N=400, seed=1, equil=1500, drive=4000, T=0.0):
    G, Ag, tris = make(N=N, seed=seed)
    rng = np.random.default_rng(100 + seed)
    th = rng.uniform(0, 2*np.pi, N); th_old = th.copy()
    # phase 1: frustrate the glass with A=0 frozen
    Az = np.zeros((N, N))
    for _ in range(equil):
        th, th_old = clock_phase_step(th, th_old, Az, Ag, eta=0.05)
    r_base = spectrum_r(th, Az, Ag)
    phi0 = float(np.abs(flux_per_triangle_v(Az, tris, N)).sum())
    # phase 2: switch on A from EXACTLY zero
    Aconn = np.zeros((N, N))
    phis = []
    for t in range(drive):
        th, th_old = clock_phase_step(th, th_old, Aconn, Ag, eta=0.05)
        Aconn = connection_step(Aconn, th, Ag, tris, N, K, mu, T, rng)
        if t % 50 == 0:
            phis.append(float(np.abs(flux_per_triangle_v(Aconn, tris, N)).sum()))
    phi_final = float(np.mean(phis[-10:]))
    phi_scale = len(tris) * np.pi                    # max possible |flux| sum
    r_dyn = spectrum_r(th, Aconn, Ag)
    return dict(K=K, mu=mu, r_base=round(r_base, 4), r_dyn=round(r_dyn, 4),
                phi0=round(phi0, 4), phi_final=round(phi_final, 3),
                phi_frac=round(phi_final / phi_scale, 4),
                phi_growth=round(phi_final / max(phi0, 1e-9), 1) if phi0 > 1e-9
                else (float('inf') if phi_final > 0.1 else 0.0),
                phi_trace=[round(p, 2) for p in phis[::4]], n_tris=len(tris))

def gauge_check(N=200, seed=3):
    G, Ag, tris = make(N=N, seed=seed)
    rng = np.random.default_rng(7)
    th = rng.uniform(0, 2*np.pi, N)
    Aconn = 0.3 * rng.standard_normal((N, N)); Aconn = (Aconn-Aconn.T)/np.sqrt(2); Aconn*=(Ag!=0)
    phi1 = np.abs(flux_per_triangle(Aconn, tris)).sum()
    chi = rng.standard_normal(N)
    th2 = np.mod(th + chi, 2*np.pi)
    A2 = Aconn + (chi[:,None]-chi[None,:])*(Ag!=0)
    phi2 = np.abs(flux_per_triangle(A2, tris)).sum()
    return float(abs(phi1 - phi2))

if __name__ == '__main__':
    print("calibrating estimator...")
    GOE, GUE = calibrate()
    thr = GOE + 0.3 * (GUE - GOE)
    print(f"GOE={GOE:.4f}  GUE={GUE:.4f}  lift-threshold={thr:.4f}")

    gc = gauge_check()
    print(f"D4 gauge invariance of flux: |dPhi|={gc:.2e}  pass={gc<1e-9}")

    # sweep Maxwell stiffness: cheap flux (small K,mu) -> dear flux (large)
    configs = [dict(K=0.02, mu=0.02), dict(K=0.1, mu=0.05),
               dict(K=0.5, mu=0.1), dict(K=2.0, mu=0.5)]
    results = []
    for cfg in configs:
        r = run(cfg['K'], cfg['mu'])
        results.append(r)
        print(f"K={cfg['K']:<5} mu={cfg['mu']:<5} | phi0={r['phi0']:.3f} "
              f"-> phi_final={r['phi_final']:.2f} (x{r['phi_growth']}, "
              f"frac={r['phi_frac']}) | r {r['r_base']} -> {r['r_dyn']}")

    max_growth = max(r['phi_growth'] for r in results)
    dynamo = [r for r in results if r['phi_growth'] >= 10 and r['phi_frac'] > 0.01]
    lift = [r for r in dynamo if r['r_dyn'] >= thr]
    verdict = dict(
        GOE_cal=round(GOE,4), GUE_cal=round(GUE,4), lift_threshold=round(thr,4),
        D2_dynamo_fires=bool(len(dynamo) > 0),
        D2_max_flux_growth=max_growth,
        D2_KILL=bool(all(r['phi_growth'] < 2 for r in results)),
        D3_self_lift=bool(len(lift) > 0),
        D3_best_r_dyn=max((r['r_dyn'] for r in results), default=None),
        D4_gauge_invariant=bool(gc < 1e-9),
        HEADLINE=("DYNAMICAL U(1): arrow emergent, self-lifts to GUE" if lift else
                  "DYNAMICAL FLUX but spectrally inert (autopsy)" if dynamo else
                  "NON-DYNAMICAL: flux relaxes to zero, Rajapinta must impose it"))
    print(json.dumps(verdict, indent=2))
    json.dump(dict(calibration=dict(GOE=GOE, GUE=GUE), runs=results, verdict=verdict),
              open('/home/claude/dynamo_results.json', 'w'), indent=1)
