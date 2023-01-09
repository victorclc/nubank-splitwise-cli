from dataclasses import dataclass, field
from datetime import datetime
from typing import List

import requests


@dataclass
class UserShare:
    user_id: int
    owed_share: str
    paid_share: str


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
    category_id: int = 18  # GENERAL
    users_share: List[UserShare] = field(default_factory=list)

    def to_dict(self):
        dict_ = {
            **self.__dict__,
            "cost": f"{self.cost / 100:.2f}",
            "date": self.date.strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        dict_.pop("users_share")
        if self.users_share:
            for i, user_share in enumerate(self.users_share):
                dict_[f"users__{i}__user_id"] = user_share.user_id
                dict_[f"users__{i}__paid_share"] = user_share.paid_share
                dict_[f"users__{i}__owed_share"] = user_share.owed_share
        return dict_


@dataclass
class Member:
    id: int
    first_name: str
    last_name: str

    @classmethod
    def from_dict(cls, dict_):
        return Member(id=dict_["id"], first_name=dict_["first_name"], last_name=dict_["last_name"])


@dataclass
class User:
    id: int

    @classmethod
    def from_dict(cls, dict_):
        return User(id=dict_["id"])


@dataclass
class GroupDetails:
    id: str
    name: str
    members: List[Member]

    @classmethod
    def from_dict(cls, dict_):
        return GroupDetails(id=dict_["id"], name=dict_["name"], members=[Member.from_dict(d) for d in dict_["members"]])


class Splitwise:
    BASE_URL = "https://secure.splitwise.com/api/v3.0/"

    def __init__(self, api_key: str):
        self.__key = api_key

    def __default_headers(self):
        return {"Authorization": f"Bearer {self.__key}"}

    def current_user(self):
        response = requests.get(self.BASE_URL + "get_current_user", headers=self.__default_headers())
        return User.from_dict(response.json()["user"])

    def group_details(self, group_id: int) -> GroupDetails:
        response = requests.get(self.BASE_URL + f"get_group/{group_id}", headers=self.__default_headers())
        return GroupDetails.from_dict(response.json()["group"])

    def create_expense(self, expense: Expense):
        response = requests.post(self.BASE_URL + "create_expense", headers=self.__default_headers(),
                                 json=expense.to_dict())
        if response.status_code != 200 or not response.json()["expenses"]:
            raise Exception(f"create_expense error: {response.text}")  # TODO custom exception

    def get_groups(self):
        response = requests.get(self.BASE_URL + "get_groups", headers=self.__default_headers())
        return response.json()['groups']
