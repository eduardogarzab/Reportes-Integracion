from pydantic import BaseModel, Field, constr, condecimal
from datetime import datetime

class TransferIn(BaseModel):
    source_account: constr(strip_whitespace=True, min_length=10, max_length=34)
    destination_account: constr(strip_whitespace=True, min_length=10, max_length=34)
    amount: condecimal(gt=0, max_digits=12, decimal_places=2)
    currency: constr(pattern=r"^[A-Z]{3}$") = "MXN"
    reference: constr(strip_whitespace=True, min_length=1, max_length=64) = "MOBILE"

class TransferMsg(TransferIn):
    user_id: str
    request_ts: datetime = Field(default_factory=datetime.utcnow)

class BalanceOut(BaseModel):
    account: str
    available: condecimal(ge=0, max_digits=14, decimal_places=2)
    currency: str = "MXN"
