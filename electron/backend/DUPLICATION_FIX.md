# Duplication Fix - Priority-Based Detail Levels

**Issue:** Ingestion was duplicating the same detailed information across multiple files.

**Example Problem:**
```
Input: "Received NVIDIA offer: $155k base, $25k bonus, $180k RSUs"

Old Behavior:
- career/Job Search.md: 
  "Received offer from NVIDIA... $155k base, $25k bonus, $180k RSUs [6-11]"
  
- personal/About Me.md:
  "Received offer from NVIDIA... $155k base, $25k bonus, $180k RSUs [4-9]"
  
❌ Same detailed info in both files!
```

---

## Solution: Priority-Based Formatting

### Concept

Files are now categorized as:
- **PRIMARY** (full details) - Gets comprehensive information
- **SECONDARY** (high-level) - Gets brief summary only

### How It Works

**1. File Selection** (unchanged)
- Agent selects multiple files
- Marks each as `primary` or `secondary`

**2. Content Formatting** (NEW)
- Primary files: Get ALL details with multiple citations
- Secondary files: Get KEY FACT only with minimal citations

**3. Result**
```
Input: "Received NVIDIA offer: $155k base, $25k bonus, $180k RSUs"

New Behavior:
- career/Job Search.md (PRIMARY):
  "Received official offer from NVIDIA... Base salary $155,000 [6], 
   sign-on bonus $25,000 [7], RSUs $180,000 vesting over 4 years [8]."
  → FULL DETAILS with citations for each fact
  
- personal/About Me.md (SECONDARY):
  "Accepted Software Engineer position at NVIDIA [3]."
  → HIGH-LEVEL summary, one citation
  
✅ No duplication! Each file has appropriate level of detail.
```

---

## Implementation

### Modified Files

**1. `src/core/ingestion/content_formatter.py`**

Added `priority` parameter and priority-aware prompting:

```python
def format_for_append(
    self,
    vault_path: Path,
    file_path: Path,
    context: str,
    source_metadata: Dict,
    priority: str = "primary"  # NEW PARAMETER
) -> Tuple[str, Dict]:
```

**Prompt adjustment based on priority:**

```python
if priority == "primary":
    detail_instruction = """
    DETAIL LEVEL: PRIMARY (Full Details)
    - Include ALL specific information (numbers, dates, names, amounts)
    - Cite each factual claim separately
    - Be comprehensive and thorough
    """
else:  # secondary
    detail_instruction = """
    DETAIL LEVEL: SECONDARY (High-Level Summary)
    - Include only the KEY FACT or main point
    - Keep it brief and concise (1-2 sentences max)
    - Don't duplicate detailed information from primary files
    - Example: "Accepted position at NVIDIA" 
      NOT "Accepted position at NVIDIA for $155k with $25k bonus..."
    """
```

**2. `src/agentic_ingest.py`**

Updated pipeline to pass priority through:

```python
# Pass priority to append/modify methods
success = self._append_to_file(
    file_path,
    context,
    source_metadata,
    priority=selection.get('priority', 'primary')  # NEW
)
```

Added priority display:

```python
def _append_to_file(..., priority: str = "primary"):
    detail_level = "full details" if priority == "primary" else "high-level summary"
    print(f"   Appending to file ({detail_level})...")  # Shows in output
```

---

## Example Scenarios

### Scenario 1: Job Offer (Single Topic)

**Input:**
```
"Received offer from Stripe: $170k base, $40k sign-on, equity package"
```

**File Selection:**
```
PRIMARY:   career/Job Search.md
SECONDARY: personal/About Me.md
```

**Output:**

**Job Search.md (PRIMARY):**
```markdown
Received official offer from Stripe for Backend Engineer position [12].
Base salary $170,000 per year [13], sign-on bonus $40,000 [14], 
and equity package included [15].
```
→ 4 citations, full compensation breakdown

**About Me.md (SECONDARY):**
```markdown
Accepted Backend Engineer position at Stripe [4].
```
→ 1 citation, just the key fact

