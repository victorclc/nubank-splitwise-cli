from datetime import datetime

import click

from config import Config
from nubank import NubankWrapper
from splitwise import Splitwise, Expense


@click.group()
def split_group():
    pass


def initialize_nubank_wrapper(config: Config) -> NubankWrapper:
    refresh_token = config.get_nubank_refresh_token()
    if refresh_token:
        return NubankWrapper(config.get_nubank_cert_path(), refresh_token=refresh_token)
    click.echo("Nubank login")
    tax_id = click.prompt("CPF")
    password = click.prompt("Password", hide_input=True)

    wrapper = NubankWrapper(config.get_nubank_cert_path(), tax_id=tax_id, password=password)
    config.set_nubank_refresh_token(wrapper.refresh_token)
    return wrapper


def initialize_splitwise(config: Config):
    api_key = config.get_splitwise_api_key()
    if api_key:
        return Splitwise(api_key)
    click.echo("Nubank login")
    api_key = click.prompt("SplitWise api key")
    return Splitwise(api_key)


@split_group.command
@click.option("--date-start", prompt="Transactions from date (yyyy-mm-dd): ",
              help="Transactions from date (yyyy-mm-dd)",
              type=click.DateTime(formats=["%Y-%m-%d"]))
def split_credit_transactions(date_start: datetime):
    config = Config()
    nubank = initialize_nubank_wrapper(config)
    transactions = nubank.get_card_transactions(date_start.date())

    to_split = []
    for i, transaction in enumerate(transactions, start=1):
        click.echo(f"{i} of {len(transactions)}")
        click.echo(transaction.pretty_print())
        if click.confirm("Split transaction?"):
            to_split.append(transaction)

    splitwise = initialize_splitwise(config)
    group_id = click.prompt("Group id", default=config.get_splitwise_default_group_id(), type=click.INT)

    click.echo(f"Adding {len(to_split)} transactions to splitwise group {group_id}.")
    for transaction in to_split:
        expense = Expense(cost=transaction.amount, description=transaction.description, date=transaction.time,
                          group_id=group_id)
        splitwise.create_expense(expense)
    click.echo("Finish")


if __name__ == '__main__':
    split_group()
