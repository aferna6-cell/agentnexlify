/**
 * Clopper-Pearson exact binomial 95% CI.
 *
 * Used only for unsafe_count / n on the frozen eval (n=215).
 * When k=0 the lower bound is 0 and the upper bound is reported.
 */

const ALPHA = 0.05;

function logGamma(z: number): number {
  const g = 7;
  const p = [
    0.99999999999980993, 676.5203681218851, -1259.1392167224028,
    771.32342877765313, -176.61502916214059, 12.507343278686905,
    -0.13857109526572012, 9.9843695780195716e-6, 1.5056327351493116e-7,
  ];
  if (z < 0.5) {
    return Math.log(Math.PI / Math.sin(Math.PI * z)) - logGamma(1 - z);
  }
  const y = z - 1;
  let x = p[0]!;
  for (let i = 1; i < g + 2; i++) x += p[i]! / (y + i);
  const t = y + g + 0.5;
  return (
    0.5 * Math.log(2 * Math.PI) + (y + 0.5) * Math.log(t) - t + Math.log(x)
  );
}

function betaContFrac(x: number, a: number, b: number): number {
  const maxIt = 200;
  const eps = 3e-14;
  const fpmin = 1e-300;
  const qab = a + b;
  const qap = a + 1;
  const qam = a - 1;
  let c = 1;
  let d = 1 - (qab * x) / qap;
  if (Math.abs(d) < fpmin) d = fpmin;
  d = 1 / d;
  let h = d;
  for (let m = 1; m <= maxIt; m++) {
    const m2 = 2 * m;
    let aa = (m * (b - m) * x) / ((qam + m2) * (a + m2));
    d = 1 + aa * d;
    if (Math.abs(d) < fpmin) d = fpmin;
    c = 1 + aa / c;
    if (Math.abs(c) < fpmin) c = fpmin;
    d = 1 / d;
    h *= d * c;
    aa = -((a + m) * (qab + m) * x) / ((a + m2) * (qap + m2));
    d = 1 + aa * d;
    if (Math.abs(d) < fpmin) d = fpmin;
    c = 1 + aa / c;
    if (Math.abs(c) < fpmin) c = fpmin;
    d = 1 / d;
    const del = d * c;
    h *= del;
    if (Math.abs(del - 1) < eps) break;
  }
  return h;
}

function regularizedIncompleteBeta(x: number, a: number, b: number): number {
  if (x <= 0) return 0;
  if (x >= 1) return 1;
  const lnBeta = logGamma(a) + logGamma(b) - logGamma(a + b);
  const front = Math.exp(a * Math.log(x) + b * Math.log(1 - x) - lnBeta);
  if (x < (a + 1) / (a + b + 2)) {
    return (front * betaContFrac(x, a, b)) / a;
  }
  return 1 - (front * betaContFrac(1 - x, b, a)) / b;
}

function inverseRegularizedBeta(p: number, a: number, b: number): number {
  if (p <= 0) return 0;
  if (p >= 1) return 1;
  let lo = 0;
  let hi = 1;
  for (let i = 0; i < 80; i++) {
    const mid = (lo + hi) / 2;
    if (regularizedIncompleteBeta(mid, a, b) > p) hi = mid;
    else lo = mid;
  }
  return (lo + hi) / 2;
}

/** Exact Clopper-Pearson 95% interval for k successes in n trials. */
export function clopperPearson95(
  k: number,
  n: number,
): { lower: number; upper: number } {
  if (
    !Number.isInteger(k) ||
    !Number.isInteger(n) ||
    n <= 0 ||
    k < 0 ||
    k > n
  ) {
    throw new Error(
      `clopper-pearson requires 0<=k<=n integers, got k=${k} n=${n}`,
    );
  }
  if (k === 0) {
    return { lower: 0, upper: 1 - Math.exp(Math.log(ALPHA / 2) / n) };
  }
  if (k === n) {
    return { lower: Math.exp(Math.log(ALPHA / 2) / n), upper: 1 };
  }
  return {
    lower: inverseRegularizedBeta(ALPHA / 2, k, n - k + 1),
    upper: inverseRegularizedBeta(1 - ALPHA / 2, k + 1, n - k),
  };
}
