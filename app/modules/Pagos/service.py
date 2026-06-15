# app/modules/payments/service.py — Lógica de integración con MercadoPago
#
# CONCEPTOS CLAVE DE MERCADOPAGO:
#
# - Preference: es lo que se crea ANTES de que el usuario pague. Representa
#   "la intención de cobro". Tiene items, montos, URLs de retorno, etc.
#   MP devuelve un preference_id y un init_point (URL del checkout).
#
# - Payment: es el pago REAL que el usuario hace. Tiene su propio ID
#   (mp_payment_id) y un status que indica si se aprobó, rechazó, etc.
#
# - Merchant Order: agrupa uno o más payments. Si el usuario intenta pagar
#   varias veces, cada intento es un payment diferente dentro de la misma orden.
#
# - Webhook: MP nos notifica cuando algo cambia (un pago se aprueba, etc.).
#   Puede llegar con topic=payment o topic=merchant_order. El webhook NO trae
#   todos los datos del pago — solo el ID y el topic. Por eso tenemos que
#   hacer una consulta adicional con SDK.payment().get(id).
#
# - Idempotency Key: UUID único por intento de pago. Si el frontend reenvía
#   la misma solicitud (por timeout o doble click), la constraint UNIQUE en
#   la BD evita que se duplique el registro.
#
# MAPEO DE ESTADOS (MP -> nuestro sistema):
#   MP "approved"              → "aprobado"
#   MP "rejected"              → "rechazado"
#   MP "cancelled"             → "rechazado"
#   MP "refunded"              → "rechazado"
#   MP "charged_back"          → "rechazado"
#   MP "pending"               → "pendiente"
#   MP "in_process"            → "pendiente"
#   MP "authorized"            → "pendiente"
#   cualquier otro             → se ignora
#
import uuid
import logging
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlmodel import Session

from app.Core.config import settings
from app.modules.Pedido.model import Pedido
from app.modules.Pagos.models import Pago
from app.modules.Pagos.schemas import PagoCrearResponse, PagoEstadoResponse
from app.modules.Pagos.unit_of_work import PagoUnitOfWork

logger = logging.getLogger(__name__)


