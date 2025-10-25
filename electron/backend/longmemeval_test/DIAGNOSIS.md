# LongMemEval Benchmark - Diagnosis & Fixes Needed

## 🔴 Critical Issues Found

### 1. **Search Retrieval is FAILING**

**Problem**: Questions like "Which device did I get first, Samsung Galaxy S22 or Dell XPS 13?" return:
- ✅ 1 context found  
- ❌ Answer: "I cannot answer based on context"

**But the data EXISTS**:
```
test-vault/technology/devices_and_travel_setup.md:
- Samsung Galaxy S22: Purchased February 20, 2023
- Dell XPS 13: Actually arrived February 25, 2023
```

**Root Cause**: 
- Agentic search (ripgrep + LLM) not finding relevant files
- LLM getting wrong context chunks
- Answer generation too conservative

---

### 2. **Folder Naming is UGLY**

**Current (BAD)**:
```
food_and_dining/
personal_events/
work_and_career/
home_and_kitchen/
```

**Should be**:
```
Food and Dining/
Personal/Events/
Work and Career/
Home/Kitchen/
```

**Location**: `src/bulk_ingest.py` line 137
- Prompt says "Use clear, descriptive filenames"  
- Doesn't specify: no underscores, use title case

---

### 3. **Folder Organization is FLAT**

**Current Structure (BAD)**:
```
test-vault/
├── food_and_dining/
├── personal_events/
├── personal_shopping/
├── personal_interests/
├── personal_growth/
├── personal_finance/
├── personal_productivity/
└── personal_administration/
```

**Should Be (GOOD)**:
```
test-vault/
├── Personal/
│   ├── Events/
│   ├── Shopping/
│   ├── Interests/
│   ├── Growth/
│   ├── Finance/
│   ├── Productivity/
│   └── Administration/
├── Food and Dining/
└── Work and Career/
```

**Root Cause**: 
- Prompt doesn't encourage nested folders
- LLM creating flat structure with name prefixes instead

---

## 🔧 Fixes Needed

### Fix 1: Improve Bulk Ingestion Prompt

**File**: `src/bulk_ingest.py` line 123-151

**Current prompt issues**:
- No guidance on folder naming conventions
- No encouragement for nested structures
- Too vague on organization

**New prompt should specify**:
```
FOLDER NAMING RULES:
1. Use Title Case with spaces: "Food and Dining" not "food_and_dining"
2. Create nested folders for related content: "Personal/Events" not "personal_events"
3. Max 2-3 levels deep
4. Group by broad category first, then subcategory

EXAMPLES:
✅ Personal/Shopping/clothing.md
✅ Work and Career/job_search.md  
✅ Health/Fitness/workouts.md
❌ personal_shopping/clothing.md
❌ work_and_career/job_search.md
❌ health_and_fitness/workouts.md
```

### Fix 2: Improve Agentic Search

**File**: `src/agentic_search.py`

**Issues**:
1. grep patterns too specific - misses variations
2. LLM not reading enough files
3. Answer generation too cautious

**Improvements needed**:
```python
# More flexible grep patterns
pattern = "Samsung|Galaxy|S22|Dell|XPS"  # Not just exact match

# Read more files when uncertain
if len(grep_results) < 3:
    # Expand search

# Better answer prompt
"Based on the context, synthesize a direct answer. 
If dates are mentioned, compare them explicitly."
```

### Fix 3: Add Hybrid Search

Current: LLM-only (slow, can miss patterns)
Better: grep + LLM hybrid

```python
def search(query):
    # 1. Fast grep scan for keywords
    keywords = extract_keywords(query)
    grep_results = grep_vault(keywords)
    
    # 2. LLM refines and answers
    answer = llm_answer(grep_results, query)
    
    return answer
```

---

## 📊 LongMemEval Results So Far

**First 50 questions**:
- Contexts found: ~60% (30/50)
- Correct answers: ~0% (LLM says "cannot answer")
- Daemon crashes: ~40% (20/50 connection refused)

**Why so bad?**:
1. Search not finding files even when content exists
2. Answer generation too conservative
3. Daemon stability issues (connection refused)

---

## ✅ Action Plan

1. **FIX PROMPT** (bulk_ingest.py) - 5 mins
   - Add folder naming rules
   - Encourage nested structure
   - Give examples

2. **WIPE & RE-INGEST** - 20 mins
   - Delete test-vault
   - Re-run ingestion with new prompt
   - Verify folder structure looks good

3. **IMPROVE SEARCH** (agentic_search.py) - 15 mins
   - More flexible grep patterns
   - Read more files
   - Better answer synthesis

4. **RE-RUN EVAL** - 10 mins
   - Test on 50 questions
   - Should get >80% retrieval rate
   - Should get >60% correct answers

**Total time**: ~50 mins to properly working benchmark

---

## 🎯 Success Criteria

After fixes:
- ✅ Folder names: "Personal/Events" not "personal_events"
- ✅ Retrieval rate: >80% (40/50 questions find contexts)
- ✅ Answer accuracy: >60% (30/50 questions correct)
- ✅ Daemon stable: 0% connection refused errors
