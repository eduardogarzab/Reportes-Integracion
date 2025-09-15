import json
import azure.functions as func
from shared.models import TransferIn, TransferMsg
from shared.bus import send_transfer

async def main(req: func.HttpRequest) -> func.HttpResponse:
    idem = req.headers.get("Idempotency-Key")
    if not idem or len(idem) < 8:
        return func.HttpResponse("Falta Idempotency-Key", status_code=400)

    try:
        payload = TransferIn.model_validate_json(req.get_body())
    except Exception as e:
        return func.HttpResponse(f"JSON inválido: {e}", status_code=400)

    user_id = req.headers.get("x-user-id", "demo-user")
    msg = TransferMsg(**payload.model_dump(), user_id=user_id)
    send_transfer(msg.model_dump(), idem_key=idem)

    return func.HttpResponse(
        json.dumps({"status": "accepted", "tracking_id": idem}),
        status_code=202,
        mimetype="application/json"
    )
