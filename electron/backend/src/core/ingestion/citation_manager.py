#!/usr/bin/env python3
"""
Citation Manager - Manages JSON citation files
"""

from pathlib import Path
from typing import Dict
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.file_ops import read_json_citations, write_json_citations


class CitationManager:
    """Manages citation JSON files."""
    
    def add_citations(self, file_path: Path, new_citations: Dict) -> None:
        """
        Add new citations to file's JSON.
        
        Args:
            file_path: Path to markdown file
            new_citations: Dict of new citations to add {num: {platform, timestamp, url, quote}}
        """
        # Read existing citations
        existing = read_json_citations(file_path)
        
        # Merge with new citations
        existing.update(new_citations)
        
        # Write back
        write_json_citations(file_path, existing)
    
    def update_citation(self, file_path: Path, citation_num: str, metadata: Dict) -> None:
        """Update a specific citation."""
        citations = read_json_citations(file_path)
        citations[citation_num] = metadata
        write_json_citations(file_path, citations)
    
    def get_citations(self, file_path: Path) -> Dict:
        """Get all citations for a file."""
        return read_json_citations(file_path)
    
    def validate_citation(self, citation: Dict) -> bool:
        """
        Validate citation has required fields.
        
        Required: platform, timestamp, url, quote
        """
        required_fields = ['platform', 'timestamp', 'url', 'quote']
        return all(field in citation for field in required_fields)
    
    def clean_citations(self, citations: Dict) -> Dict:
        """
        Ensure all citations have proper format.
        
        Adds null for missing fields.
        """
        cleaned = {}
        for num, cit in citations.items():
            cleaned[num] = {
                'platform': cit.get('platform', 'Manual'),
                'timestamp': cit.get('timestamp', ''),
                'url': cit.get('url'),
                'quote': cit.get('quote')
            }
        return cleaned
