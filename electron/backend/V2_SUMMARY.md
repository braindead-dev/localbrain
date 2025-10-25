# V2 Pipeline - Quick Summary

## What I Fixed

### 1. Citation Explosion ❌ → ✅

**Before (V1):**
```json
{
  "6": {"quote": "Subject: Your Offer from Netflix"},
  "7": {"quote": "position of Software Engineer"},
  "8": {"quote": "full-time, exempt position"},
  "9": {"quote": "start date Monday, July 14"},
  "10": {"quote": "base salary $155,000"},
  ...10+ more citations
}
```

**After (V2):**
```json
{
  "6": {
    "platform": "Gmail",
    "quote": "Your starting base salary will be $155,000 per year. In addition, you will be eligible for a sign-on bonus of $25,000 and RSUs valued at $180,000...",
    "note": "Netflix job offer for SWE position"
  }
}
```

**ONE citation** for the entire source. All facts reference [1] in markdown.

---

### 2. Premature File Selection ❌ → ✅

**Before (V1 Flow):**
```
Decide WHERE → Then figure out WHAT to say
```
- Selected 3 files before knowing what to write
- Forced to create content to justify selections
- Resulted in duplication

**After (V2 Flow):**
```
Decide WHAT to say → Then WHERE to put it
```
- ONE LLM call analyzes everything
- Pre-writes ALL content
- Only selects files with specific edits

---

### 3. LLM Calls: 7 → 1

**V1:** 
- File selection (1)
- Format file 1 (1)
- Edit strategy file 1 (1)
- Format file 2 (1)
- Edit strategy file 2 (1)
- Format file 3 (1)
- Edit strategy file 3 (1)
- **Total: 7 calls**

**V2:**
- Analyze & create all edit plans (1)
- **Total: 1 call**

**Result:** 7x faster, 7x cheaper, more coherent

---

## New Components

### ContentAnalyzer (new)
Replaces FileSelector + ContentFormatter with ONE call that:
- Analyzes content
- Decides what to write for each file
- Creates ONE citation
- Returns complete edit plans

### AgenticIngestionPipelineV2
Simplified flow:
1. Analyze & route (1 LLM call)
2. Apply edits (deterministic)
3. Add citation (same one to all files)
4. Validate (check citations are used)

---

## Testing V2

### Using the script (recommended):

```bash
conda activate localbrain
cd /Users/henry/Documents/GitHub/localbrain/electron/backend

# Test with the Netflix offer
python scripts/ingest_from_file.py scripts/example_content.txt
```

### Direct usage:

```bash
python src/agentic_ingest_v2.py ~/Documents/GitHub/localbrain/my-vault "Your content here"
```

---

## Files Changed

**New files:**
- `src/core/ingestion/content_analyzer.py` - Single-pass analyzer
- `src/agentic_ingest_v2.py` - Redesigned pipeline
- `PIPELINE_V2_REDESIGN.md` - Full technical explanation
- `V2_SUMMARY.md` - This file

**Modified files:**
- `scripts/ingest_from_file.py` - Now uses V2 by default

**Unchanged:**
- `src/agentic_ingest.py` - V1 still exists for comparison

---

## Key Differences

| Feature | V1 | V2 |
|---------|----|----|
| LLM calls per ingestion | 7 | 1 |
| Citations per source | 10+ | 1 |
| File selection | Premature | After content |
| Content quality | Variable | Consistent |
| Duplication risk | High | Low |
| Validation | None | Built-in |

---

## What to Test

1. **Single topic** (job offer) - Should create 1 citation, update 2 files
2. **Multi-topic** (project work + interview) - Should separate topics cleanly
3. **Edge cases** - Long content, empty vault, etc.

Run the Netflix offer test first to see the difference!
