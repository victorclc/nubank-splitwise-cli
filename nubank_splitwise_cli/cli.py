from datetime import datetime
from typing import Callable, List

import click
import sys

from .config import Config
from .nubank import NubankWrapper, Transaction
from .splitwise import Splitwise, Expense


@click.group()
def cli_group():
    pass


class NotConfiguredException(Exception):
    ...


def raise_not_configured_exception():
    raise NotConfiguredException(f"{sys.argv[0]} not configured properly. Run '{sys.argv[0]} configure'")


def choose_splitwise_group(splitwise: Splitwise, config: Config, message: str):
    click.echo("Fetching splitwise groups...")
    groups = {str(g["id"]): g["name"] for g in splitwise.get_groups()}
    for _id, name in groups.items():
        click.echo(f"{_id} - {name}")
    group_id = int(click.prompt(message, default=str(config.get_splitwise_default_group_id()),
                                type=click.Choice(list(groups.keys()))))
    return group_id


def nubank_config_wizard(config: Config):
    click.echo(
        """Nubank Configuration
First, you need to generate .p12 certificate so the authentication works properly, to do so, in another terminal,
run the command 'pynubank' and follow the instructions.
With the certificate in hands, enter the absolute path of the file bellow.
"""
    )
    config.set_nubank_cert_path(
        click.prompt("Nubank .p12 certificate absolute path", default=config.get_nubank_cert_path())
    )
    click.echo("Enter your credentials")
    tax_id = click.prompt("CPF")
    password = click.prompt("Password", hide_input=True)

    wrapper = NubankWrapper(config.get_nubank_cert_path(), tax_id=tax_id, password=password)
    config.set_nubank_refresh_token(wrapper.refresh_token)

    click.echo("Nubank configuration completed.\n")


def splitwise_config_wizard(config: Config):
    click.echo(
        """Splitwise Configuration
Now, you will need to create an app and an api key with your splitwise account on here: 
https://secure.splitwise.com/apps 
"""
    )
    config.set_splitwise_api_key(
        click.prompt("Your api key", default=config.get_splitwise_api_key())
    )
    config.set_splitwise_default_group_id(
        choose_splitwise_group(Splitwise(config.get_splitwise_api_key()), config, "Choose the default group")
    )

    click.echo("Splitwise configuration completed.\n")


@cli_group.command
@click.option("--nubank-cert-path",
              help="Absolute path of the generated nubank certificate. For how to generate a certificate please check: https://github.com/andreroggeri/pynubank/blob/master/examples/login-certificate.md")
@click.option("--splitwise-api-key", help="You can generate one here: https://secure.splitwise.com/apps")
@click.option("--splitwise-default-group-id", help="Default group id to register expenses.", type=click.INT)
def configure(nubank_cert_path: str, splitwise_api_key: str, splitwise_default_group_id: int):
    config = Config()
    if nubank_cert_path:
        config.set_nubank_cert_path(nubank_cert_path)
    if splitwise_api_key:
        config.set_splitwise_api_key(splitwise_api_key)
    if splitwise_default_group_id:
        config.set_splitwise_default_group_id(splitwise_default_group_id)

    if not nubank_cert_path and not splitwise_api_key and not splitwise_default_group_id:
        nubank_config_wizard(config)
        splitwise_config_wizard(config)


def initialize_nubank_wrapper(config: Config) -> NubankWrapper:
    refresh_token = config.get_nubank_refresh_token()
    if refresh_token:
        click.echo("Obtaining Nubank session...")
        return NubankWrapper(config.get_nubank_cert_path(), refresh_token=refresh_token)
    raise_not_configured_exception()


def initialize_splitwise(config: Config):
    api_key = config.get_splitwise_api_key()
    if api_key:
        return Splitwise(api_key)
    raise_not_configured_exception()


@cli_group.command
def splitwise_list_groups():
    config = Config()
    splitwise = Splitwise(config.get_splitwise_api_key())
    for group in splitwise.get_groups():
        click.echo(f"id: {group['id']}\tname: {group['name']}")


def split_transactions(config: Config, get_transactions_func: Callable[[], List[Transaction]]):
    transactions = get_transactions_func()
    if not transactions:
        click.echo("No transactions found.")
        return

    splitwise = initialize_splitwise(config)
    group_id = choose_splitwise_group(splitwise, config, "Select group id to add expenses")

    to_split = []
    for i, transaction in enumerate(transactions, start=1):
        click.echo(f"{i} of {len(transactions)}")
        click.echo(transaction.pretty_print())
        if click.confirm("Split transaction?"):
            to_split.append(transaction)

    click.echo(f"Adding {len(to_split)} transactions to splitwise group {group_id}.")
    for transaction in to_split:
        expense = Expense(cost=transaction.amount, description=transaction.description, date=transaction.time,
                          group_id=group_id)
        splitwise.create_expense(expense)
    click.echo("Done.")


def get_credit_transactions(nubank: NubankWrapper, date_start: datetime):
    click.echo("Fetching Nubank credit transactions...")
    return nubank.get_credit_transactions(date_start.date())


def get_debit_transactions(nubank: NubankWrapper, date_start: datetime):
    click.echo("Fetching Nubank debit transactions...")
    return nubank.get_debit_transactions(date_start.date())


def get_all_transactions(nubank: NubankWrapper, date_start: datetime):
    click.echo("Fetching Nubank debit and credit transactions...")
    return nubank.get_debit_transactions(date_start.date()) + nubank.get_credit_transactions(date_start.date())


@cli_group.command
@click.option("--date-start", prompt="Transactions from date (yyyy-mm-dd): ",
              help="Transactions from date (yyyy-mm-dd)",
              type=click.DateTime(formats=["%Y-%m-%d"]))
def split_credit(date_start: datetime):
    config = Config()
    nubank = initialize_nubank_wrapper(config)
    split_transactions(config, lambda: get_credit_transactions(nubank, date_start))


@cli_group.command
@click.option("--date-start", prompt="Transactions from date (yyyy-mm-dd): ",
              help="Transactions from date (yyyy-mm-dd)",
              type=click.DateTime(formats=["%Y-%m-%d"]))
def split_debit(date_start: datetime):
    config = Config()
    nubank = initialize_nubank_wrapper(config)
    split_transactions(config, lambda: get_debit_transactions(nubank, date_start))


@cli_group.command
@click.option("--date-start", prompt="Transactions from date (yyyy-mm-dd): ",
              help="Transactions from date (yyyy-mm-dd)",
              type=click.DateTime(formats=["%Y-%m-%d"]))
def split_all(date_start: datetime):
    config = Config()
    nubank = initialize_nubank_wrapper(config)
    split_transactions(config, lambda: get_all_transactions(nubank, date_start))
