import logging
from datetime import datetime, timedelta
from typing import List, Dict
from agentic_ingest import AgenticIngestionPipeline

logger = logging.getLogger(__name__)

def chrome_timestamp_to_iso(chrome_timestamp: float) -> str:
    """Converts a Chrome timestamp (microseconds since 1601-01-01) to ISO 8601 format."""
    # The epoch for Chrome timestamps is 1601-01-01 UTC.
    # The difference between the Chrome epoch and the Unix epoch (1970-01-01) is 11644473600 seconds.
    epoch_start = datetime(1601, 1, 1)
    delta = timedelta(microseconds=chrome_timestamp)
    return (epoch_start + delta).isoformat() + "Z"

def ingest_browser_data(items: List[Dict], vault_path: str) -> Dict:
    """
    Ingests browser data items.

    Args:
        items: A list of browser data items to ingest.
        vault_path: The path to the vault.

    Returns:
        A dictionary with the results of the ingestion.
    """
    logger.info(f"🌐 Browser ingest: {len(items)} items")

    # Preprocess browser data into structured format (like Gmail/Calendar)
    processed_items = []
    for item in items:
        try:
            # Extract fields
            title = item.get('title', '(No Title)')
            url = item.get('url', '')
            content = item.get('content', '')

            # Handle timestamp
            if 'timestamp' in item:
                timestamp = item['timestamp']
            elif 'visitTime' in item:
                timestamp = chrome_timestamp_to_iso(item['visitTime'])
            else:
                timestamp = datetime.utcnow().isoformat() + 'Z'

            extra_metadata = item.get('metadata', {})

            # Format as structured text (similar to Gmail/Calendar format)
            text_content = f"""Browser Content: {title}
URL: {url}
Captured: {timestamp}

{content}

---
Source URL: {url}
"""

            # Build metadata (following Gmail/Calendar pattern)
            metadata = {
                'platform': 'Browser',
                'timestamp': timestamp,
                'url': url,
                'quote': title,
                'source': f"Browser/{url}",
                'type': 'browser_content',
                **extra_metadata
            }

            processed_items.append({
                'text': text_content,
                'metadata': metadata
            })

        except Exception as e:
            logger.error(f"Error preprocessing browser item: {e}")
            continue

    logger.info(f"📝 Preprocessed {len(processed_items)} browser items")

    # Use AgenticIngestionPipeline (same as Gmail/Calendar)
    pipeline = AgenticIngestionPipeline(vault_path)

    ingested_count = 0
    errors = []

    for item in processed_items:
        try:
            # Prepare source metadata for the pipeline
            source_metadata = {
                'platform': 'Browser',
                'timestamp': item['metadata']['timestamp'],
                'url': item['metadata']['url'],
                'quote': item['metadata']['quote']
            }

            # Use the agentic pipeline to ingest
            result = pipeline.ingest(
                context=item['text'],
                source_metadata=source_metadata
            )

            if result.get('success', False):
                ingested_count += 1
                logger.info(f"✅ Ingested browser content: {item['metadata']['quote'][:50]}...")
            else:
                error_msg = f"Failed to ingest: {item['metadata']['quote'][:50]}"
                errors.append(error_msg)
                logger.warning(f"⚠️  {error_msg}")

        except Exception as e:
            error_msg = f"Error ingesting item: {str(e)}"
            errors.append(error_msg)
            logger.error(f"⚠️  {error_msg}")
            continue

    logger.info(f"✅ Browser ingest complete: {ingested_count}/{len(processed_items)} successful")

    return {
        'success': True,
        'items_processed': len(processed_items),
        'items_ingested': ingested_count,
        'errors': errors
    }
