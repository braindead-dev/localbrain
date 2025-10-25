# Ingestion Scripts

## ingest_from_file.py

Ingest content from text files into your vault.

### Quick Start

```bash
conda activate localbrain

# Basic usage
python scripts/ingest_from_file.py my_content.txt

# With metadata (optional)
python scripts/ingest_from_file.py my_content.txt metadata.json
```

### Example

**content.txt:**
```
Got offer from Meta for $160k base, $30k bonus, $200k RSUs.
Start date June 1st, 2025 in Menlo Park.
```

**metadata.json** (optional):
```json
{
  "platform": "Gmail",
  "timestamp": "2024-10-25T14:30:00Z",
  "url": null,
  "quote": "We're pleased to offer you..."
}
```

**Run it:**
```bash
python scripts/ingest_from_file.py content.txt metadata.json
```

### Testing

```bash
# Test with example Netflix offer
python scripts/ingest_from_file.py example_content.txt
```

This is easier than typing long strings in the terminal!
