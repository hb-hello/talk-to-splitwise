# talk-to-splitwise

An MCP server that takes a batch of transactions (invoice line items, daily
expenses, etc.), groups the ones that share the same payer/participants/group
into combined Splitwise expenses, and posts them to Splitwise.

## Setup

```sh
uv sync
```

Splitwise credentials (only needed when not in dry-run mode):

```sh
export SPLITWISE_API_KEY=...   # personal API key, see https://secure.splitwise.com/oauth_clients
```

## Dry run mode

By default (`TALK_TO_SPLITWISE_DRY_RUN=true`), no Splitwise API calls are
made. `post_transactions` logs the `createExpense` payload it would have
sent instead of calling Splitwise, and `list_friends`/`list_groups` return
empty lists. Set `TALK_TO_SPLITWISE_DRY_RUN=false` (and provide credentials
above) to post for real.

## Run

By default the server listens over HTTP (MCP's `streamable-http` transport)
at `http://127.0.0.1:8000/mcp`:

```sh
uv run talk-to-splitwise
```

Configure the bind address with `TALK_TO_SPLITWISE_HOST` /
`TALK_TO_SPLITWISE_PORT`. To run over stdio instead (e.g. for a local MCP
client that launches the process itself), set
`TALK_TO_SPLITWISE_TRANSPORT=stdio`.

## Tools

- `list_friends()` — Splitwise friends and their user IDs
- `list_groups()` — Splitwise groups, IDs, and member IDs
- `post_transactions(transactions)` — groups transactions (default strategy:
  same payer + same participant set + same group get merged into one
  expense) and posts each resulting expense to Splitwise

## Design notes

- MVP grouping strategy (`ByPayerAndSplit`) is the only sound way to merge
  line items given Splitwise's one-split-per-expense model; other strategies
  can implement `GroupingStrategy` (`src/talk_to_splitwise/grouping/base.py`).
- The server is stateless: `post_transactions` groups and posts in one call,
  no separate preview/confirm step and no persistence layer.
- Splitwise category is not wired up yet (`Transaction.category` is present
  for future grouping strategies but isn't sent to Splitwise).
