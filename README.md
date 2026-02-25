# Daily Telegram Scraper

A modular, high-performance Telegram channel scraper that collects **posts**, **comments**, and **reactions** from public Telegram channels and stores them in **ClickHouse**. It supports HTTP proxy and MTProto proxy connections, Jalali (Shamsi) calendar conversion, parallel batch processing, and distributed tmux-based workers.

---

## Features

- **Post Scraping via HTTP:** Scrapes public channel pages (`t.me/s/{channel}`) using HTTP requests and BeautifulSoup — no Telegram client needed for posts.
- **Comment Fetching via Telethon:** Retrieves threaded comments using the Telegram MTProto API with multiple sessions.
- **Reaction Extraction:** Extracts emoji reactions and their counts for each post.
- **ClickHouse Storage:** All data (posts, comments, reactions) is batch-inserted into ClickHouse using the HTTP interface and Buffer tables for high throughput.
- **Jalali Calendar Support:** Converts Gregorian dates to Jalali (Shamsi), detects Iranian holidays using the `salnama` library.
- **Parallel Batch Processing:** Uses `ProcessPoolExecutor` + `ThreadPoolExecutor` for post scraping across thousands of channels.
- **Distributed tmux Workers:** Launches multiple tmux sessions for concurrent comment/reaction fetching across Telegram sessions.
- **Rate-Limit Handling:** Gracefully handles Telegram's `FloodWaitError` with automatic retry and backoff.
- **Proxy Support:** Supports both HTTP proxies (for web scraping) and MTProto proxies (for Telegram API).
- **Modular Architecture:** Clean separation of concerns across fetch tools, database models, workers, and configuration.

---

## Project Structure

```
daily_telegram/
├── config.py                          # Telegram API credentials, proxy settings, session count
├── get_posts.py                       # Main entry point: batch post scraper (multiprocessing + threading)
├── get_comments_reactions.py          # Splits work & launches tmux workers for comments/reactions
├── run_full_scraper.sh                # Shell script to run post scraper then comments/reactions sequentially
├── requirements.txt                   # Python dependencies
├── input/
│   └── channels.json                  # JSON file with list of Telegram channel URLs
├── fetch_tools/
│   ├── posts.py                       # HTTP-based post scraper (t.me/s/ pages), parses HTML, inserts to ClickHouse
│   ├── comments.py                    # Async Telethon-based comment fetcher
│   ├── reactions.py                   # Async Telethon-based reaction fetcher
│   ├── utils.py                       # ClickHouse batch insertion, HTML parsing, holiday checking, media type detection
│   └── configDB.py                    # ClickHouse connection settings (URL, auth, DB name, HTTP headers)
├── db/
│   ├── db.py                          # SQLAlchemy engine & session for ClickHouse
│   └── models.py                      # SQLAlchemy models: BufferPost, BufferComment, BufferReaction
├── utils/
│   ├── worker_posts.py                # Channel normalization, worker function for post fetching
│   └── worker_comments_reactions.py   # Async worker: connects Telethon client, processes batch file
├── session/
│   ├── create_esssion.py              # Script to create multiple Telethon sessions with MTProto proxy
│   └── telegram_*.session             # Auto-generated Telethon session files
├── output/
│   ├── batches/                       # Batch JSON files with channel → msgid mappings
│   └── tmp_batches/                   # Temporary worker batch files
└── logs/                              # Log files from scraper runs
```

---

## How It Works

### Phase 1: Post Scraping (`get_posts.py`)

1. Reads the channel list from `input/channels.json`.
2. Splits channels into batches (default: 1000 channels per batch).
3. Each batch is processed in a separate process (`ProcessPoolExecutor`).
4. Within each batch, channels are scraped concurrently using threads (`ThreadPoolExecutor`).
5. Posts are fetched by scraping `https://t.me/s/{channel}` HTML pages via HTTP (with proxy if configured).
6. Each post is parsed for: message ID, text content, view count, date, and media type.
7. Gregorian dates are converted to Jalali; Iranian holidays are detected.
8. Posts are batch-inserted into the `telegram_posts_buffer` ClickHouse table.
9. Collected message IDs are saved to `output/batches/batch_XXX.json`.

