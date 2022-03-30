from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List

from pynubank import Nubank


@dataclass
class Transaction:
    description: str
    amount: int
    time: datetime

    def __post_init__(self):
        if isinstance(self.time, str):
            self.time = datetime.strptime(self.time, "%Y-%m-%dT%H:%M:%SZ")

    def pretty_print(self):
        return f"""
        Description: {self.description}
        Time: {self.time.strftime("%Y-%m-%dT%H:%M:%SZ")}
        Amount: {self.amount / 100:.2f}
        """


class NubankWrapper:
    def __init__(self,
                 certificate_path: str,
                 refresh_token: Optional[str] = None,
                 tax_id: Optional[str] = None,
                 password: Optional[str] = None):
        self._nu = Nubank()

        if refresh_token:
            self.refresh_token = self._nu.authenticate_with_refresh_token(refresh_token, certificate_path)
        else:
            self.refresh_token = self._nu.authenticate_with_cert(tax_id, password, certificate_path)

    def get_credit_transactions(self, from_: datetime.date) -> List[Transaction]:
        transactions = [Transaction(s["description"], s["amount"], s["time"]) for s in self._nu.get_card_statements()]
        return list(filter(lambda t: t.time.date() >= from_, transactions))

    def get_debit_transactions(self, from_: datetime.date) -> List[Transaction]:
        return [Transaction(
            description=f"{s['detail']} ({s['__typename']})",
            amount=int(s['amount'] * 100),
            time=datetime.strptime(s["postDate"], "%Y-%m-%d"))
            for s in self._nu.get_account_statements() if s["postDate"] >= from_.strftime("%Y-%m-%d")]
