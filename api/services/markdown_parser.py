"""
Markdown parser service for extracting semantic entities.

Parses markdown content looking for entity markers like:
- REQ: A requirement statement
- INSTR: An instruction to follow
- NOTE: A note to remember
- etc.
"""

import re
from typing import List, Optional, Tuple
from dataclasses import dataclass

from api.schemas.orm.entity import EntityType


@dataclass
class ParsedEntity:
    """A semantic entity parsed from markdown."""
    entity_type: EntityType
    title: str
    description: str
    source_text: str
    source_line: int
    tags: List[str]
    priority: Optional[int]


class MarkdownParser:
    """
    Parser for extracting semantic entities from markdown content.
    
    Supported formats:
    
    Inline markers (single line):
        REQ: User must be able to login
        INSTR: Run `npm install` to set up
        NOTE: Client prefers dark mode
    
    Block markers (multi-line):
        REQ: User Authentication
        The system must support email/password authentication
        with optional 2FA support.
        ---
    
    With priority:
        REQ[P1]: Critical security requirement
        TODO[P3]: Nice to have feature
    
    With tags:
        REQ #auth #security: User passwords must be hashed
    """
    
    # Pattern for entity markers
    # Matches: TYPE[Pn] #tag1 #tag2: content
    ENTITY_PATTERN = re.compile(
        r'^(?P<type>REQ|INSTR|DEC|Q|ASSUME|CONST|RISK|TODO|NOTE)'
        r'(?:\[P(?P<priority>[1-5])\])?'  # Optional priority [P1-P5]
        r'(?P<tags>(?:\s+#\w+)*)'          # Optional tags
        r':\s*(?P<content>.+)$',
        re.MULTILINE
    )
    
    # Pattern for block end marker
    BLOCK_END = re.compile(r'^---\s*$', re.MULTILINE)
    
    def __init__(self):
        self.entity_type_map = {
            "REQ": EntityType.REQUIREMENT,
            "INSTR": EntityType.INSTRUCTION,
            "DEC": EntityType.DECISION,
            "Q": EntityType.QUESTION,
            "ASSUME": EntityType.ASSUMPTION,
            "CONST": EntityType.CONSTRAINT,
            "RISK": EntityType.RISK,
            "TODO": EntityType.TODO,
            "NOTE": EntityType.NOTE,
        }
    
    def parse(self, content: str) -> List[ParsedEntity]:
        """
        Parse markdown content and extract all semantic entities.
        
        Args:
            content: Markdown content to parse
            
        Returns:
            List of ParsedEntity objects
        """
        entities = []
        lines = content.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i]
            match = self.ENTITY_PATTERN.match(line.strip())
            
            if match:
                entity_type = self.entity_type_map[match.group('type')]
                priority_str = match.group('priority')
                priority = int(priority_str) if priority_str else None
                tags = [t.strip('#') for t in match.group('tags').split() if t.startswith('#')]
                first_line_content = match.group('content').strip()
                
                # Check if this is a block (has content on following lines before ---)
                block_content, block_end_line = self._extract_block(lines, i + 1)
                
                if block_content:
                    # Block format: first line is title, rest is description
                    title = first_line_content
                    description = block_content
                    source_text = '\n'.join(lines[i:block_end_line + 1])
                    i = block_end_line + 1
                else:
                    # Single line format
                    title = first_line_content
                    description = first_line_content
                    source_text = line
                    i += 1
                
                entities.append(ParsedEntity(
                    entity_type=entity_type,
                    title=self._truncate(title, 100),
                    description=description,
                    source_text=source_text,
                    source_line=i,
                    tags=tags,
                    priority=priority,
                ))
            else:
                i += 1
        
        return entities
    
    def _extract_block(self, lines: List[str], start_idx: int) -> Tuple[str, int]:
        """
        Extract multi-line block content until --- marker.
        
        Returns:
            Tuple of (block_content, end_line_index) or ("", start_idx) if no block
        """
        content_lines = []
        i = start_idx
        
        while i < len(lines):
            line = lines[i]
            
            # Check for block end
            if self.BLOCK_END.match(line):
                if content_lines:
                    return '\n'.join(content_lines).strip(), i
                return "", start_idx
            
            # Check if we hit another entity marker (end of implicit block)
            if self.ENTITY_PATTERN.match(line.strip()):
                if content_lines:
                    return '\n'.join(content_lines).strip(), i - 1
                return "", start_idx
            
            # Empty line after content might end implicit block
            if not line.strip() and content_lines:
                # Look ahead - if next non-empty line is an entity, end here
                for j in range(i + 1, min(i + 3, len(lines))):
                    if lines[j].strip():
                        if self.ENTITY_PATTERN.match(lines[j].strip()):
                            return '\n'.join(content_lines).strip(), i - 1
                        break
            
            content_lines.append(line)
            i += 1
        
        # End of file
        if content_lines:
            return '\n'.join(content_lines).strip(), i - 1
        return "", start_idx
    
    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text to max_length, adding ellipsis if needed."""
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."
    
    def extract_entities_from_conversation(
        self,
        messages: List[dict],
    ) -> List[ParsedEntity]:
        """
        Extract entities from a list of conversation messages.
        
        Args:
            messages: List of message dicts with 'content' key
            
        Returns:
            List of ParsedEntity objects
        """
        all_entities = []
        
        for msg in messages:
            content = msg.get('content', '')
            entities = self.parse(content)
            all_entities.extend(entities)
        
        return all_entities


# Singleton instance
markdown_parser = MarkdownParser()