class PaymentService:
    """
    Servicio que orquesta toda la integración con MercadoPago.

    Responsabilidades:
      1. Crear preferencias de pago en MP (etapa pre-checkout)
      2. Procesar notificaciones webhook de MP (etapa post-pago)
      3. Confirmar/consultar el estado de pagos manualmente
      4. Mantener sincronizados nuestros registros locales con MP
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    # ╔════════════════════════════════════════════════════════════════════╗
    # ║  MÉTODOS PRIVADOS: COMUNICACIÓN CON EL SDK DE MERCADOPAGO          ║
    # ╚════════════════════════════════════════════════════════════════════╝

    def _get_mp_access_token(self) -> Optional[str]:
        """
        Retorna el Access Token de MP desde la configuración.
        Este token es SECRETO — identifica nuestra cuenta de MP.
        Se configura via .env como MP_ACCESS_TOKEN.
        """
        return settings.MP_ACCESS_TOKEN

    def _get_mp_public_key(self) -> Optional[str]:
        """
        Retorna la Public Key de MP desde la configuración.
        Esta clave es PÚBLICA — se envía al frontend para que
        el SDK de MercadoPago en el navegador pueda inicializarse.
        Se configura via .env como MP_PUBLIC_KEY.
        """
        return settings.MP_PUBLIC_KEY

    def _crear_preferencia_mp(self, monto: float, titulo: str,
                               pedido_id: int, back_urls: dict) -> dict:
        """
        Crea una preferencia de pago en MercadoPago.

        ¿Qué es una preferencia?
        Es el "checkout" que ve el usuario. MP necesita saber:
          - qué se cobra (items, montos)
          - a dónde redirigir después del pago (back_urls)
          - a dónde notificar cambios (notification_url / webhook)
          - una referencia externa para identificar el pedido (external_reference)

        Args:
            monto:     Total del pedido en ARS
            titulo:    Texto que se muestra en el checkout de MP
            pedido_id: ID de nuestro pedido (se pasa como external_reference)
            back_urls: URLs a donde redirige MP después del pago

        Returns:
            dict con preference_id e init_point

        Raises:
            RuntimeError: si MP no está configurado o hay error de conexión
        """
        access_token = self._get_mp_access_token()
        if not access_token:
            raise RuntimeError(
                "MercadoPago no está configurado. Configure MP_ACCESS_TOKEN"
            )

        try:
            # El SDK de mercadopago se importa AQUÍ (no al tope del archivo)
            # para que la aplicación pueda arrancar aunque no esté instalado.
            # Si no está, el error es claro: "pip install mercadopago".
            import mercadopago
            sdk = mercadopago.SDK(access_token)

            # ── Construcción del payload de la preferencia ──────────────
            preference_data = {
                "items": [{
                    "title": titulo,
                    "quantity": 1,
                    # En este caso la orden es un solo ítem genérico.
                    # Podríamos enviar los ítems reales del pedido si quisieramos
                    # mostrar el detalle en el checkout de MP.
                    "unit_price": float(monto),
                    "currency_id": "ARS",  # Moneda: pesos argentinos
                }],
                "external_reference": str(pedido_id),
                # external_reference: MP devuelve esto en el webhook.
                # Nos permite identificar qué pedido nuestro corresponde al pago.
                "back_urls": back_urls,
                # back_urls: Cuando el usuario termina en MP, lo redirige a:
                #   success → pago aprobado
                #   failure → pago rechazado
                #   pending → pago pendiente (ej: transferencia)
                "notification_url": (
                    # URL donde MP notifica cambios de estado (webhook).
                    # Si no hay MP_WEBHOOK_URL configurado, usa la URL local.
                    # En producción debería ser una URL pública (ej: con ngrok).
                    settings.MP_WEBHOOK_URL
                    or f"{settings.VITE_API_URL}/api/v1/pagos/webhook"
                ),
                "auto_return": "approved",
                # auto_return: si el pago se aprueba, MP redirige automáticamente
                # al usuario de vuelta a nuestra back_urls.success sin esperar.
            }

            # ── Llamada a la API de MP ──────────────────────────────────
            result = sdk.preference().create(preference_data)

            # MP devuelve status 200 o 201 si todo salió bien
            if result.get("status") not in (200, 201):
                logger.error("Error creando preferencia MP: %s", result)
                raise RuntimeError(
                    "Error al crear preferencia: "
                    f"{result.get('response', {}).get('message', 'desconocido')}"
                )

            # Extraemos los datos que nos interesa devolver
            response = result.get("response", {})
            return {
                "preference_id": response.get("id"),
                # ID de la preferencia en MP — lo guardamos en BD para tracking
                "init_point": response.get("init_point"),
                # URL del checkout de MP — el frontend la usa para redirigir
            }

        except ImportError:
            raise RuntimeError("pip install mercadopago")
        except Exception as e:
            logger.exception("Error inesperado al crear preferencia MP")
            raise RuntimeError(f"Error de conexión con MP: {str(e)}")

    def _consultar_pago_mp(self, payment_id: int) -> dict:
        """
        Consulta el estado de un pago REAL en MercadoPago usando su payment_id.

        A diferencia de la preferencia (que es la "intención de cobro"),
        el payment_id identifica el pago concreto que el usuario hizo (o intentó hacer).
        MP devuelve el estado actual del pago: approved, rejected, pending, etc.

        Este método se llama desde:
          - procesar_webhook(): cuando MP nos notifica un cambio
          - confirmar_pago():   cuando el frontend consulta manualmente

        Args:
            payment_id: ID del pago en MP (viene en el webhook o lo pasa el frontend)

        Returns:
            dict con mp_payment_id, mp_status, mp_status_detail, mp_merchant_order_id

        Raises:
            RuntimeError: si MP no está configurado o hay error de conexión
        """
        access_token = self._get_mp_access_token()
        if not access_token:
            raise RuntimeError("MP no configurado")

        try:
            import mercadopago
            sdk = mercadopago.SDK(access_token)
            result = sdk.payment().get(payment_id)

            if result.get("status") != 200:
                logger.error("Error consultando pago MP %s: %s", payment_id, result)
                raise RuntimeError(f"Error al consultar pago {payment_id}")

            response = result.get("response", {})
            return {
                "mp_payment_id":        response.get("id"),
                "mp_status":            response.get("status"),
                # status: approved | rejected | pending | in_process | ...
                "mp_status_detail":     response.get("status_detail"),
                # status_detail: accredited | pending_waiting_payment | ...
                # Nos da más granularidad sobre POR QUÉ está en ese estado.
                "mp_merchant_order_id": response.get("merchant_order_id"),
                # merchant_order_id: permite agrupar pagos relacionados.
                # Si el usuario paga, se rechaza y vuelve a pagar,
                # todos los intentos comparten el mismo merchant_order_id.
            }

        except ImportError:
            raise RuntimeError("pip install mercadopago")
        except Exception as e:
            logger.exception("Error consultando pago MP %s", payment_id)
            raise RuntimeError(f"Error de conexión con MP: {str(e)}")

    # ╔════════════════════════════════════════════════════════════════════╗
    # ║  OPERACIONES DE NEGOCIO                                            ║
    # ╚════════════════════════════════════════════════════════════════════╝

    def crear_pago(self, pedido_id: int) -> PagoCrearResponse:
        """
        PASO 1 DEL FLUJO: Crear una preferencia de pago en MP.

        Este método:
          1. Verifica que el pedido existe en nuestra BD
          2. Verifica que MP está configurado (hay MP_ACCESS_TOKEN)
          3. Arma las URLs de retorno (back_urls) para después del pago
          4. Llama al SDK de MP para crear la preferencia
          5. Guarda el intento de pago en nuestra BD con estado "pendiente"
          6. Devuelve al frontend los datos necesarios para el checkout

        El frontend recibe:
          - preference_id: para tracking
          - init_point:    URL del checkout de MP
          - public_key:    clave pública de MP (para inicializar el SDK frontend)
        """
        # ── Validación del pedido ────────────────────────────────────────
        pedido = self._session.get(Pedido, pedido_id)
        if not pedido:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pedido no encontrado",
            )

        # ── Validación de configuración de MP ────────────────────────────
        if not self._get_mp_access_token():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MercadoPago no configurado. Configure MP_ACCESS_TOKEN",
            )

        # ── Construcción de back_urls ────────────────────────────────────
        # Después del pago en MP, el usuario es redirigido a estas URLs.
        # Usamos ngrok_url si está configurado (para desarrollo con túneles).
        ngrok_url = settings.NGROK_URL or "http://localhost:8000"
        back_urls = {
            "success": f"{ngrok_url}/api/v1/pagos/redirect/{pedido_id}/success",
            "failure": f"{ngrok_url}/api/v1/pagos/redirect/{pedido_id}/failure",
            "pending": f"{ngrok_url}/api/v1/pagos/redirect/{pedido_id}/pending",
        }

        # ── Creación de la preferencia en MP ────────────────────────────
        try:
            mp_data = self._crear_preferencia_mp(
                monto=pedido.total,
                titulo=f"Pedido #{pedido_id} - FoodStore",
                pedido_id=pedido_id,
                back_urls=back_urls,
            )
        except RuntimeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

        # ── Persistencia local del intento de pago ──────────────────────
        with PagoUnitOfWork(self._session) as uow:
            pago = Pago(
                pedido_id=pedido_id,
                monto=pedido.total,
                estado="pendiente",              # arranca pendiente
                mp_preference_id=mp_data["preference_id"],
                mp_init_point=mp_data.get("init_point"),
                idempotency_key=str(uuid.uuid4()),  # UUID único para idempotencia
            )
            uow.pagos.add(pago)

            # ── Respuesta al frontend ───────────────────────────────────
            return PagoCrearResponse(
                pago_id=pago.id,                     # ID de nuestro pago local
                preference_id=mp_data["preference_id"],  # ID de la preferencia en MP
                init_point=mp_data.get("init_point"),     # URL del checkout de MP
                public_key=self._get_mp_public_key(),     # Public Key para el SDK frontend
            )

    def procesar_webhook(self, data: dict,
                         query_params: Optional[dict] = None) -> dict:
        """
        PASO 5 DEL FLUJO: Procesar notificaciones webhook de MercadoPago.

        MP nos envía una notificación POST cuando el estado de un pago cambia.
        El webhook puede llegar de DOS formas:

        A) Con topic="payment":
           {
             "action": "payment.created",
             "data": { "id": "123456789" },
             "type": "payment"
           }
           El data.id es el mp_payment_id.

        B) Con topic="merchant_order" (menos común):
           {
             "topic": "merchant_order",
             "id": "987654321"
           }
           El id es el merchant_order_id (no payment_id).

        En AMBOS casos, el webhook NO trae el estado del pago.
        Solo trae un ID. Tenemos que llamar a _consultar_pago_mp() para
        obtener el estado actual.

        Este método:
          1. Extrae el payment_id o merchant_order_id del payload
          2. Ignora topics que no sean "payment" o "merchant_order"
          3. Consulta el estado real del pago a MP con SDK.payment().get()
          4. Mapea el estado de MP a nuestro estado local
          5. Actualiza el registro de pago en nuestra BD
          6. Si el pago se aprobó, actualiza el pedido a "pagado"
          7. Retorna un resumen de lo procesado

        Idempotencia: si el webhook llega más de una vez (MP puede reenviar),
        el método detecta que el pago ya no está "pendiente" y lo ignora.
        """
        logger.info("Webhook recibido: data=%s qs=%s", data, query_params or {})

        # ── Extracción de datos del webhook ──────────────────────────────
        # MP puede enviar el payload de diferentes formas según el topic.
        # Este bloque normaliza todas las variantes posibles.

        # Si el body está vacío pero hay query params, usamos esos
        if not data and query_params:
            data = query_params

        topic = data.get("type") or data.get("topic")
        data_id = data.get("data_id") or (data.get("data") or {}).get("id")
        payment_id = data.get("id")

        # Algunas versiones del webhook envían datos en query params
        if not data_id and query_params:
            data_id = query_params.get("data.id") or query_params.get("id")
        if not topic and query_params:
            topic = query_params.get("topic") or query_params.get("type")

        # El ID que usaremos para consultar a MP
        pago_mp_id = data_id


        # ── Validaciones ─────────────────────────────────────────────────
        if not pago_mp_id:
            return {"status": "ignored", "reason": "No payment ID"}

        # Solo procesamos payments y merchant_orders.
        # MP también envía webhooks de otros topics (ej: test, plan, etc.)
        # que no nos interesan.
        if topic not in (None, "payment", "merchant_order"):
            return {"status": "ignored", "reason": f"Topic: {topic}"}

        # ── Consulta a MP y actualización ───────────────────────────────
        try:
            # PASO 1: Consultar el estado real del pago a MP
            mp_info = self._consultar_pago_mp(int(pago_mp_id))
        

            estado_mp = mp_info.get("mp_status")
            print("Estado MP:", estado_mp)

            # PASO 2: Mapear estado de MP a nuestro estado local
            #
            # MP status → nuestro estado:
            #   "approved"       → "aprobado"  ✓ el pago fue exitoso
            #   "rejected"       → "rechazado"  ✗ MP rechazó (fondos, etc.)
            #   "cancelled"      → "rechazado"  ✗ el usuario canceló
            #   "refunded"       → "rechazado"  ✗ se devolvió el dinero
            #   "charged_back"   → "rechazado"  ✗ el comprador disputó
            #   "pending"        → "pendiente"  ⏳ esperando (ej: transferencia)
            #   "in_process"     → "pendiente"  ⏳ MP está revisando
            #   "authorized"     → "pendiente"  ⏳ autorizado pero no capturado
            #   otro             → ignorado     ? no sabemos qué hacer
            #
            if estado_mp == "approved":
                nuevo_estado = "aprobado"
            elif estado_mp in ("rejected", "cancelled",
                               "refunded", "charged_back"):
                nuevo_estado = "rechazado"
            elif estado_mp in ("pending", "in_process", "authorized"):
                nuevo_estado = "pendiente"
            else:
                
                return {"status": "ignored",
                        "reason": f"Unknown status: {estado_mp}"}

            # PASO 3: Buscar el pago en nuestra BD
            with PagoUnitOfWork(self._session) as uow:
                # Primero intentamos por mp_payment_id (el caso más común)
                pago = uow.pagos.get_by_mp_payment_id(int(pago_mp_id))

                # Si no lo encontramos, quizás el webhook llegó con un
                # merchant_order_id. Intentamos buscar por ese.
                if not pago and mp_info.get("mp_merchant_order_id"):
                    print("Buscando por merchant_order_id:", mp_info.get("mp_merchant_order_id")  )
                    pago = uow.pagos.get_by_mp_merchant_order_id(
                        mp_info["mp_merchant_order_id"]
                    )

                # Si aún no encontramos el pago, lo ignoramos.
                # Esto puede pasar si el webhook llega ANTES de que
                # hayamos creado el pago en nuestra BD (race condition).
                if not pago:
                    print("Pago no encontrado en BD para MP payment_id:", pago_mp_id       )
                    return {"status": "ignored",
                            "reason": "Pago not found in local DB"}
                print("Pago encontrado en BD:", pago    )

                # ── Idempotencia ─────────────────────────────────────────
                # Si el pago ya fue procesado (no está pendiente), ignoramos
                # la notificación. Esto evita procesar dos veces el mismo
                # webhook si MP reenvía la notificación.
                if pago.estado != "pendiente":
                    return {"status": "already_processed",
                            "estado": pago.estado}

                # PASO 4: Actualizar el registro de pago con los datos de MP
                pago.mp_payment_id = int(pago_mp_id)
                pago.mp_status = estado_mp
                pago.mp_status_detail = mp_info.get("mp_status_detail")
                pago.mp_merchant_order_id = mp_info.get("mp_merchant_order_id")
                pago.estado = nuevo_estado
                pago.updated_at = datetime.utcnow()
                uow.pagos.update(pago)

                print("Pago actualizado en BD:", pago   )

                # PASO 5: Si el pago se aprobó, actualizar el pedido
                #
                # Esto sincroniza el estado del pedido con el pago.
                # Es importante que esto esté DENTRO de la misma transacción
                # (UnitOfWork) para que si algo falla, todo se deshaga.
                if nuevo_estado == "aprobado":
                    pedido = self._session.get(Pedido, pago.pedido_id)
                    if pedido:
                        pedido.estado_codigo = "PENDIENTE"
                        pedido.updated_at = datetime.utcnow()
                        self._session.add(pedido)

            return {
                "status": "processed",
                "pago_id": pago.id,
                "estado": nuevo_estado,
                "pedido_id": pago.pedido_id,
            }

        except Exception as e:
            # Si hay CUALQUIER error procesando el webhook, lo logueamos
            # y devolvemos un 200 igual (MP espera un 200 para no reenviar).
            # Si devolviéramos 500, MP reintentaría el webhook.
            logger.exception("Error procesando webhook MP")
            return {"status": "error", "reason": str(e)}

    def confirmar_pago(self, pedido_id: int,
                       payment_id: Optional[int] = None) -> PagoEstadoResponse:
        """
        Consulta y sincroniza el estado de un pago manualmente.

        Este es el PASO 11 del flujo (opcional). El frontend puede llamar a
        este endpoint para "refrescar" el estado de un pago sin esperar el
        webhook. Es útil cuando:
          - El webhook tardó en llegar
          - El usuario vuelve a la página después de pagar en MP
          - Queremos verificar el estado antes de mostrar la confirmación

        Args:
            pedido_id:  ID de nuestro pedido
            payment_id: ID del pago en MP (opcional). Si no se pasa,
                       buscamos el último mp_payment_id asociado al pedido.

        Returns:
            PagoEstadoResponse con el estado actual y el pedido_id
        """
        # ── Validación del pedido ────────────────────────────────────────
        pedido = self._session.get(Pedido, pedido_id)
        if not pedido:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pedido no encontrado",
            )

        # ── Resolver el payment_id ───────────────────────────────────────
        # Si no nos pasaron un payment_id, buscamos el último pago local
        # y usamos su mp_payment_id (si tiene).
        resolved_payment_id = payment_id
        if not resolved_payment_id:
            with PagoUnitOfWork(self._session) as uow:
                pago_local = uow.pagos.get_ultimo_by_pedido(pedido_id)
                if pago_local and pago_local.mp_payment_id:
                    resolved_payment_id = pago_local.mp_payment_id

        # ── Consultar a MP ───────────────────────────────────────────────
        if resolved_payment_id:
            try:
                mp_info = self._consultar_pago_mp(resolved_payment_id)
            except RuntimeError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e),
                )

            # Mapeo de estados (misma lógica que en procesar_webhook)
            estado_mp = mp_info.get("mp_status")
            if estado_mp == "approved":
                nuevo_estado = "aprobado"
            elif estado_mp in ("rejected", "cancelled",
                               "refunded", "charged_back"):
                nuevo_estado = "rechazado"
            else:
                nuevo_estado = "pendiente"

            # ── Actualizar BD ────────────────────────────────────────────
            with PagoUnitOfWork(self._session) as uow:
                # Buscamos el pago en nuestra BD por el payment_id de MP
                pago = uow.pagos.get_by_mp_payment_id(resolved_payment_id)
                # Si no lo encontramos, tomamos el último pago del pedido
                if not pago:
                    pago = uow.pagos.get_ultimo_by_pedido(pedido_id)

                if pago:
                    # Actualizamos todos los campos con los datos frescos de MP
                    pago.mp_payment_id = resolved_payment_id
                    pago.mp_status = estado_mp
                    pago.mp_status_detail = mp_info.get("mp_status_detail")
                    pago.mp_merchant_order_id = mp_info.get(
                        "mp_merchant_order_id"
                    )
                    pago.estado = nuevo_estado
                    pago.updated_at = datetime.utcnow()
                    uow.pagos.update(pago)

                
            return PagoEstadoResponse(estado=nuevo_estado, pedido_id=pedido_id)

        # ── Sin payment_id que consultar ─────────────────────────────────
        # Solo devolvemos el estado local del último pago
        with PagoUnitOfWork(self._session) as uow:
            pago_local = uow.pagos.get_ultimo_by_pedido(pedido_id)
            return PagoEstadoResponse(
                estado=pago_local.estado if pago_local else None,
                pedido_id=pedido_id,
            )
