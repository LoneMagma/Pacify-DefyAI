"""
Code Detection and Formatting Utilities v-1.0.0
Handles proper formatting of code blocks, technical content, and markdown
"""

import re
from typing import Tuple, Optional, List


class CodeBlockDetector:
    """Detect and preserve code blocks in AI responses."""
    
    # Code indicators (language-agnostic patterns)
    CODE_PATTERNS = [
        r'(?:^|\n)(?:def|class|function|const|let|var|import|from|#include)\s+',
        r'(?:^|\n)(?:public|private|protected|static|async|await)\s+',
        r'[{}\[\]();]',  # Common code punctuation
        r'(?:^|\n)\s*//.*$',  # Comments
        r'(?:^|\n)\s*#.*$',
        r'(?:^|\n)\s*\*.*$',
        r'=>|->|::|!=|==|<=|>=',  # Operators
    ]
    
    # Language detection patterns
    LANGUAGE_PATTERNS = {
        'python': [r'\bdef\b', r'\bclass\b', r'\bimport\b', r'\bfrom\b', r':\s*$'],
        'javascript': [r'\bfunction\b', r'\bconst\b', r'\blet\b', r'=>', r'require\('],
        'java': [r'\bpublic\s+class\b', r'\bprivate\b', r'\bprotected\b', r'System\.out'],
        'c': [r'#include', r'\bint\s+main\b', r'printf\(', r'\bvoid\b'],
        'cpp': [r'#include', r'std::', r'cout\s*<<', r'\bnamespace\b'],
        'rust': [r'\bfn\b', r'\blet\s+mut\b', r'println!', r'\bimpl\b'],
        'go': [r'\bfunc\b', r'\bpackage\b', r':=', r'fmt\.'],
        'ruby': [r'\bend\b', r'\bdef\b', r'@\w+', r'puts\s'],
        'php': [r'<\?php', r'\$\w+', r'echo\s', r'function\s'],
        'html': [r'<[a-z]+', r'</[a-z]+>', r'<!DOCTYPE'],
        'css': [r'[.#]\w+\s*{', r':\s*\w+;', r'@media'],
        'sql': [r'\bSELECT\b', r'\bFROM\b', r'\bWHERE\b', r'\bINSERT\b'],
        'bash': [r'#!/bin/', r'\becho\b', r'\$\(', r'\[\['],
    }
    
    @classmethod
    def detect_code(cls, text: str) -> bool:
        """
        Check if text contains code-like patterns.
        
        Args:
            text: Text to analyze
        
        Returns:
            True if code detected
        """
        # Check for existing markdown code blocks
        if '```' in text:
            return True
        
        # Check for code patterns
        code_score = 0
        for pattern in cls.CODE_PATTERNS:
            if re.search(pattern, text, re.MULTILINE):
                code_score += 1
        
        # Threshold: 3+ code patterns = likely code
        return code_score >= 3
    
    @classmethod
    def detect_language(cls, code: str) -> str:
        """
        Detect programming language from code content.
        
        Args:
            code: Code snippet
        
        Returns:
            Language name or 'text'
        """
        scores = {}
        
        for lang, patterns in cls.LANGUAGE_PATTERNS.items():
            score = sum(1 for pattern in patterns if re.search(pattern, code, re.IGNORECASE))
            if score > 0:
                scores[lang] = score
        
        if scores:
            return max(scores, key=scores.get)
        
        return 'text'
    
    @classmethod
    def extract_code_blocks(cls, text: str) -> List[Tuple[str, str, str]]:
        """
        Extract existing markdown code blocks.
        
        Args:
            text: Text containing code blocks
        
        Returns:
            List of (language, code, full_block) tuples
        """
        pattern = r'```(\w*)\n(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)
        
        blocks = []
        for lang, code in matches:
            full_block = f'```{lang}\n{code}```'
            blocks.append((lang or 'text', code, full_block))
        
        return blocks
    
    @classmethod
    def wrap_code_blocks(cls, text: str) -> str:
        """
        Detect and wrap code sections in markdown blocks.
        
        Args:
            text: Raw text possibly containing code
        
        Returns:
            Text with code wrapped in ``` blocks
        """
        # Already has code blocks? Return as-is
        if '```' in text:
            return text
        
        # Check if entire response is code
        if cls.detect_code(text):
            lines = text.split('\n')
            
            # Find code sections (indented or starting with code keywords)
            code_sections = []
            current_section = []
            in_code = False
            
            for line in lines:
                is_code_line = (
                    line.strip() and (
                        line.startswith('    ') or  # Indented
                        line.startswith('\t') or
                        re.match(r'^\s*(?:def|class|function|const|let|var|import|from|#include)', line) or
                        re.search(r'[{}\[\]();]', line)
                    )
                )
                
                if is_code_line:
                    if not in_code:
                        in_code = True
                    current_section.append(line)
                else:
                    if in_code and current_section:
                        code_sections.append('\n'.join(current_section))
                        current_section = []
                        in_code = False
            
            # Don't forget last section
            if current_section:
                code_sections.append('\n'.join(current_section))
            
            # If we found code sections, wrap them
            if code_sections:
                result = text
                for section in code_sections:
                    lang = cls.detect_language(section)
                    wrapped = f'```{lang}\n{section}\n```'
                    result = result.replace(section, wrapped)
                return result
        
        return text