### Phase 2: Comments & Reactions (`get_comments_reactions.py`)

1. Reads all batch JSON files from `output/batches/`.
2. Flattens `(channel, msgid)` pairs and splits them into chunks for N workers.
3. Each chunk is saved as a text file (`worker_batch_N.txt`).
4. tmux sessions are launched, each running `worker_comments_reactions.py` with a Telethon session file.
5. Each worker connects via MTProto proxy, iterates over its batch, and:
   - Fetches reactions per message and inserts into `telegram_reactions_buffer`.
   - Fetches threaded comments and inserts into `telegram_comments_buffer`.

### Full Pipeline (`run_full_scraper.sh`)

Runs Phase 1, waits for completion, then launches Phase 2 — all via tmux with logging.

---

## Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd daily_telegram
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Telegram API Credentials

Edit `config.py` with your API credentials from [my.telegram.org](https://my.telegram.org):

```python
api_id = 123456
api_hash = 'your_api_hash_here'
```

### 4. Configure Proxy Settings

In `config.py`, update the HTTP and MTProto proxy settings:

```python
# HTTP Proxy (for web scraping)
HTTP_PROXY_HOST = 'your_proxy_ip'
HTTP_PROXY_PORT = 8888
HTTP_PROXY_USER = 'user'
HTTP_PROXY_PASS = 'password'

# MTProto Proxy (for Telegram API)
MTPROTO_PROXY = {
    'server': 'your_proxy_ip',
    'port': 443,
    'secret': 'your_hex_secret'
}
```

### 5. Configure ClickHouse

Edit `fetch_tools/configDB.py`:

```python
CLICKHOUSE_HTTP_URL = "http://localhost:8123/"
CLICKHOUSE_AUTH = ("your_user", "your_password")
DB_NAME = "your_database"
```

### 6. Create ClickHouse Tables

Connect to ClickHouse and create the required database and tables:

```sql
CREATE DATABASE IF NOT EXISTS vazir1;

-- Main posts table
CREATE TABLE vazir1.telegram_posts (
    channel String,
    msgid UInt32,
    ptype Nullable(String),
    views UInt64,
    reactions UInt64,
    is_forwarded UInt8,
    forwarded_from Nullable(String),
    txtContent Nullable(String),
    date DateTime('Asia/Tehran'),
    shdate String,
    day_of_week UInt8,
    is_holiday UInt8,
    insert_date DateTime('Asia/Tehran'),
    update_date DateTime('Asia/Tehran')
) ENGINE = MergeTree()
ORDER BY (channel, msgid);

-- Buffer table for posts (high-throughput writes)
CREATE TABLE vazir1.telegram_posts_buffer AS vazir1.telegram_posts
ENGINE = Buffer(vazir1, telegram_posts, 16, 10, 600, 10000, 100000, 10000000, 200000000);

-- Main comments table
CREATE TABLE vazir1.telegram_comments (
    comment_id UInt32,
    channel String,
    msgid UInt32,
    user_id UInt64,
    ptype Nullable(String),
    reactions UInt64,
    is_reply UInt8,
    reply_to Nullable(UInt32),
    txtContent Nullable(String),
    date DateTime('Asia/Tehran'),
    shdate String,
    day_of_week UInt8,
    is_holiday UInt8,
    insert_date DateTime('Asia/Tehran'),
    update_date DateTime('Asia/Tehran')
) ENGINE = MergeTree()
ORDER BY (channel, msgid, comment_id);

-- Buffer table for comments
CREATE TABLE vazir1.telegram_comments_buffer AS vazir1.telegram_comments
ENGINE = Buffer(vazir1, telegram_comments, 16, 10, 600, 10000, 100000, 10000000, 200000000);

-- Main reactions table
CREATE TABLE vazir1.telegram_reactions (
    channel String,
    msgid UInt32,
    reaction String,
    count UInt32,
    insert_date DateTime('Asia/Tehran'),
    update_date DateTime('Asia/Tehran')
) ENGINE = MergeTree()
ORDER BY (channel, msgid, reaction);

-- Buffer table for reactions
CREATE TABLE vazir1.telegram_reactions_buffer AS vazir1.telegram_reactions
ENGINE = Buffer(vazir1, telegram_reactions, 16, 10, 600, 10000, 100000, 10000000, 200000000);
```

### 7. Prepare Input Channels

Edit `input/channels.json`:

```json
{
  "channels": [
    "https://t.me/channel_name_1",
    "https://t.me/channel_name_2"
  ]
}
```

### 8. Create Telegram Sessions

Run the session creator to authenticate your Telegram accounts:

```bash
python3 session/create_esssion.py
```

This will prompt you to enter phone numbers and verification codes for each session.

---

## Usage

### Run the Full Pipeline

```bash
bash run_full_scraper.sh
```

This will:
1. Scrape posts from all channels (last 1 day by default).
2. Wait for post scraping to complete.
3. Launch tmux workers to fetch comments and reactions.

### Run Post Scraper Only

```bash
python3 get_posts.py --channels input/channels.json --days 3
```

**Arguments:**

| Argument | Default | Description |
|---|---|---|
| `--channels` | `input/channels.json` | Path to the channels JSON file |
| `--days` | `1` | Number of past days to scrape posts for |

### Run Comments & Reactions Scraper Only

```bash
python3 get_comments_reactions.py --limit 36
```

**Arguments:**

| Argument | Default | Description |
|---|---|---|
| `--limit` | `36` | Maximum number of comments to fetch per post |

---

## Output Formats

### Post Record (ClickHouse)

```json
{
  "channel": "example_channel",
  "msgid": 12345,
  "ptype": "text + photo",
  "views": 15200,
  "reactions": 42,
  "is_forwarded": 0,
  "forwarded_from": "",
  "txtContent": "Post content text...",
  "date": "2025-06-20 14:30:00",
  "shdate": "1404-3-30",
  "day_of_week": 4,
  "is_holiday": 0
}
```

### Comment Record (ClickHouse)

```json
{
  "comment_id": 78910,
  "channel": "example_channel",
  "msgid": 12345,
  "user_id": 456789123,
  "ptype": "text",
  "reactions": 3,
  "is_reply": 1,
  "reply_to": 78900,
  "txtContent": "This is a reply comment.",
  "date": "2025-06-20 15:00:00",
  "shdate": "1404-3-30",
  "day_of_week": 4,
  "is_holiday": 0
}
```

### Reaction Record (ClickHouse)

```json
{
  "channel": "example_channel",
  "msgid": 12345,
  "reaction": "🔥",
  "count": 15
}
```

---

## Docker

### Build and Run with Docker Compose

```bash
docker compose up -d
```

This starts both the ClickHouse database and the scraper application. See `Dockerfile` and `docker-compose.yml` for details.

### Run Interactively (for session creation)

```bash
docker compose run --rm app python3 session/create_esssion.py
```

---

## Configuration Reference

| File | Purpose |
|---|---|
| `config.py` | Telegram API ID/hash, HTTP proxy, MTProto proxy, session count |
| `fetch_tools/configDB.py` | ClickHouse HTTP URL, auth credentials, database name |
| `input/channels.json` | List of Telegram channel URLs to scrape |

---

## License

This project is licensed under the MIT License. You are free to use, modify, and contribute.

---

## Contributing

Bug reports and feature requests are welcome! Please open an issue or submit a pull request.
