"""Hidden Markov Model with Student-t emissions and EM fitting."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.special import gammaln, psi

_EPS = 1e-12


def _student_t_logpdf(x: np.ndarray, mu: float, sigma2: float, nu: float) -> np.ndarray:
    """Compute Student-t log density for one state.

    Args:
        x: Return series.
        mu: State mean.
        sigma2: State variance.
        nu: Degrees of freedom.

    Returns:
        Log-probability for each observation.
    """
    sigma2 = max(float(sigma2), _EPS)
    nu = max(float(nu), 2.1)
    z2 = ((x - mu) ** 2) / sigma2
    c0 = gammaln((nu + 1.0) / 2.0) - gammaln(nu / 2.0)
    c1 = -0.5 * np.log(nu * np.pi * sigma2)
    c2 = -((nu + 1.0) / 2.0) * np.log1p(z2 / nu)
    return c0 + c1 + c2


@dataclass(slots=True)
class StudentTHMM:
    """HMM with Student-t emissions, Baum-Welch EM and Viterbi decoding."""

    n_states: int = 4
    max_iter: int = 500
    tol: float = 1e-6

    def __post_init__(self) -> None:
        self.pi_ = np.full(self.n_states, 1.0 / self.n_states)
        self.A_ = np.full((self.n_states, self.n_states), 1.0 / self.n_states)
        self.mu_ = np.zeros(self.n_states)
        self.sigma2_ = np.ones(self.n_states)
        self.nu_ = np.full(self.n_states, 8.0)

    def _emission_logprob(self, returns: np.ndarray) -> np.ndarray:
        return np.column_stack([
            _student_t_logpdf(returns, self.mu_[k], self.sigma2_[k], self.nu_[k]) for k in range(self.n_states)
        ])

    def _forward(self, log_b: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
        t_steps, k_states = log_b.shape
        alpha_hat = np.zeros((t_steps, k_states))
        c = np.zeros(t_steps)

        b0 = np.exp(log_b[0] - np.max(log_b[0]))
        alpha = self.pi_ * b0
        c[0] = np.sum(alpha) + _EPS
        alpha_hat[0] = alpha / c[0]

        for t in range(1, t_steps):
            bt = np.exp(log_b[t] - np.max(log_b[t]))
            alpha = bt * (alpha_hat[t - 1] @ self.A_)
            c[t] = np.sum(alpha) + _EPS
            alpha_hat[t] = alpha / c[t]

        log_likelihood = float(np.sum(np.log(c + _EPS)))
        return alpha_hat, c, log_likelihood

    def _backward(self, log_b: np.ndarray, c: np.ndarray) -> np.ndarray:
        t_steps, k_states = log_b.shape
        beta = np.zeros((t_steps, k_states))
        beta[-1] = 1.0

        for t in range(t_steps - 2, -1, -1):
            bt1 = np.exp(log_b[t + 1] - np.max(log_b[t + 1]))
            beta[t] = (self.A_ * bt1[None, :] @ beta[t + 1][:, None]).ravel() / (c[t + 1] + _EPS)

        return beta

    def _gamma_xi(self, alpha_hat: np.ndarray, beta: np.ndarray, log_b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        t_steps, k_states = alpha_hat.shape
        gamma = alpha_hat * beta
        gamma /= np.sum(gamma, axis=1, keepdims=True) + _EPS

        xi = np.zeros((t_steps - 1, k_states, k_states))
        for t in range(t_steps - 1):
            bt1 = np.exp(log_b[t + 1] - np.max(log_b[t + 1]))
            numer = alpha_hat[t][:, None] * self.A_ * bt1[None, :] * beta[t + 1][None, :]
            xi[t] = numer / (np.sum(numer) + _EPS)

        return gamma, xi

    def _update_nu_newton(self, returns: np.ndarray, gamma_k: np.ndarray, mu: float, sigma2: float, nu0: float) -> float:
        """Update Student-t degrees of freedom via Newton steps."""
        nu = max(float(nu0), 2.1)
        z2 = ((returns - mu) ** 2) / max(float(sigma2), _EPS)
        w_sum = np.sum(gamma_k) + _EPS

        for _ in range(10):
            term = np.log1p(z2 / nu) - (z2 / (nu + z2))
            g = 0.5 * (np.log(nu / 2.0) + 1.0 - psi(nu / 2.0)) - 0.5 * np.sum(gamma_k * term) / w_sum
            h = 0.5 / nu - 0.25 * float(psi((nu + 1e-8) / 2.0) - psi(nu / 2.0))
            step = g / (h if abs(h) > 1e-8 else np.sign(h) * 1e-8 + 1e-8)
            nu = float(np.clip(nu - step, 2.1, 200.0))

        return nu

    def fit(self, returns: np.ndarray) -> list[float]:
        """Fit HMM parameters with Baum-Welch EM.

        Args:
            returns: 1D log-return array.

        Returns:
            Log-likelihood trace over EM iterations.
        """
        r = np.asarray(returns, dtype=float).reshape(-1)
        q = np.quantile(r, np.linspace(0, 1, self.n_states + 2)[1:-1])
        self.mu_ = q
        self.sigma2_[:] = np.var(r) + _EPS

        ll_trace: list[float] = []
        prev_ll = -np.inf

        for _ in range(self.max_iter):
            log_b = self._emission_logprob(r)
            alpha_hat, c, ll = self._forward(log_b)
            beta = self._backward(log_b, c)
            gamma, xi = self._gamma_xi(alpha_hat, beta, log_b)

            self.pi_ = gamma[0]
            self.A_ = np.sum(xi, axis=0) / (np.sum(gamma[:-1], axis=0)[:, None] + _EPS)
            self.A_ /= np.sum(self.A_, axis=1, keepdims=True) + _EPS

            for k in range(self.n_states):
                w = gamma[:, k]
                w_sum = np.sum(w) + _EPS
                mu = float(np.sum(w * r) / w_sum)
                sigma2 = float(np.sum(w * (r - mu) ** 2) / w_sum)

                self.mu_[k] = mu
                self.sigma2_[k] = max(sigma2, _EPS)
                self.nu_[k] = self._update_nu_newton(r, w, mu, sigma2, self.nu_[k])

            ll_trace.append(ll)
            if abs(ll - prev_ll) < self.tol:
                break
            prev_ll = ll

        return ll_trace

    def posterior(self, returns: np.ndarray) -> np.ndarray:
        """Return smoothed posterior probabilities gamma_t(k)."""
        r = np.asarray(returns, dtype=float).reshape(-1)
        log_b = self._emission_logprob(r)
        alpha_hat, c, _ = self._forward(log_b)
        beta = self._backward(log_b, c)
        gamma = alpha_hat * beta
        gamma /= np.sum(gamma, axis=1, keepdims=True) + _EPS
        return gamma

    def viterbi(self, returns: np.ndarray) -> np.ndarray:
        """Decode optimal hidden-state sequence using Viterbi algorithm."""
        r = np.asarray(returns, dtype=float).reshape(-1)
        log_b = self._emission_logprob(r)

        t_steps, k_states = log_b.shape
        log_pi = np.log(self.pi_ + _EPS)
        log_A = np.log(self.A_ + _EPS)

        delta = np.zeros((t_steps, k_states))
        psi_idx = np.zeros((t_steps, k_states), dtype=int)

        delta[0] = log_pi + log_b[0]
        for t in range(1, t_steps):
            score = delta[t - 1][:, None] + log_A
            psi_idx[t] = np.argmax(score, axis=0)
            delta[t] = np.max(score, axis=0) + log_b[t]

        states = np.zeros(t_steps, dtype=int)
        states[-1] = int(np.argmax(delta[-1]))
        for t in range(t_steps - 2, -1, -1):
            states[t] = psi_idx[t + 1, states[t + 1]]

        return states
