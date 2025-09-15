import json, logging, time, random
from decimal import Decimal
import azure.functions as func

def call_core_settlement(source, dest, amount, currency, reference) -> dict:
    time.sleep(0.2)
    if random.random() < 0.03:
        return {"ok": False, "code": "CORE_TIMEOUT"}
    return {"ok": True, "auth_code": "AP" + str(random.randint(100000, 999999))}

def _to_decimal(x):
    return Decimal(str(x))

def main(msg: func.ServiceBusMessage):
    body = json.loads(msg.get_body().decode("utf-8"))
    t = body
    logging.info(f"[transfer] recibido: {t}")

    try:
        res = call_core_settlement(
            t["source_account"], t["destination_account"],
            _to_decimal(t["amount"]), t["currency"], t["reference"]
        )
        if not res["ok"]:
            raise RuntimeError(f"core error: {res}")
        logging.info(f"[transfer] liquidada ok auth={res['auth_code']}")
    except Exception as e:
        logging.exception(f"[transfer] fallo: {e}")
        raise
