#!/bin/bash

# ==================================================
# Script: run_full_scraper.sh
# Description:
#   Runs both post scraper and comments/reactions scraper
#   in sequence using tmux sessions. Logs are saved separately.
# Author: [Alireza Parvaresh]
# Last Updated: 2025-06-22
# ==================================================

set -e  # Exit if any command fails

# -------------------------
# Configuration
# -------------------------
LOG_DIR="logs"
mkdir -p "$LOG_DIR"

# ---------- 1. Run Post Scraper ----------
POST_SESSION="getposts"
POST_TIMESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')
POST_LOG="$LOG_DIR/$POST_SESSION-$POST_TIMESTAMP.log"
POST_SCRIPT="python3 get_posts.py --channels input/channels.json --days 1"

echo "🚀 Starting POST scraper in tmux session '$POST_SESSION'..."

tmux new-session -d -s "$POST_SESSION" \
  "echo '[INFO] Running post scraper...'; \
   $POST_SCRIPT | tee '$POST_LOG'; \
   echo '[INFO] Post scraping done. Closing session...'; \
   sleep 1; \
   tmux kill-session -t $POST_SESSION"

# ---------- 2. Wait for Post Scraper to Finish ----------
echo "⏳ Waiting for post scraper to finish..."
tmux wait-for -S $POST_SESSION  # Just to ensure next block starts after

while tmux has-session -t $POST_SESSION 2>/dev/null; do
    sleep 2
done

echo "✅ Post scraper completed."

# ---------- 3. Run Comment/Reaction Scraper ----------
CR_SESSION="get_comments_reactions"
CR_TIMESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')
CR_LOG="$LOG_DIR/$CR_SESSION-$CR_TIMESTAMP.log"
CR_SCRIPT="python3 get_comments_reactions.py --limit 36"

echo "🚀 Starting COMMENT/REACTION scraper in tmux session '$CR_SESSION'..."

tmux new-session -d -s "$CR_SESSION" \
  "echo '[INFO] Running comment/reaction scraper...'; \
   $CR_SCRIPT | tee '$CR_LOG'; \
   echo '[INFO] Reactions/comments scraping done. Closing session...'; \
   sleep 1; \
   tmux kill-session -t $CR_SESSION"

echo "📄 Logs:"
echo "  - Post Scraper Log:        $POST_LOG"
echo "  - Comments/Reactions Log:  $CR_LOG"

echo "✅ All scraping processes launched."
