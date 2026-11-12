"""Read-only ClickHouse queries for the data tab (plus schema creation)."""

import requests

from settings import load_settings


class ClickHouseError(Exception):
    pass


def query(sql: str, ch: dict | None = None, fmt: str = "JSON"):
    ch = ch or load_settings()["clickhouse"]
    body = f"{sql}\nFORMAT {fmt}" if fmt else sql
    try:
        r = requests.post(
            ch["url"],
            params={"database": ch["database"]},
            data=body.encode("utf-8"),
            auth=(ch["user"], ch["password"]),
            timeout=20,
        )
    except requests.RequestException as e:
        raise ClickHouseError(f"Cannot reach ClickHouse at {ch['url']}: {e}") from e
    if r.status_code != 200:
        raise ClickHouseError(r.text.strip()[:600])
    return r.json()["data"] if fmt == "JSON" else r.text


def ping(ch: dict | None = None) -> dict:
    ch = ch or load_settings()["clickhouse"]
    version = query("SELECT version() AS v", ch)[0]["v"]
    tables = [row["name"] for row in query(
        "SELECT name FROM system.tables WHERE database = currentDatabase() ORDER BY name", ch)]
    return {"version": version, "database": ch["database"], "tables": tables}


# Rows written by reactions.py into telegram_posts_buffer only carry (channel, msgid,
# reactions); real post rows always have a shdate, so we group by post and keep those.
POSTS = "telegram_posts_buffer"
COMMENTS = "telegram_comments_buffer"
REACTIONS = "telegram_reactions_buffer"


def overview() -> dict:
    totals = query(f"""
        SELECT
          (SELECT uniqExactIf((channel, msgid), shdate != '') FROM {POSTS}) AS posts,
          (SELECT uniqExactIf(channel, shdate != '') FROM {POSTS}) AS channels,
          (SELECT uniqExact(channel, msgid, comment_id) FROM {COMMENTS}) AS comments,
          (SELECT count() FROM {REACTIONS}) AS reaction_rows,
          (SELECT toString(maxIf(insert_date, shdate != '')) FROM {POSTS}) AS last_post_insert,
          (SELECT toString(max(insert_date)) FROM {COMMENTS}) AS last_comment_insert
    """)[0]
    daily = query(f"""
        SELECT toString(toDate(date)) AS day, uniqExact(channel, msgid) AS posts
        FROM {POSTS}
        WHERE shdate != '' AND date >= today() - 13
        GROUP BY day ORDER BY day
    """)
    top_reactions = query(f"""
        SELECT reaction, sum(c) AS count FROM (
          SELECT channel, msgid, reaction, max(count) AS c FROM {REACTIONS} GROUP BY channel, msgid, reaction
        ) GROUP BY reaction ORDER BY count DESC LIMIT 12
    """)
    return {"totals": totals, "daily": daily, "top_reactions": top_reactions}


def channels(limit: int = 200) -> list[dict]:
    rows = query(f"""
        SELECT channel, count() AS posts, sum(v) AS views, sum(r) AS reactions,
               toString(max(d)) AS last_post
        FROM (
          SELECT channel, msgid, max(views) AS v, max(reactions) AS r, max(date) AS d
          FROM {POSTS} GROUP BY channel, msgid HAVING countIf(shdate != '') > 0
        )
        GROUP BY channel ORDER BY posts DESC LIMIT {int(limit)}
    """)
    comments = {r["channel"]: int(r["c"]) for r in query(
        f"SELECT channel, uniqExact(msgid, comment_id) AS c FROM {COMMENTS} GROUP BY channel")}
    for r in rows:
        r["comments"] = comments.get(r["channel"], 0)
    return rows


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'")


def recent_posts(channel: str = "", limit: int = 30) -> list[dict]:
    where = f"AND channel = '{_esc(channel)}'" if channel else ""
    return query(f"""
        SELECT channel, msgid,
               anyIf(ptype, shdate != '') AS ptype,
               max(views) AS views, max(reactions) AS reactions,
               toString(max(date)) AS date, anyIf(shdate, shdate != '') AS shdate,
               anyIf(substring(ifNull(txtContent, ''), 1, 400), shdate != '') AS text
        FROM {POSTS}
        WHERE (channel, msgid) IN (
          SELECT channel, msgid FROM {POSTS} WHERE shdate != '' {where}
          ORDER BY date DESC LIMIT {int(limit)}
        )
        GROUP BY channel, msgid ORDER BY date DESC
    """)


def recent_comments(channel: str = "", limit: int = 30) -> list[dict]:
    where = f"WHERE channel = '{_esc(channel)}'" if channel else ""
    return query(f"""
        SELECT channel, msgid, comment_id, user_id, reactions, toString(date) AS date,
               substring(ifNull(txtContent, ''), 1, 300) AS text
        FROM {COMMENTS} {where}
        ORDER BY insert_date DESC LIMIT {int(limit)}
    """)


def init_schema() -> list[str]:
    """Create the database, MergeTree tables and Buffer tables if they do not exist."""
    ch = load_settings()["clickhouse"]
    db = ch["database"]
    post_cols = """
        channel String, msgid UInt32, ptype Nullable(String), views UInt64, reactions UInt64,
        is_forwarded UInt8, forwarded_from Nullable(String), txtContent Nullable(String),
        date DateTime('Asia/Tehran'), shdate String, day_of_week UInt8, is_holiday UInt8,
        insert_date DateTime('Asia/Tehran'), update_date DateTime('Asia/Tehran')"""
    comment_cols = """
        comment_id UInt32, channel String, msgid UInt32, user_id UInt64, ptype Nullable(String),
        reactions UInt64, is_reply UInt8, reply_to Nullable(UInt32), txtContent Nullable(String),
        date DateTime('Asia/Tehran'), shdate String, day_of_week UInt8, is_holiday UInt8,
        insert_date DateTime('Asia/Tehran'), update_date DateTime('Asia/Tehran')"""
    reaction_cols = """
        channel String, msgid UInt32, reaction String, count UInt32,
        insert_date DateTime('Asia/Tehran'), update_date DateTime('Asia/Tehran')"""
    buffer = "16, 10, 600, 10000, 100000, 10000000, 200000000"
    statements = [f"CREATE DATABASE IF NOT EXISTS {db}"]
    for name, cols, order in (
        ("telegram_posts", post_cols, "(channel, msgid)"),
        ("telegram_comments", comment_cols, "(channel, msgid, comment_id)"),
        ("telegram_reactions", reaction_cols, "(channel, msgid, reaction)"),
    ):
        statements.append(f"CREATE TABLE IF NOT EXISTS {db}.{name} ({cols}) ENGINE = MergeTree() ORDER BY {order}")
        statements.append(f"CREATE TABLE IF NOT EXISTS {db}.{name}_buffer AS {db}.{name} "
                          f"ENGINE = Buffer({db}, {name}, {buffer})")
    # The database may not exist yet, so run against `default`.
    bootstrap = {**ch, "database": "default"}
    for sql in statements:
        query(sql, bootstrap, fmt="")
    return statements
