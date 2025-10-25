# Citation System Documentation

## Overview

LocalBrain uses a **numbered citation system** with separate JSON metadata files for source tracking. This keeps markdown files clean and readable while maintaining detailed source information.

---

## File Pairing System

Each markdown file has a corresponding JSON file:

```
career/
├── job-search.md       # Content with [1], [2] citations
├── job-search.json     # Citation metadata
├── resume.md
└── resume.json
```

---

## Markdown Format

**Example: `job-search.md`**

```markdown
# job-search

Tracking my job application process and outcomes.

## Applications

Applied to over 200 internships but received no responses [1]. Most applications were for software engineering roles at tech companies [2].

Received positive feedback from recruiters at NVIDIA and Google during networking events [3], suggesting the issue isn't technical skills but application approach.

Got an offer from Meta for full-time position with $150k base salary [4].

## Related Topics

- [[resume-optimization]]
- [[interview-prep]]
- [[networking-strategies]]
```

**Key Points:**
- Use `[1]`, `[2]`, `[3]` for inline citations (not `[^1]`)
- No footnote section at bottom of markdown
- Clean, readable content
- Only cite factual claims that need verification

---

## JSON Metadata Format

**Example: `job-search.json`**

```json
{
  "1": {
    "platform": "Gmail",
    "timestamp": "2024-01-15T10:30:00Z",
    "description": "Gmail analysis showing automated rejection emails from 180+ companies",
    "url": null,
    "quote": null
  },
  "2": {
    "platform": "LinkedIn",
    "timestamp": "2024-03-01T14:20:00Z",
    "description": "LinkedIn job application history for Jan-Mar 2024",
    "url": "https://linkedin.com/jobs/applications",
    "quote": null
  },
  "3": {
    "platform": "Manual",
    "timestamp": "2024-02-15T16:00:00Z",
    "description": "Career fair notes from university event",
    "url": null,
    "quote": "Really impressed with your React experience! We'd love to see an application."
  },
  "4": {
    "platform": "Gmail",
    "timestamp": "2024-03-25T09:00:00Z",
    "description": "Offer letter from Meta",
    "url": null,
    "quote": "We're pleased to offer you a full-time Software Engineer position with a base salary of $150,000."
  }
}
```

---

## JSON Schema

Each citation entry must include:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `platform` | string | ✅ Yes | Source platform (Gmail, Discord, Manual, LinkedIn, etc.) |
| `timestamp` | string | ✅ Yes | ISO 8601 timestamp (e.g., "2024-03-15T10:30:00Z") |
| `description` | string | ✅ Yes | Brief description of what this citation references |
| `url` | string or null | ✅ Yes | Link to source if available, otherwise null |
| `quote` | string or null | ✅ Yes | Direct quotation if applicable, otherwise null |

**Additional Optional Fields:**
- `date_range`: For citations covering a time period (e.g., "Jan-Mar 2024")
- `author`: For citations with specific authors
- `context`: Additional context about the source

---

## Citation Guidelines

### When to Cite

✅ **DO cite:**
- Specific numbers and statistics
- Dates and timestamps
- Direct quotes from people or documents
- Factual claims that could be verified
- Decisions and outcomes
- External sources (emails, messages, documents)

❌ **DON'T cite:**
- General observations
- Personal opinions
- Common knowledge
- Speculative thoughts
- Connecting insights between sources

### Example

```markdown
# Correct Usage

I applied to NVIDIA on March 15 [1] and received a rejection on March 20 [2]. 
This suggests my application materials might need improvement.

# Breakdown:
- "applied to NVIDIA on March 15" → Factual, needs citation [1]
- "received a rejection on March 20" → Factual, needs citation [2]  
- "suggests my application materials might need improvement" → Analysis, no citation needed
```

---

## File Management

### Creating New Files

When creating a new markdown file, also create its JSON file:

```python
# Create markdown file
with open("career/job-search.md", "w") as f:
    f.write(markdown_content)

# Create empty JSON citations file
with open("career/job-search.json", "w") as f:
    json.dump({}, f, indent=2)
```