class ResponseFormatter:
    """Format AI responses for optimal display."""
    
    @staticmethod
    def format_for_cli(response: str) -> str:
        """
        Format response for CLI display with Rich.
        
        Args:
            response: Raw AI response
        
        Returns:
            Formatted response (markdown)
        """
        # Wrap code blocks if needed
        response = CodeBlockDetector.wrap_code_blocks(response)
        
        # Preserve code blocks from cleanup
        code_blocks = CodeBlockDetector.extract_code_blocks(response)
        placeholders = {}
        
        for i, (lang, code, full_block) in enumerate(code_blocks):
            placeholder = f"__CODE_BLOCK_{i}__"
            placeholders[placeholder] = full_block
            response = response.replace(full_block, placeholder)
        
        # Clean up non-code text
        response = response.strip()
        
        # Remove filler openings (only from non-code parts)
        fillers = [
            "ah,", "oh,", "well,", "hmm,", "so,", "indeed,",
            "i understand", "let me", "you know,", "to be honest,",
            "honestly,", "i think", "i believe"
        ]
        
        for filler in fillers:
            if response.lower().startswith(filler):
                response = response[len(filler):].strip()
                if response:
                    response = response[0].upper() + response[1:]
                break
        
        # Restore code blocks
        for placeholder, code_block in placeholders.items():
            response = response.replace(placeholder, code_block)
        
        # Clean excessive newlines (but preserve in code)
        parts = response.split('```')
        for i in range(0, len(parts), 2):  # Only clean non-code parts
            parts[i] = re.sub(r'\n{3,}', '\n\n', parts[i])
        
        response = '```'.join(parts)
        
        return response
    
    @staticmethod
    def format_for_web(response: str) -> str:
        """
        Format response for web display with Gradio.
        
        Args:
            response: Raw AI response
        
        Returns:
            Formatted response (markdown)
        """
        # Same as CLI but Gradio handles markdown rendering
        return ResponseFormatter.format_for_cli(response)
    
    @staticmethod
    def extract_metadata(response: str) -> Tuple[str, dict]:
        """
        Extract metadata markers from response.
        
        Args:
            response: AI response possibly with metadata
        
        Returns:
            (clean_response, metadata_dict)
        """
        metadata = {}
        
        # Look for metadata patterns (future enhancement)
        # For now, just return as-is
        
        return response, metadata


# Export main functions
__all__ = [
    'CodeBlockDetector',
    'ResponseFormatter',
]
