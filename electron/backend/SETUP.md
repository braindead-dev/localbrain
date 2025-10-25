# Setup Guide

## Prerequisites

- Python 3.10+
- Conda (recommended) or venv
- Anthropic API key

---

## Installation

### 1. Create Environment

```bash
# Navigate to backend directory
cd electron/backend

# Create conda environment
conda create -n localbrain python=3.10 -y
conda activate localbrain

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Key

```bash
# Create .env file
echo "ANTHROPIC_API_KEY=sk-ant-your-key-here" > .env

# Verify
cat .env
```

### 3. Initialize Vault

```bash
# Initialize your vault (one time)
python src/init_vault.py ~/my-vault
```

**Creates:**
```
my-vault/
├── .localbrain/           # Config and internal data
├── personal/              # Personal notes
├── career/                # Job search, applications
├── projects/              # Project work
├── research/              # Research notes
├── social/                # Social interactions
├── finance/               # Financial information
├── health/                # Health tracking
├── learning/              # Learning notes
└── archive/               # Archived content
```

---

## Quick Test

```bash
# Test with example content
python scripts/ingest_from_file.py scripts/example_content.txt
```

**Check results:**
```bash
cat ~/my-vault/career/Job\ Search.md
cat ~/my-vault/personal/About\ Me.md
```

---

## Troubleshooting

### "ANTHROPIC_API_KEY not found"

Add your API key to `.env`:
```bash
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
```

### "Vault not initialized"

Initialize first:
```bash
python src/init_vault.py ~/my-vault
```

### "Module not found"

Reinstall dependencies:
```bash
conda activate localbrain
pip install -r requirements.txt
```

---

## What's Implemented

✅ AI-powered ingestion (V2 pipeline)  
✅ Single-pass content analysis  
✅ Smart file routing  
✅ Citation management  
✅ Priority-based detail levels  
✅ Validation system  

## What's Next

- [ ] Embeddings and semantic search
- [ ] Web connectors (Gmail, Discord, etc.)
- [ ] Conflict detection
- [ ] Relationship linking
