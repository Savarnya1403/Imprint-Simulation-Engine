"""Vectorized per-agent belief networks for large cohorts.

The micrograd path (nn.MLP + Value graph) is exact and inspectable, but it
builds a Python object graph per agent per day — unusable at N=3000.
This module is the same 6 -> 4 (tanh) -> 1 (sigmoid) architecture with the
same MSE-to-peer belief update and temperature-scaled SGD, but batched in
NumPy. It is selected automatically above ~600 agents and is labelled in
the run provenance so the switch is never silent.

No claim is made that the two paths are numerically identical; they share
initialisation scale, architecture and update rule. Determinism comes from
the engine's seeded RNGs in both cases.
"""
from __future__ import annotations

import numpy as np


def _sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -60, 60)))


class BatchedMLP:
    """N independent 6-4-1 MLPs with batched forward / backward."""

    def __init__(self, n: int):
        n = max(1, int(n))
        # Matches nn.Neuron init scale: gauss(0,1)/sqrt(nin)
        self.W1 = np.random.randn(n, 6, 4) / np.sqrt(6)  # (N,6,4)
        self.b1 = np.zeros((n, 4))
        self.W2 = np.random.randn(n, 4, 1) / np.sqrt(4)  # (N,4,1)
        self.b2 = np.zeros((n, 1))
        self.n = n
        self._h = None
        self._out = None
        self._x = None

    def forward_batch(self, X: np.ndarray) -> np.ndarray:
        """X: (N,6) -> out: (N,) probabilities in (0,1). Caches for backward."""
        X = np.asarray(X, dtype=np.float64)
        self._x = X
        z1 = np.einsum("ni,nij->nj", X, self.W1) + self.b1  # (N,4)
        h = np.tanh(z1)
        z2 = np.einsum("nj,njk->nk", h, self.W2) + self.b2  # (N,1)
        out = _sigmoid(z2).squeeze(-1)  # (N,)
        self._h = h
        self._out = out
        return out

    def backward_and_step(self, X: np.ndarray, target: np.ndarray, lr: float):
        """One SGD step toward target (MSE loss), with temperature-scaled lr."""
        X = np.asarray(X, dtype=np.float64)
        target = np.asarray(target, dtype=np.float64).reshape(-1)
        # Forward (recompute so the step is correct even if X changed)
        z1 = np.einsum("ni,nij->nj", X, self.W1) + self.b1
        h = np.tanh(z1)
        z2 = np.einsum("nj,njk->nk", h, self.W2) + self.b2
        out = _sigmoid(z2).squeeze(-1)  # (N,)
        # Loss L_i = (out_i - target_i)^2, dL/dout = 2*(out-target)
        grad_out = (2.0 * (out - target)).reshape(-1, 1)  # (N,1)
        # Sigmoid derivative
        dz2 = grad_out * (out.reshape(-1, 1) * (1 - out.reshape(-1, 1)))  # (N,1)
        # dW2: h (N,4) x dz2 (N,1) -> (N,4,1)
        dW2 = h[:, :, None] * dz2[:, None, :]  # (N,4,1)
        db2 = dz2.copy()
        # Backprop to hidden
        dh = np.einsum("nj,njk->nk", dz2, self.W2.transpose(0, 2, 1))  # (N,4)
        dz1 = dh * (1 - h ** 2)  # tanh derivative
        # dW1: X (N,6) outer dz1 (N,4) -> (N,6,4)
        dW1 = X[:, :, None] * dz1[:, None, :]  # (N,6,4)
        db1 = dz1.copy()
        # SGD step (matches nn.sgd_update with lr = mlp_lr * temp)
        step = float(lr)
        self.W1 -= step * dW1
        self.b1 -= step * db1
        self.W2 -= step * dW2
        self.b2 -= step * db2
        # Cache for any inspection
        self._h, self._out, self._x = h, out, X
        return out


def belief_forward_backward(
    model: BatchedMLP,
    afford: np.ndarray,
    relative: np.ndarray,
    social: np.ndarray,
    trust: np.ndarray,
    risk: np.ndarray,
    status: np.ndarray,
    social_field_prev: np.ndarray,
    peer_rate: np.ndarray,
    lr: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Stacked (N,6) features, forward + learning step.

    Returns (p_pre, p_post) where p_pre is the belief before the step and
    p_post is after. The engine uses p_pre for the day's social field and
    appraisal, exactly as the micrograd path does.
    """
    X_pre = np.stack(
        [afford, relative, social_field_prev, trust, risk, status], axis=1
    ).astype(np.float64)
    p_pre = model.forward_batch(X_pre)
    X_post = np.stack(
        [afford, relative, social, trust, risk, status], axis=1
    ).astype(np.float64)
    p_post = model.backward_and_step(X_post, peer_rate, lr)
    return p_pre, p_post
