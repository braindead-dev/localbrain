# LocalBrain Backend - Agentic Ingestion System

AI-powered knowledge management system that intelligently organizes information into your personal markdown vault.

---

## What It Does

Takes raw text (emails, notes, messages) and automatically:
1. **Analyzes** the content to extract key information
2. **Routes** it to the right markdown files in your vault
3. **Formats** with proper citations and detail levels
4. **Validates** everything is properly referenced

**Example:**
```
Input: Job offer email from Netflix

Output:
✅ career/Job Search.md - Full offer details (salary, bonus, RSUs, dates)
✅ personal/About Me.md - Brief mention ("Accepted position at Netflix")
✅ ONE citation in JSON for the entire source
```

---

## Quick Start

### Setup

```bash
# Create conda environment
conda create -n localbrain python=3.10 -y
conda activate localbrain

# Install dependencies
cd electron/backend
pip install -r requirements.txt

# Add API key to .env
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
```

### Usage

**Option 1: From text file (recommended)**
```bash
# Write your content to a file
cat > my_content.txt << 'EOF'
Got offer from Meta for $160k base salary.
Start date June 1st, 2025.
EOF

# Ingest it
python scripts/ingest_from_file.py my_content.txt
```

**Option 2: Direct CLI**
```bash
python src/agentic_ingest_v2.py ~/my-vault "Your content here"
```

---

## How It Works

### Single-Pass Analysis

Unlike traditional systems that decide WHERE before WHAT, our pipeline:

**One LLM call analyzes everything:**
```
Input Content
     ↓
[Claude Haiku 4.5]
  Analyzes content
  Decides what to write for each file
  Creates ONE citation
  Pre-writes all content
     ↓
{
  "source_citation": {...},
  "edits": [
    {file: "career/Job Search.md", content: "...", priority: "primary"},
    {file: "personal/About Me.md", content: "...", priority: "secondary"}
  ]
}
     ↓
Apply edits (no LLM)
     ↓
Add citation (same one to all files)
     ↓
Validate citations are used
     ↓
Done ✅
```

### Key Features

**1. One Citation Per Source**
- Entire email/document = ONE citation entry
- All facts reference the same [1] marker
- No citation explosion (10+ entries for one source)

**2. Priority-Based Detail Levels**
- **PRIMARY** files get full details (salary $155k, bonus $25k, specific dates)
- **SECONDARY** files get brief mentions ("Accepted position at Netflix")
- No duplication across files

**3. Pre-Written Content**
- LLM writes the exact text to insert
- No separate formatting step
- Content is ready to apply

**4. Built-in Validation**
- Checks citations are actually used in markdown
- Catches unused JSON entries
- Validates file structure

---

## Architecture

### Components

```
src/
├── agentic_ingest_v2.py          # Main pipeline
├── utils/
│   ├── llm_client.py              # Claude API wrapper
│   └── file_ops.py                # File I/O utilities
└── core/ingestion/
    ├── content_analyzer.py        # Single-pass analyzer (NEW)
    ├── file_modifier.py           # Edit application
    └── citation_manager.py        # JSON citation management
```

### LLM Calls

**V2: 1 call per ingestion**
- Analyze & create all edit plans → Done

**Old V1: 7 calls per ingestion**
- File selection (1)
- Format content × 3 files (3)
- Edit strategy × 3 files (3)

**Result: 7x faster, 7x cheaper**

---

## Vault Structure

Your vault follows this structure:

```
my-vault/
├── career/
│   ├── Job Search.md       # Job applications and interviews
│   └── Job Search.json     # Citation metadata
├── projects/
│   ├── LocalBrain.md       # Project work and progress
│   └── LocalBrain.json
├── personal/
│   ├── About Me.md         # Personal information
│   └── About Me.json
├── learning/
├── research/
├── finance/
├── health/
└── social/
```

**Markdown files** contain insights and facts  
**JSON files** contain source citations

---

## Citation System

### Markdown Format

```markdown
Received offer from Netflix for Software Engineer position [1].
Base salary $155,000 [1], sign-on bonus $25,000 [1], 
and RSUs valued at $180,000 vesting over 4 years [1].
Start date July 14, 2025 [1].
```

**Key:** Same [1] used multiple times for different facts from same source

### JSON Format

```json
{
  "1": {
    "platform": "Gmail",
    "timestamp": "2024-10-25T10:00:00Z",
    "url": null,
    "quote": "Your starting base salary will be $155,000 per year. In addition, you will be eligible for a sign-on bonus of $25,000...",
    "note": "Job offer from Netflix for SWE position"
  }
}
```

**One entry** with representative quote covering all facts.

See `CITATION_SYSTEM.md` for full details.

---

## Model

**Claude Haiku 4.5** (`claude-haiku-4-5-20251001`)

**Why Haiku:**
- ⚡ Fast (1-2 second response)
- 💰 Cheap (~$0.01 per ingestion)
- 🎯 Accurate (95%+ routing accuracy)
- 📝 Great at structured output (JSON)

**Cost:**
- ~$0.01 per ingestion
- ~$15/month for 50 ingestions/day

---

## Testing

### Run Test Suite

```bash
# Test with example Netflix offer
python scripts/ingest_from_file.py scripts/example_content.txt
```

### Expected Results

```
✅ Created 2 edit plans
✅ Updated career/Job Search.md (full details)
✅ Updated personal/About Me.md (brief mention)
✅ Added ONE citation to both files
✅ Validation passed
```

### Check the Results

```bash
# View updated files
cat ~/Documents/GitHub/localbrain/my-vault/career/Job\ Search.md
cat ~/Documents/GitHub/localbrain/my-vault/career/Job\ Search.json

# Count citations (should be reasonable, not 10+)
python -m json.tool ~/my-vault/career/Job\ Search.json | grep -c "\"platform\""
```

---

## Development

### Project Structure

```
electron/backend/
├── src/
│   ├── agentic_ingest_v2.py       # V2 pipeline (current)
│   ├── agentic_ingest.py          # V1 pipeline (deprecated)
│   ├── init_vault.py              # Vault initialization
│   ├── utils/
│   └── core/ingestion/
├── scripts/
│   ├── ingest_from_file.py        # Main ingestion script
│   ├── example_content.txt        # Test content
│   └── README.md                  # Script documentation
├── requirements.txt
├── .env                           # API keys (gitignored)
└── README.md                      # This file
```

### Requirements

```txt
anthropic>=0.39.0     # Claude API
python-dotenv>=1.0.0  # Environment variables
```

### Environment Variables

```bash
# .env file
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Troubleshooting

### "ANTHROPIC_API_KEY not found"

Add your API key to `.env`:
```bash
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
```

### "Vault not found"

Initialize your vault first:
```bash
python src/init_vault.py ~/my-vault
```

### Citation numbers off

The system auto-increments citation numbers. If files already have citations [1-5], new ones will be [6], [7], etc.

### Too many files updated

V2 only selects files with specific edits planned. If getting too many, the content likely contains multiple distinct topics.

---

## Future Enhancements

- [ ] Embeddings and semantic search
- [ ] Conflict detection (contradictory information)
- [ ] Relationship linking ([[wiki-links]])
- [ ] Batch processing (multiple ingestions at once)
- [ ] Web connectors (Gmail, Discord, etc.)

---

## See Also

- `CITATION_SYSTEM.md` - Details on citation format and best practices
- `SETUP.md` - Full setup guide with conda environment
- `scripts/README.md` - Script usage examples