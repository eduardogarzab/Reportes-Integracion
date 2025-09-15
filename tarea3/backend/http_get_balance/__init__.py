import azure.functions as func
from shared.models import BalanceOut
from decimal import Decimal

_FAKE = {
    "MX1234567890": Decimal("1250.55"),
    "MX0987654321": Decimal("98654.10")
}

async def main(req: func.HttpRequest) -> func.HttpResponse:
    account_id = req.route_params.get("accountId")
    if account_id not in _FAKE:
        return func.HttpResponse("Cuenta no encontrada", status_code=404)

    bal = BalanceOut(account=account_id, available=_FAKE[account_id])
    return func.HttpResponse(
        body=bal.model_dump_json(),
        status_code=200,
        mimetype="application/json"
    )
