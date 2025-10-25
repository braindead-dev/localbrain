# Ingestion Engine

Processes and stores new documents and data into the LocalBrain system. Responsible for intelligent extraction of insights, observations, and maintaining the structured filesystem.

## Core Responsibilities

- **Document Processing**: Ingest and parse various file formats
- **Content Chunking**: Split documents into searchable segments
- **Embedding Generation**: Create vector representations for semantic search
- **Insight Extraction**: Identify key observations and patterns
- **Source Citation Management**: Track and link supporting evidence
- **File Structure Management**: Maintain standardized markdown format

## Guardrails & Security

**Sensitive Data Protection:**
- Automatic detection and filtering of passwords, SSNs, credit cards
- Pattern-based recognition of sensitive information
- Sanitization before storage and processing
- Configurable filtering rules

**Data Quality:**
- Content validation and cleaning
- Duplicate detection and merging
- Metadata extraction and validation
- Error handling and recovery

## Document Processing Pipeline

1. **Input Reception**: Accept data from connectors or direct upload
2. **Format Detection**: Identify file type and structure
3. **Content Extraction**: Parse and clean document content
4. **Security Filtering**: Remove sensitive information
5. **Chunking Strategy**: Split into optimal search segments
6. **Embedding Generation**: Create vector representations
7. **Metadata Creation**: Extract and store file/source metadata
8. **Storage**: Save chunks, embeddings, and metadata to database

## Markdown File Structure

**File Format:**
- **Filename as Title**: `job-search.md` (no YAML frontmatter needed)
- **Purpose Summary**: Opening paragraph explaining file content
- **Content Sections**: Organized by topic/theme
- **Numbered Citations**: Inline `[1]` references with separate JSON metadata file
- **Related Topics**: Wiki-style `[[links]]` to other files

**Example Structure:**

**filename.md:**
```markdown
# filename

Purpose summary paragraph explaining what this file contains.

## Main Section

Content with factual claims cited inline [1]. Observations and 
insights that connect multiple sources [2].

## Related Topics

- [[related-file]]
- [[another-topic]]
```

**filename.json:**
```json
{
  "1": {
    "platform": "Gmail",
    "timestamp": "2024-03-15T10:30:00Z",
    "url": null,
    "quote": "The deadline has been moved to April 1st"
  },
  "2": {
    "platform": "Discord",
    "timestamp": "2024-03-20T14:00:00Z",
    "url": "https://discord.com/channels/...",
    "quote": null
  }
}
```

**Citation Guidelines:**
- **Cite factual claims**: Numbers, dates, quotes, specific events
- **Don't cite everything**: General observations and opinions don't need sources
- **Format**: `[1]` inline in markdown, metadata in JSON file
- **JSON fields** (4 only): platform, timestamp, url (nullable), quote (nullable)

**Auto-Initialization:**
- Files created with purpose summary
- Structure follows template
- Citations added automatically from source metadata
- Manual editing allowed and preserved

## Integration Points

- **Connectors**: Receive data from external sources
- **Frontend**: Accept direct file uploads and quick notes
- **Retrieval**: Provide processed content for search indexing
- **Filesystem**: Create and manage `.localbrain/` directory structure

## File Modification Agent

**Architecture:**
The file modification agent works like a modern coding agent (Cursor, Copilot, etc.), making surgical edits to markdown files without breaking existing content.

**How It Works:**
1. **File Analysis**: Read entire file, understand structure and sections
2. **Context Matching**: Determine which section(s) need updates
3. **Diff Generation**: Create precise edit operations for specific lines
4. **Validation**: Ensure edits maintain file structure and formatting
5. **Application**: Apply edits and verify file integrity
6. **Re-indexing**: Trigger re-chunking and re-embedding for updated content

**Edit Operations:**
- **Append to Section**: Add new insights to existing section
- **Update Line**: Modify specific claim or observation
- **Add Citation**: Insert footnote reference and source
- **Create Section**: Add new section if topic is distinct
- **Merge Related**: Combine similar observations

**Example Operation:**
```python
# Input: New context
context = "Received offer from Startup X for $120k"
source_metadata = {
    "platform": "Gmail",
    "timestamp": "2024-03-15T09:00:00Z",
    "url": None,
    "quote": "We're pleased to offer you $120k base salary"
}

# Agent analyzes job-search.md
# Determines this is a positive outcome in job search
# Appends to relevant section with citation

# Output: Surgical edit
insert_after_line(23, "Received offer from Startup X for $120k base salary [4].")

# Update job-search.json
update_json_file("job-search.json", citation_num=4, metadata=source_metadata)
```