---

### Scenario 2: Multi-Topic (Diverse Information)

**Input:**
```
"Started React open source contribution and got Google interview for Chrome team"
```

**File Selection:**
```
PRIMARY: projects/Open Source.md (React contribution details)
PRIMARY: career/Job Search.md (Google interview)
```

**Output:**

**Open Source.md (PRIMARY):**
```markdown
Started contributing to React open source project [5]. 
Submitted first PR fixing bug in reconciliation algorithm [6].
```
→ Full details about the contribution

**Job Search.md (PRIMARY):**
```markdown
Received invitation for technical interview with Google's Chrome team [7].
Interview scheduled for December 5th [8].
```
→ Full details about the interview

**NO duplication** - each file gets its relevant topic in full detail!

---

### Scenario 3: Update + New Info

**Input:**
```
"Meta interview moved from Nov 5th to Nov 10th. Also my mom is visiting next week."
```

**File Selection:**
```
PRIMARY:   career/Job Search.md (interview update)
SECONDARY: personal/Family.md (mom visit)
```

**Output:**

**Job Search.md (PRIMARY):**
```markdown
Meta interview rescheduled to November 10th [15] due to scheduling conflict.
```
→ Full details about the change

**Family.md (SECONDARY):**
```markdown
Mom visiting next week [3].
```
→ Brief mention

---

## Benefits

### ✅ No Duplication
- Same information doesn't appear verbatim in multiple files
- Each file gets appropriate level of detail

### ✅ Better Organization
- Primary files serve as "source of truth" with full details
- Secondary files have high-level cross-references
- User can find complete info in the right place

### ✅ Reduced Citation Clutter
- Primary files: Multiple citations (one per fact)
- Secondary files: Minimal citations (one for key fact)
- Fewer total citations to manage

### ✅ Smarter Context
- Agent understands what belongs where
- Adapts detail level to file's purpose
- Maintains information relationships without redundancy

---

## Testing

### Test Command

```bash
# Don't actually run - just showing structure
python src/agentic_ingest.py ~/my-vault \
  "Received offer from company X for $Y salary and $Z bonus" \
  '{"platform": "Gmail", "timestamp": "...", ...}'
```

### Expected Behavior

**PRIMARY file (e.g., Job Search.md):**
- Lists ALL details: salary, bonus, equity, dates, location, recruiter
- Multiple citations [6], [7], [8], [9]...
- Comprehensive paragraph

**SECONDARY file (e.g., About Me.md):**
- Brief mention: "Accepted position at Company X [4]"
- Single citation
- One sentence

---

## Edge Cases Handled

### 1. All Primary Files
If all selected files are marked `primary`, all get full details:
```
PRIMARY: projects/LocalBrain.md
PRIMARY: career/Job Search.md
```
→ Both get full details of their respective topics

### 2. All Secondary Files
If all are `secondary` (rare), all get summaries:
```
SECONDARY: personal/Notes.md
SECONDARY: archive/Old Updates.md
```
→ Both get brief mentions

### 3. Mixed Topics in Single Input
Agent separates topics and routes appropriately:
```
"Built new feature AND got interview"
→ projects/: feature details (PRIMARY)
→ career/: interview details (PRIMARY)
```

---

## Future Enhancements

### Potential Improvements

1. **Explicit detail control**
   - User specifies: "full" vs "summary" vs "mention-only"
   - Override agent's decision

2. **Context-aware summaries**
   - Secondary summaries adapt to existing file content
   - Don't repeat what's already known

3. **Citation linking**
   - Secondary files link to primary: "See [[Job Search]] for details"
   - Creates knowledge graph connections

4. **Smart deduplication**
   - Detect if information already exists
   - Don't add duplicate even in primary files

---

## Summary

**Problem:** Detailed information duplicated across multiple files

**Solution:** Priority-based formatting
- Primary files = full details
- Secondary files = high-level summaries

**Result:** Clean, organized, non-redundant knowledge base! ✅

**Status:** ✅ Implemented and ready for testing
