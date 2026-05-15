
# ── FSM de Pedido ───────────────────────────────────────────────────────

# Definición de estados, transiciones y validaciones para el ciclo de vida de un pedido.
# Es un modelo que define qué estados puede tener algo y a qué estados puede pasar

# ────────────────────────────────────────────────────────────────────────

TRANSICIONES_PEDIDO = {
    "PENDIENTE": ["CONFIRMADO", "CANCELADO"],

    "CONFIRMADO": ["EN_PREP", "CANCELADO"],

    "EN_PREP": ["EN_CAMINO", "CANCELADO"],

    "EN_CAMINO": ["ENTREGADO"],

    "ENTREGADO": [],

    "CANCELADO": [],
}