### Adding Citations

When appending content with citations:

1. Find the next citation number
2. Add `[n]` to markdown content
3. Add metadata entry to JSON file

```python
# Get next citation number
with open("job-search.json", "r") as f:
    citations = json.load(f)
    next_num = str(max([int(k) for k in citations.keys()]) + 1) if citations else "1"

# Add to JSON
citations[next_num] = {
    "platform": "Gmail",
    "timestamp": "2024-03-25T09:00:00Z",
    "description": "Offer letter from Meta",
    "url": None,
    "quote": "Base salary of $150,000"
}

with open("job-search.json", "w") as f:
    json.dump(citations, f, indent=2)
```

### Updating Existing Citations

Citations are immutable by citation number. If source information changes, add a new citation rather than modifying an existing one.

---

## Benefits of This System

### 1. Clean Markdown
- Readable files without cluttered footnotes
- Easy to edit manually
- Standard markdown syntax

### 2. Rich Metadata
- Full source tracking with timestamps
- Direct quotes preserved
- URLs and platform information
- Extensible schema for future needs

### 3. Searchable Sources
- Can query all citations by platform
- Find all quotes from a specific source
- Time-based analysis of sources

### 4. Separation of Concerns
- Content in markdown (human-readable)
- Metadata in JSON (machine-readable)
- Easy to parse and process separately

---

## Integration with Ingestion

### LLM-Powered Citation Extraction

When ingesting content, the LLM will:

1. **Identify factual claims** that need citations
2. **Extract source metadata** from the original context
3. **Generate markdown** with `[n]` citations
4. **Create JSON entries** with full metadata

**Example Ingestion Flow:**

```python
# Input context
context = {
    "text": "Email from recruiter@meta.com: We're offering $150k base salary",
    "platform": "Gmail",
    "timestamp": "2024-03-25T09:00:00Z",
    "sender": "recruiter@meta.com"
}

# LLM generates
markdown = "Received offer from Meta for $150k base salary [1]."
citation = {
    "1": {
        "platform": "Gmail",
        "timestamp": "2024-03-25T09:00:00Z",
        "description": "Offer letter from Meta recruiter",
        "url": None,
        "quote": "We're offering $150k base salary"
    }
}
```

---

## Retrieval Integration

When displaying search results, the system can:

1. **Show content** with inline citations
2. **Expand citations** on hover or click
3. **Link to original sources** when URLs available
4. **Display quotes** for context

**Example UI:**

```
Job Search Progress

Applied to 200+ internships with no responses [1].
                                                 ↑ [hover]
                                                 
[Citation 1]
Platform: Gmail
Date: Jan-Mar 2024  
Source: Gmail analysis showing rejection emails from 180+ companies
```

---

## Migration Notes

### From Old Format (Footnotes)

If you have existing files with `[^1]` style footnotes:

```markdown
Old format [^1].

---

[^1]: Source info here
```

**Convert to:**

```markdown
Old format [1].
```

```json
{
  "1": {
    "platform": "Manual",
    "timestamp": "2024-10-25T00:00:00Z",
    "description": "Source info here",
    "url": null,
    "quote": null
  }
}
```

---

## Best Practices

1. **Keep citation numbers sequential** - Always use the next available number
2. **Be descriptive in descriptions** - Help future you understand the context
3. **Include quotes when relevant** - Preserve the exact wording
4. **Always use ISO 8601 timestamps** - Ensures consistency
5. **Null is okay** - Don't force URLs or quotes if they don't exist
6. **One citation per fact** - Don't overload single citations with multiple facts

---

## Future Enhancements

Potential improvements to consider:

- **Citation visualization**: Graph of source platforms over time
- **Source credibility scoring**: Weight citations by source type
- **Auto-linking**: Automatically link citations to original messages/emails
- **Citation search**: Find all content citing a specific source
- **Duplicate detection**: Identify redundant citations
- **Citation export**: Generate bibliography from JSON files
