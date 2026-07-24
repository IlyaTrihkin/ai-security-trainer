import logging
import re
from datetime import datetime
from dateutil import parser as dateparser
import feedparser
from . import db
from .models import NewsArticle
from .rss_sources import RSS_SOURCES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_news_for_language(lang: str) -> int:
    """
    Fetches news from RSS sources for a given language ('ru' or 'en').
    Returns the number of new articles added.
    """
    sources = RSS_SOURCES.get(lang, [])
    if not sources:
        logger.warning(f"No RSS sources configured for language: {lang}")
        return 0

    added_count = 0

    for src in sources:
        name = src['name']
        url = src['url']
        logger.info(f"Fetching RSS: {name} ({url})")

        try:
            feed = feedparser.parse(url)
        except Exception as e:
            logger.error(f"Failed to parse RSS from {name}: {e}")
            continue

        if feed.bozo and not feed.entries:
            logger.warning(f"Bozo feed from {name} with no entries, skipping")
            continue

        for entry in feed.entries:
            link = entry.get('link', '')
            if not link:
                continue

            # Check for duplicates
            existing = NewsArticle.query.filter_by(link=link).first()
            if existing:
                continue

            title = entry.get('title', 'Без заголовка')
            summary_raw = entry.get('summary', '') or entry.get('description', '')
            # Strip HTML tags from summary
            summary = re.sub(r'<[^>]+>', '', summary_raw)[:1000] if summary_raw else ''

            published = None
            published_raw = entry.get('published', '') or entry.get('updated', '')
            if published_raw:
                try:
                    published = dateparser.parse(published_raw)
                except Exception:
                    published = datetime.utcnow()
            else:
                published = datetime.utcnow()

            article = NewsArticle(
                title=title[:500],
                link=link,
                summary=summary,
                published=published,
                source=name,
                language=lang
            )

            try:
                db.session.add(article)
                db.session.commit()
                added_count += 1
            except Exception as e:
                db.session.rollback()
                logger.error(f"Failed to save article '{title[:80]}' from {name}: {e}")

    logger.info(f"Fetched {added_count} new articles for language '{lang}'")
    return added_count


def fetch_all_news():
    """Fetches news for all configured languages."""
    total = 0
    for lang in RSS_SOURCES:
        total += fetch_news_for_language(lang)
    logger.info(f"Total new articles fetched: {total}")
    return total
