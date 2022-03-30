from dataclasses import dataclass
from datetime import datetime

import requests


@dataclass
class Expense:
    cost: int
    description: str
    date: datetime
    group_id: int
    details: str = "Auto by NSC"
    currency_code: str = "BRL"
    split_equally: bool = True
    repeat_interval: str = "never"
    category_id: str = 18  # GENERAL

    def to_dict(self):
        return {
            **self.__dict__,
            "cost": f"{self.cost / 100:.2f}",
            "date": self.date.strftime("%Y-%m-%dT%H:%M:%SZ")
        }


class Splitwise:
    BASE_URL = "https://secure.splitwise.com/api/v3.0/"

    def __init__(self, api_key: str):
        self.__key = api_key

    def __default_headers(self):
        return {"Authorization": f"Bearer {self.__key}"}

    def create_expense(self, expense: Expense):
        response = requests.post(self.BASE_URL + "create_expense", headers=self.__default_headers(),
                                 json=expense.to_dict())
        if response.status_code != 200 or not response.json()["expenses"]:
            raise Exception(f"create_expense error: {response.text}")  # TODO custom exception

    def get_groups(self):
        response = requests.get(self.BASE_URL + "get_groups", headers=self.__default_headers())
        return response.json()['groups']
