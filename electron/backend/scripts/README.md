# Ingestion Scripts

Helper scripts for testing and running ingestion.

## ingest_from_file.py

Ingest content from a text file into your vault.

### Usage

```bash
# Activate conda environment first
conda activate localbrain

# Basic usage (Manual source metadata)
python scripts/ingest_from_file.py my_content.txt

# With source metadata
python scripts/ingest_from_file.py my_content.txt metadata.json
```

### Example Files

**content.txt:**
```
Got offer from Meta for Software Engineer role. 
Base salary $160k, sign-on bonus $30k, and RSU grant worth $200k over 4 years.
Start date is June 1st, 2025 in Menlo Park office.
```

**metadata.json:**
```json
{
  "platform": "Gmail",
  "timestamp": "2024-10-25T14:30:00Z",
  "url": null,
  "quote": "We're pleased to offer you a base salary of $160,000..."
}
```

### Creating Test Files

```bash
# Create content file
cat > test_content.txt << 'EOF'
Started learning Rust programming language. 
Completed chapters 1-5 of the Rust Book covering ownership, borrowing, and lifetimes.
Working through exercises and building a small CLI tool.
EOF

# Create metadata file (optional)
cat > test_metadata.json << 'EOF'
{
  "platform": "Manual",
  "timestamp": "2024-10-25T20:00:00Z",
  "url": null,
  "quote": null
}
EOF

# Ingest
python scripts/ingest_from_file.py test_content.txt test_metadata.json
```

### Quick Testing Workflow

1. **Write your content** in a txt file
2. **(Optional)** Create metadata JSON
3. **Run the script**
4. **Check the vault** to see what was updated

This is much easier than typing long strings in the terminal!

### Tips

- Keep content files focused on one topic for better routing
- Use realistic timestamps in metadata
- Include direct quotes when available
- Test edge cases (multi-topic content, very short content, etc.)
