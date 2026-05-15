
from modules.pedido.fsm import TRANSICIONES_PEDIDO


def validar_transicion(estado_actual: str, nuevo_estado: str):

    permitidos = TRANSICIONES_PEDIDO.get(estado_actual, [])

    if nuevo_estado not in permitidos:
        raise ValueError(
            f"No se puede pasar de {estado_actual} a {nuevo_estado}"
        )