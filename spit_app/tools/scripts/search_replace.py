import sys
import re
from pathlib import Path

try:
    path = Path(path)
    if not path.exists():
        print(f"ERROR: Path does not exist: `{path}`")
        sys.exit(1)
    
    if not path.is_file():
        print(f"ERROR: Path is not a file: `{path}`")
        sys.exit(1)
    
    # Read the file
    content = path.read_text(encoding='utf-8')
    
    # Find matches and perform replacements
    if use_regex:
        pattern = re.compile(find)
        matches = list(pattern.finditer(content))
        num_matches = len(matches)
    else:
        # Plain text search
        matches = []
        start = 0
        while True:
            idx = content.find(find, start)
            if idx == -1:
                break
            matches.append((idx, idx + len(find)))
            start = idx + 1
        num_matches = len(matches)
    
    if num_matches == 0:
        print(f"No matches found for `{find}` in `{path}`.")
        sys.exit(0)
    
    max_matches = num_matches
    if not max_replacements == 0:
        if num_matches > max_replacements:
            max_matches = max_replacements

    # Preview changes if requested
    if preview or dry_run:
        print(f"Showing {max_matches} replacements(s) for `{find}` in `{path}`.")
        print("")
        print("Preview:")
        print("```")
        
        # Show context around each match
        context_lines = 3
        
        for i, match in enumerate(matches[:max_matches]):
            # Get start and end indices
            if isinstance(match, tuple):
                start_idx, end_idx = match
            else:
                start_idx = match.start()
                end_idx = match.end()
            
            # Get line number
            line_num = content[:start_idx].count('\n') + 1
            
            # Get surrounding context
            lines = content.split('\n')
            line_start = content.rfind('\n', 0, start_idx) + 1
            if line_start == 0:
                line_start = 0
            line_end = content.find('\n', end_idx)
            if line_end == -1:
                line_end = len(content)
            
            line_text = content[line_start:line_end]
            
            # Highlight the match
            match_start_in_line = start_idx - line_start
            match_end_in_line = end_idx - line_start
            
            if match_start_in_line >= 0 and match_end_in_line <= len(line_text):
                highlighted = (
                    line_text[:match_start_in_line] +
                    "[" + line_text[match_start_in_line:match_end_in_line] + "]" +
                    line_text[match_end_in_line:]
                )
            else:
                highlighted = line_text
            
            print(f"Line {line_num}: {highlighted}")
            
        # Show replacement preview
        print("")
        print(f"Replacement: `{replace}`")
        print("```")
        print("")
        if dry_run:
            print("dry_run: No changes made!")
            sys.exit(0)
    
    # Perform replacements
    if use_regex:
        new_content, num_replaced = pattern.subn(replace, content, count=max_matches)
    else:
        new_content = content
        num_replaced = max_matches
        count = 0
        for start_idx, end_idx in matches[:max_matches]:
            offset = count * (len(find) - len(replace))
            new_content = new_content[:start_idx-offset] + replace + new_content[end_idx-offset:]
            count += 1
    
    # Write the file back
    path.write_text(new_content, encoding='utf-8')
    
    print(f"Replaced {num_replaced} of {num_matches} match(es) in `{path}`.")

except Exception as exception:
    print(f"ERROR: `{type(exception).__name__}`: `{exception}`")
    sys.exit(1)
