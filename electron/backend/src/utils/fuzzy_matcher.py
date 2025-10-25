#!/usr/bin/env python3
"""
Fuzzy Matcher - Port of OpenCode's fuzzy matching logic for LocalBrain

Handles LLM imperfection in section names and content matching using
Levenshtein distance and similarity thresholds.
"""

from typing import Optional


def levenshtein(a: str, b: str) -> int:
    """
    Calculate Levenshtein distance between two strings.
    
    Port from OpenCode's edit.ts implementation.
    """
    if not a or not b:
        return max(len(a), len(b))
    
    # Create matrix
    matrix = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    
    # Initialize first row and column
    for i in range(len(a) + 1):
        matrix[i][0] = i
    for j in range(len(b) + 1):
        matrix[0][j] = j
    
    # Fill matrix
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            matrix[i][j] = min(
                matrix[i - 1][j] + 1,      # Deletion
                matrix[i][j - 1] + 1,      # Insertion
                matrix[i - 1][j - 1] + cost  # Substitution
            )
    
    return matrix[len(a)][len(b)]


def find_best_section_match(
    content: str,
    target_section: str,
    threshold: float = 0.6
) -> Optional[str]:
    """
    Find best matching section in markdown content.
    
    Args:
        content: Full markdown file content
        target_section: Section name LLM wants to target
        threshold: Minimum similarity score (0.0-1.0)
    
    Returns:
        Actual section name from file, or None if no match
    
    Examples:
        >>> content = "## Job Applications\\n...\\n## Interview Prep\\n..."
        >>> find_best_section_match(content, "Applications")
        "Job Applications"
        
        >>> find_best_section_match(content, "Interviews")
        "Interview Prep"
    """
    lines = content.split('\n')
    sections = [line for line in lines if line.startswith('##')]
    
    if not sections:
        return None
    
    # Try exact substring match first (case-insensitive)
    target_lower = target_section.lower()
    for section in sections:
        section_text = section.replace('##', '').strip()
        if target_lower in section_text.lower() or section_text.lower() in target_lower:
            return section_text
    
    # Fuzzy match using Levenshtein distance
    best_match = None
    best_similarity = 0.0
    
    for section in sections:
        section_name = section.replace('##', '').strip()
        
        # Calculate similarity
        distance = levenshtein(target_section.lower(), section_name.lower())
        max_len = max(len(target_section), len(section_name))
        similarity = 1 - (distance / max_len) if max_len > 0 else 0
        
        if similarity > best_similarity:
            best_similarity = similarity
            best_match = section_name
    
    if best_similarity >= threshold:
        return best_match
    
    return None


def find_similar_filename(
    vault_path,
    target_filename: str,
    threshold: float = 0.7
) -> Optional[str]:
    """
    Find similar filename in vault using fuzzy matching.
    
    Helps when LLM references "job-search" but file is "job_search.md"
    or "Job Search.md".
    """
    from pathlib import Path
    from .file_ops import list_vault_files
    
    existing_files = list_vault_files(vault_path, include_about=False)
    
    if not existing_files:
        return None
    
    # Normalize target
    target_normalized = target_filename.lower().replace('_', ' ').replace('-', ' ')
    
    best_match = None
    best_similarity = 0.0
    
    for file_info in existing_files:
        file_stem = Path(file_info['relative_path']).stem
        file_normalized = file_stem.lower().replace('_', ' ').replace('-', ' ')
        
        # Calculate similarity
        distance = levenshtein(target_normalized, file_normalized)
        max_len = max(len(target_normalized), len(file_normalized))
        similarity = 1 - (distance / max_len) if max_len > 0 else 0
        
        if similarity > best_similarity:
            best_similarity = similarity
            best_match = file_info['relative_path']
    
    if best_similarity >= threshold:
        return best_match
    
    return None
