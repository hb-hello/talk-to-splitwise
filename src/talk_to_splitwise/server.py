from __future__ import annotations

import argparse
import logging
import os

from mcp.server import MCPServer

from talk_to_splitwise.grouping import ByPayerAndSplit
from talk_to_splitwise.models import Transaction
from talk_to_splitwise.splitwise_client import FriendInfo, GroupInfo, PostResult, SplitwiseClient

logger = logging.getLogger(__name__)

DRY_RUN = os.environ.get("TALK_TO_SPLITWISE_DRY_RUN", "true").lower() not in ("0", "false", "no")
TRANSPORT = os.environ.get("TALK_TO_SPLITWISE_TRANSPORT", "http").lower()
HOST = os.environ.get("TALK_TO_SPLITWISE_HOST", "127.0.0.1")
PORT = int(os.environ.get("TALK_TO_SPLITWISE_PORT", "8000"))

mcp = MCPServer("talk-to-splitwise")
_client = SplitwiseClient(dry_run=DRY_RUN)
_strategy = ByPayerAndSplit()


@mcp.tool()
def list_friends() -> list[FriendInfo]:
    """List the current user's Splitwise friends, with their user IDs."""
    return _client.list_friends()


@mcp.tool()
def list_groups() -> list[GroupInfo]:
    """List the current user's Splitwise groups, with their group IDs and member IDs."""
    return _client.list_groups()


@mcp.tool()
def post_transactions(transactions: list[Transaction]) -> list[PostResult]:
    """Group transactions that share the same payer/participants/group into
    combined Splitwise expenses, and post each resulting expense.

    In dry-run mode (default), no expense is actually created on Splitwise;
    the would-be API call is logged instead.
    """
    grouped = _strategy.group(transactions)
    return [_client.post_expense(g) for g in grouped]


def _cli_list_friends() -> None:
    for friend in _client.list_friends():
        print(f"{friend.id}\t{friend.first_name or ''} {friend.last_name or ''}".rstrip())


def _cli_list_groups() -> None:
    for group in _client.list_groups():
        print(f"{group.id}\t{group.name}\tmembers={group.member_ids}")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    parser = argparse.ArgumentParser(prog="talk-to-splitwise")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("list-friends", help="List Splitwise friends and exit")
    subparsers.add_parser("list-groups", help="List Splitwise groups and exit")
    args = parser.parse_args()

    if args.command == "list-friends":
        _cli_list_friends()
        return
    if args.command == "list-groups":
        _cli_list_groups()
        return

    if DRY_RUN:
        logger.info("Starting talk-to-splitwise MCP server in DRY-RUN mode (no expenses will be posted)")
    if TRANSPORT == "stdio":
        mcp.run(transport="stdio")
        return
    logger.info("Serving MCP over streamable-http on http://%s:%d/mcp", HOST, PORT)
    mcp.run(transport="streamable-http", host=HOST, port=PORT)


if __name__ == "__main__":
    main()
