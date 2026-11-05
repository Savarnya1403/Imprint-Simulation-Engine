"""Tiny autograd engine + MLP, in the style of micrograd.

Every agent is a small neural network. Belief updating is backpropagation on
a cognitive-dissonance loss (belief vs observed peer behavior). No PyTorch,
no magic — pure NumPy, ~150 lines, fully differentiable.

This is the "neurological concept" made explicit: agents are small networks
that learn from their social environment.
"""
from __future__ import annotations

from typing import Callable, List


class Value:
    """A scalar node in a dynamic computation graph."""

    def __init__(self, data: float, _children: tuple = (), _op: str = "", label: str = ""):
        self.data = float(data)
        self.grad = 0.0
        self._backward: Callable[[], None] = lambda: None
        self._prev = set(_children)
        self._op = _op
        self.label = label

    def __repr__(self) -> str:
        return f"Value(data={self.data:.4f}, grad={self.grad:.4f})"

    def __add__(self, other: "Value") -> "Value":
        other = other if isinstance(other, Value) else Value(other)
        out = Value(self.data + other.data, (self, other), "+")

        def _backward():
            self.grad += out.grad
            other.grad += out.grad

        out._backward = _backward
        return out

    def __mul__(self, other: "Value") -> "Value":
        other = other if isinstance(other, Value) else Value(other)
        out = Value(self.data * other.data, (self, other), "*")

        def _backward():
            self.grad += other.data * out.grad
            other.grad += self.data * out.grad

        out._backward = _backward
        return out

    def __neg__(self) -> "Value":
        return self * -1

    def __sub__(self, other: "Value") -> "Value":
        return self + (-other)

    def __pow__(self, other: float) -> "Value":
        assert isinstance(other, (int, float)), "only int/float powers supported"
        out = Value(self.data ** other, (self,), f"**{other}")

        def _backward():
            self.grad += other * (self.data ** (other - 1)) * out.grad

        out._backward = _backward
        return out

    def relu(self) -> "Value":
        out = Value(0 if self.data < 0 else self.data, (self,), "ReLU")

        def _backward():
            self.grad += (out.data > 0) * out.grad

        out._backward = _backward
        return out

    def sigmoid(self) -> "Value":
        x = self.data
        out = Value(1.0 / (1.0 + math.exp(-x)), (self,), "sigmoid")

        def _backward():
            self.grad += (1 - out.data) * out.data * out.grad

        out._backward = _backward
        return out

    def tanh(self) -> "Value":
        x = self.data
        t = math.tanh(x)
        out = Value(t, (self,), "tanh")

        def _backward():
            self.grad += (1 - t ** 2) * out.grad

        out._backward = _backward
        return out

    def backward(self) -> None:
        topo: List[Value] = []
        visited: set = set()

        def build(v: "Value") -> None:
            if v not in visited:
                visited.add(v)
                for child in v._prev:
                    build(child)
                topo.append(v)

        build(self)
        self.grad = 1.0
        for node in reversed(topo):
            node._backward()


import math  # noqa: E402


class Neuron:
    """A single neuron: y = activation(w·x + b)."""

    def __init__(self, nin: int, nonlinearity: str = "tanh"):
        self.w = [Value(__import__("random").gauss(0, 1) / (nin ** 0.5)) for _ in range(nin)]
        self.b = Value(0.0)
        self.nonlinearity = nonlinearity

    def __call__(self, x: List[Value]) -> Value:
        act = sum((wi * xi for wi, xi in zip(self.w, x)), Value(0.0)) + self.b
        if self.nonlinearity == "relu":
            return act.relu()
        if self.nonlinearity == "sigmoid":
            return act.sigmoid()
        return act.tanh()

    def parameters(self) -> List[Value]:
        return self.w + [self.b]


class Layer:
    """A layer of neurons."""

    def __init__(self, nin: int, nout: int, nonlinearity: str = "tanh"):
        self.neurons = [Neuron(nin, nonlinearity) for _ in range(nout)]

    def __call__(self, x: List[Value]) -> List[Value]:
        return [n(x) for n in self.neurons]

    def parameters(self) -> List[Value]:
        return [p for n in self.neurons for p in n.parameters()]


class MLP:
    """Multi-layer perceptron: maps context vector -> adoption logit."""

    def __init__(self, nin: int, nouts: List[int]):
        sizes = [nin] + nouts
        self.layers = [
            Layer(sizes[i], sizes[i + 1], nonlinearity="tanh" if i < len(sizes) - 2 else "sigmoid")
            for i in range(len(sizes) - 1)
        ]

    def __call__(self, x: List[Value]) -> Value:
        for layer in self.layers:
            x = layer(x)
        return x[0]

    def parameters(self) -> List[Value]:
        return [p for layer in self.layers for p in layer.parameters()]

    def zero_grad(self) -> None:
        for p in self.parameters():
            p.grad = 0.0


def sgd_update(params: List[Value], lr: float) -> None:
    for p in params:
        p.data -= lr * p.grad
        p.grad = 0.0


__all__ = ["Value", "Neuron", "Layer", "MLP", "sgd_update"]
