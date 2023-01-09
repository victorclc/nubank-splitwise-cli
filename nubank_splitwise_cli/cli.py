import sys
from datetime import datetime
from typing import List

import click
from pynubank import NuRequestException

from .config import Config
from .nubank import NubankWrapper, Transaction
from .splitwise import Splitwise, Expense, Member, UserShare, GroupDetails, User

pass_config = click.make_pass_decorator(Config)


class NotConfiguredException(Exception):
    ...


@click.group()
@click.pass_context
def cli(ctx: click.Context):
    ctx.obj = Config()


@cli.command
@click.option("--date-start", prompt="Transactions from date (yyyy-mm-dd)",
              help="Transactions from date (yyyy-mm-dd)",
              default=Config().get_last_execution_date(),
              type=click.DateTime(formats=["%Y-%m-%d"]))
@pass_config
def split_credit(config: Config, date_start: datetime):
    nubank = initialize_nubank_wrapper(config)
    split_transactions(config, nubank.get_credit_transactions(date_start.date()))


@cli.command
@click.option("--date-start", prompt="Transactions from date (yyyy-mm-dd)",
              default=Config().get_last_execution_date(),
              help="Transactions from date (yyyy-mm-dd)",
              type=click.DateTime(formats=["%Y-%m-%d"]))
@pass_config
def split_debit(config: Config, date_start: datetime):
    nubank = initialize_nubank_wrapper(config)
    split_transactions(config, nubank.get_debit_transactions(date_start.date()))


@cli.command
@click.option("--date-start", prompt="Transactions from date (yyyy-mm-dd)",
              help="Transactions from date (yyyy-mm-dd)",
              default=Config().get_last_execution_date(),
              type=click.DateTime(formats=["%Y-%m-%d"]))
@pass_config
def split_all(config: Config, date_start: datetime):
    nubank = initialize_nubank_wrapper(config)
    split_transactions(config, nubank.get_transactions(date_start.date()))


@cli.command
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
    nubank_config_credentials(config)
    click.echo("Nubank configuration completed.\n")


def nubank_config_credentials(config: Config) -> NubankWrapper:
    click.echo("Enter your credentials")
    tax_id = click.prompt("CPF")
    password = click.prompt("Password", hide_input=True)

    wrapper = NubankWrapper(config.get_nubank_cert_path(), tax_id=tax_id, password=password)
    config.set_nubank_refresh_token(wrapper.refresh_token)

    return wrapper


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


def initialize_nubank_wrapper(config: Config) -> NubankWrapper:
    refresh_token = config.get_nubank_refresh_token()
    if not refresh_token:
        raise_not_configured_exception()

    click.echo("Obtaining Nubank session...")
    try:
        return NubankWrapper(config.get_nubank_cert_path(), refresh_token=refresh_token)
    except NuRequestException as ex:
        if ex.status_code == 403:
            click.echo("Nubank session expired. Please re-enter your credentials.")
            return nubank_config_credentials(config)


def initialize_splitwise(config: Config):
    api_key = config.get_splitwise_api_key()
    if not api_key:
        raise_not_configured_exception()
    return Splitwise(api_key)


@cli.command
def splitwise_list_groups():
    config = Config()
    splitwise = Splitwise(config.get_splitwise_api_key())
    for group in splitwise.get_groups():
        click.echo(f"id: {group['id']}\tname: {group['name']}")


def collect_users_share(currend_user, members: List[Member], cost: int, percentage_cache: dict):
    shares = []
    for i, member in enumerate(members, start=1):
        click.echo(f"id: {i}\tname: {member.first_name} {member.last_name}")
        percentage = click.prompt("Percentage", type=click.INT, default=percentage_cache.get(member.id))
        percentage_cache[member.id] = percentage
        owed_share = f"{(cost * percentage) / 10000}"
        paid_share = "0"
        if member.id == currend_user.id:
            paid_share = f"{cost / 100}"

        shares.append(
            UserShare(
                member.id,
                owed_share=owed_share,
                paid_share=paid_share
            )
        )
    return shares


def collect_split_option():
    click.echo("1 - Skip")
    click.echo("2 - Split equally")
    click.echo("3 - Split by shares")

    return click.prompt("Choose option", default="1",
                        type=click.Choice(["1", "2", "3"]))


def split_transaction_equally(transaction: Transaction, group_id: int) -> Expense:
    click.echo("Spliting transaction equally.")
    return Expense(
        cost=transaction.amount,
        description=transaction.description,
        date=transaction.time,
        group_id=group_id
    )


def split_transaction_by_shares(transaction: Transaction, group_details: GroupDetails, current_user: User, percentage_shares_cache: dict) -> Expense:
    users_share = collect_users_share(current_user, group_details.members, transaction.amount, percentage_shares_cache)
    click.echo("Spliting transaction by shares.")
    return Expense(
        cost=transaction.amount,
        description=transaction.description,
        date=transaction.time,
        group_id=int(group_details.id),
        split_equally=False,
        users_share=users_share
    )


def split_transactions(config: Config, transactions: List[Transaction]):
    if not transactions:
        click.echo("No transactions found.")
        return

    splitwise = initialize_splitwise(config)
    group_id = choose_splitwise_group(splitwise, config, "Select group id to add expenses")
    group_details = splitwise.group_details(group_id)
    current_user = splitwise.current_user()

    to_split = []
    percentage_shares_cache = {}
    for i, transaction in enumerate(transactions, start=1):
        click.echo(f"{i} of {len(transactions)}")
        click.echo(transaction.pretty_print())
        option = collect_split_option()

        if option == "1":
            click.echo("Skiping transaction.")
            continue

        if option == "2":
            expense = split_transaction_equally(transaction, group_id)
            to_split.append(expense)

        if option == "3":
            expense = split_transaction_by_shares(transaction, group_details, current_user, percentage_shares_cache)
            to_split.append(expense)

    click.echo(f"Adding {len(to_split)} transactions to splitwise group {group_id}.")
    for expense in to_split:
        splitwise.create_expense(expense)

    config.set_last_execution_date(datetime.now().date())
    click.echo("Done.")
