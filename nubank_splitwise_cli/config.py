import datetime
from pathlib import Path
import configparser
from typing import Optional


class Config:
    CONFIGS_PATH = f"{Path.home()}/.nsc/"
    CONFIG_FILE_NAME = "nsc.ini"
    DATE_FORMAT = "%Y-%m-%d"

    def __init__(self):
        Path(self.CONFIG_FILE_NAME).mkdir(exist_ok=True)
        self.config_file = configparser.ConfigParser()
        if not Path(self.CONFIGS_PATH + self.CONFIG_FILE_NAME).exists():
            self._create_empty_configuration_file()
        else:
            self.config_file.read(self.CONFIGS_PATH + self.CONFIG_FILE_NAME)

    def get_nubank_cert_path(self):
        return self.config_file["nubank"]["certpath"]

    def set_nubank_cert_path(self, cert_path: str):
        self.config_file.set("nubank", "certpath", cert_path)
        self._persist_config()

    def get_nubank_refresh_token(self):
        return self.config_file["nubank"]["refreshtoken"]

    def set_nubank_refresh_token(self, token: str):
        self.config_file.set("nubank", "refreshtoken", token)
        self._persist_config()

    def get_splitwise_api_key(self):
        return self.config_file["splitwise"]["apikey"]

    def set_splitwise_api_key(self, api_key: str):
        self.config_file.set("splitwise", "apikey", api_key)
        self._persist_config()

    def get_splitwise_default_group_id(self):
        return int(self.config_file["splitwise"]["defaultgroupid"])

    def set_splitwise_default_group_id(self, default_group_id: int):
        self.config_file.set("splitwise", "defaultgroupid", str(default_group_id))
        self._persist_config()

    def get_last_execution_date(self) -> Optional[str]:
        return  self.config_file["cli"]["last_execution_date"]

    def set_last_execution_date(self, _date: datetime.date):
        self.config_file.set("cli", "last_execution_date", _date.strftime(self.DATE_FORMAT))
        self._persist_config()

    def _persist_config(self):
        with open(self.CONFIGS_PATH + self.CONFIG_FILE_NAME, 'w') as fp:
            self.config_file.write(fp)

    def _create_empty_configuration_file(self):
        self.config_file.add_section("nubank")
        self.config_file.add_section("splitwise")
        self.config_file.add_section("cli")
        self.config_file.set("nubank", "certpath", "")
        self.config_file.set("nubank", "refreshtoken", "")
        self.config_file.set("splitwise", "apikey", "")
        self.config_file.set("splitwise", "defaultgroupid", "0")
        self.config_file.set("cli", "last_execution_date", "0")
        self._persist_config()