**Conflict Avoidance:**
- Read-modify-write locks prevent concurrent edits
- Validation checks before applying changes
- Rollback capability if edit fails
- Version tracking for recovery

## Ingestion System Prompts

**Primary Ingestion Prompt:**
```
You are a personal context curator for a filesystem-based knowledge bank. 

Your role is to process incoming information and organize it into a structured markdown filesystem. This is someone's entire life context - emails, messages, documents, observations - organized for intelligent retrieval.

ORGANIZATION PRINCIPLES:
1. One topic per file - keep files focused and coherent
2. Create new files for distinct topics, append to existing files for related context
3. Use descriptive filenames: job-search.md, not notes.md
4. Organize into logical directories: career/, personal/, research/, projects/
5. Link related topics using [[wiki-style-links]]

FILE STRUCTURE:
- Start with purpose summary (what this file is about)
- Main content in ## sections
- Factual claims need citations [1], [2], etc.
- Separate .json file with citation metadata
- Related topics section for cross-references

CITATION RULES:
- Cite factual claims: numbers, dates, quotes, decisions
- Don't cite: opinions, observations, general knowledge
- Format: [n] inline in markdown
- JSON metadata (4 fields): platform, timestamp, url, quote

WHEN TO CREATE NEW FILES:
- Topic is distinct from existing files
- Would require multiple new sections in existing file
- Different domain/category than current files

WHEN TO APPEND TO EXISTING:
- Topic directly relates to existing file
- Adds context or updates to existing observations
- Same domain/category

Extract key insights, maintain context, preserve sources.
```

**File Selection Prompt:**
```
Given this context and the existing filesystem, determine:
1. Should this create a new file or append to existing?
2. If appending, which file(s) and which section(s)?
3. If creating, what should the filename and directory be?

Existing files: {file_list}
New context: {context}

Return: {action: "create"|"append", target: "path/filename.md", section: "section_name"}
```

**Content Extraction Prompt:**
```
Extract structured information from this context:

1. Key facts and observations (with inline citation markers like [1])
2. Source metadata (platform, timestamp, url, quote)
3. Related topics for linking
4. Suggested file section (if appending)

Output:
- Markdown content with [n] citations
- JSON object with citation metadata (4 fields only)
```

## Configuration

- **Chunking Parameters**: Configurable segment sizes and overlap
- **Embedding Models**: Selectable vectorization strategies
- **Processing Rules**: Customizable content filtering and extraction
- **Storage Options**: Database selection and configuration
- **Agent Settings**: LLM model, temperature, max tokens for file modification

## V3 Enhancements (OpenCode-Inspired)

The ingestion pipeline has been significantly improved by adopting techniques from OpenCode:

### 1. Fuzzy Matching (`utils/fuzzy_matcher.py`)
- **Levenshtein distance** algorithm for string similarity
- Section name fuzzy matching (threshold: 0.6)
- Handles LLM naming variations: "Applications" → "Job Applications"
- File name similarity matching for better file selection

### 2. Validation Feedback Loop
- **MarkdownValidator** checks file structure after edits
- Validates: titles, sections, citations, JSON metadata
- Errors fed back to LLM for correction
- Retry mechanism (max 3 attempts)

### 3. Anthropic-Optimized Prompts
- Concise tone enforcement: "No explanations, just JSON"
- Examples showing desired behavior
- Negative instructions: "❌ Don't create files when existing fits"
- Behavioral constraints matching OpenCode's anthropic.txt

### 4. Retry Loop Architecture
```python
for attempt in range(max_retries):
    result = ingest_attempt(context)
    errors = validate_files(result)
    
    if not errors:
        return success
    
    # Feed errors back to LLM
    context = create_retry_context(context, errors)
```

### Usage

**V3 Pipeline (Recommended):**
```bash
python agentic_ingest_v3.py ~/my-vault "Email from recruiter: Offer $150k"
```

**With source metadata:**
```bash
python agentic_ingest_v3.py ~/my-vault "Interview feedback" \
  '{"platform": "Gmail", "timestamp": "2024-10-25T10:30:00Z"}'
```

### Performance Improvements

- **Fewer LLM errors** due to fuzzy matching
- **Self-correcting** through validation loops
- **Higher accuracy** with Anthropic-style prompts
- **Faster iteration** with targeted error feedback
