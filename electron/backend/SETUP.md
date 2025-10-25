# Backend Setup & Testing Guide

## Initial Setup with Conda

### 1. Create Conda Environment

```bash
# Navigate to backend directory
cd /Users/henry/Documents/GitHub/localbrain/electron/backend

# Create conda environment
conda create -n localbrain python=3.10 -y

# Activate environment
conda activate localbrain

# Install dependencies
pip install -r requirements.txt
```

### 2. Verify Environment Variables

Check that `.env` exists with your API key:
```bash
cat .env
# Should show: ANTHROPIC_API_KEY=sk-ant-...
```

---

## Testing Vault Initialization + Simple Ingestion

### Step 1: Create Test Vault

```bash
# Create a test directory
mkdir ~/test-vault
```

### Step 2: Initialize Vault

```bash
# Make sure conda environment is activated
conda activate localbrain

# Run initialization script
python src/init_vault.py ~/test-vault
```

**Expected output:**
```
🚀 Initializing LocalBrain vault at: /Users/henry/test-vault
✅ Vault directory ready: /Users/henry/test-vault
✅ Created .localbrain/ directory
✅ Created internal directories (data/, logs/)
✅ Created app.json with default configuration
✅ Created 9 default folders:
   - personal/
   - career/
   - projects/
   - research/
   - social/
   - finance/
   - health/
   - learning/
   - archive/

🎉 Vault initialization complete!
📂 Vault location: /Users/henry/test-vault
📝 Ready to ingest content!
```

### Step 3: Verify Vault Structure

```bash
# List vault contents
ls -la ~/test-vault

# Should see:
# .localbrain/
# personal/
# career/
# projects/
# research/
# social/
# finance/
# health/
# learning/
# archive/

# Check config file
cat ~/test-vault/.localbrain/app.json

# Check a sample about.md
cat ~/test-vault/career/about.md
```

### Step 4: Test Simple Ingestion

```bash
# Test 1: Job search context (should go to career/)
python src/test_ingestion.py ~/test-vault \
  "I applied to NVIDIA for a software engineering internship on March 15, 2024"

# Verify file created
cat ~/test-vault/career/job-search.md
```

**Expected file content:**
```markdown
# job-search

Tracking and organizing career-related information.

## Content

I applied to NVIDIA for a software engineering internship on March 15, 2024[^1].

---

[^1]: Manual input, October 24, 2024
```

### Step 5: Test Appending to Existing File

```bash
# Add another job application
python src/test_ingestion.py ~/test-vault \
  "Got rejection from Google on March 20, 2024"

# Check that it appended
cat ~/test-vault/career/job-search.md
```

**Should now have both entries with [^1] and [^2] footnotes**

### Step 6: Test Different Categories

```bash
# Project context (should go to projects/)
python src/test_ingestion.py ~/test-vault \
  "Built a new React app for personal finance tracking"

cat ~/test-vault/projects/current-projects.md

# Learning context (should go to learning/)
python src/test_ingestion.py ~/test-vault \
  "Completed React course on Udemy covering hooks and context"

cat ~/test-vault/learning/notes.md

# Personal context (should go to personal/)
python src/test_ingestion.py ~/test-vault \
  "Need to remember my mom's birthday is May 15th"

cat ~/test-vault/personal/notes.md

# Finance context (should go to finance/)
python src/test_ingestion.py ~/test-vault \
  "Paid $1200 for rent on October 1st"

cat ~/test-vault/finance/transactions.md
```

---

## What's Working Now

✅ Vault initialization with proper structure
✅ Default folder creation (personal/, career/, etc.)
✅ about.md files in each folder
✅ Simple keyword-based ingestion
✅ File creation with markdown template
✅ Appending to existing files
✅ Automatic footnote numbering
✅ Context organized by category

---

## Next Steps (Not Implemented Yet)

- [ ] LLM-powered file selection (replace keyword matching)
- [ ] Intelligent content formatting
- [ ] Surgical file edits (file modification agent)
- [ ] Citation extraction from sources
- [ ] Embeddings and vector search
- [ ] Connectors (Gmail, Discord, etc.)

---

## Troubleshooting

**"Vault not initialized" error:**
```bash
# Make sure you ran init_vault.py first
python src/init_vault.py ~/test-vault
```

**Module not found errors:**
```bash
# Activate conda environment
conda activate localbrain

# Reinstall dependencies
pip install -r requirements.txt
```

**Permission denied:**
```bash
# Make scripts executable
chmod +x src/init_vault.py
chmod +x src/test_ingestion.py
```
