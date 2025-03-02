import os

def load_dsa_table():
    """Load DSA.bin and create lookup dictionary of (world_id, room_id): index"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dsa_path = os.path.join(script_dir, "DSA.bin")
    
    dsa_table = {}
    try:
        with open(dsa_path, 'rb') as f:
            # Skip 2 byte header
            f.seek(2)
            
            # Read pairs of bytes and calculate indices
            pos = 2  # Start after header
            while True:
                bytes_pair = f.read(2)
                if not bytes_pair or len(bytes_pair) < 2:
                    break
                    
                world_id = bytes_pair[0]
                room_id = bytes_pair[1]
                index = (pos - 2) // 2  # Calculate index based on position
                
                # Store in lookup table
                dsa_table[(world_id, room_id)] = index
                pos += 2
                
    except FileNotFoundError:
        print("Error: Could not find DSA.bin")
        return None
        
    return dsa_table

# Constants for code types
CODE_END = 0x0
CODE_SET = 0x1
CODE_DSA_DISABLE = 0x2
CODE_DSA_ENABLE = 0x3
CODE_DSA_LOST = 0x4
CODE_DSA_RESET = 0x5
CODE_BGMSET = 0x6
CODE_RESET_PROGRESS = 0x7
CODE_MENUFLAG = 0x8
CODE_RESET_MENUFLAG = 0x9
CODE_WORLDSTATE2 = 0xa
CODE_SECOND = 0xb
CODE_SET_PROGRESS = 0xc
CODE_SCENARIO = 0xd

# List of all instruction markers
INSTRUCTION_MARKERS = [
    "[END]",
    "[SKIP]",
    "World Map:",
    "Raise Progress:",
    "Lower Progress:",
    "Spawn ID Change:",
    "Block:",
    "Unblock:",
    "Remove Warp:",
    "Add Warp:",
    "BGM Set:",
    "Lower Menu:",
    "Raise Menu:"
]

def check_line_syntax(line, line_number):
    """
    Check the syntax of a line for valid instructions and formatting.
    Args:
        line: The line to check
        line_number: The line number for error reporting
    Raises:
        ValueError: If the line contains invalid syntax
    """
    if ':' in line:
        # Check if it's a Progress Flag Header (4 hex digits, optional text, followed by ':')
        is_progress_header = (len(line) >= 4 and 
                            all(c in '0123456789ABCDEFabcdef' for c in line[0:4]) and 
                            ':' in line[4:])
        
        # Split at the colon and check if the instruction part (with colon added back) is valid
        instruction_part = line.split(':')[0].strip() + ':'
        
        # Special cases for sub-instructions
        is_special_case = (
            instruction_part == "Text:" or  # Text values for Block commands
            instruction_part == "Room:" or  # Room values for Spawn ID Change
            (line.startswith("Room ") and len(line) >= 7 and line[5:7].isalnum())  # Room XX: format for Spawn ID Change
        )
        
        if not is_progress_header and not is_special_case and instruction_part not in INSTRUCTION_MARKERS:
            raise ValueError(f"Line {line_number}: Invalid instruction '{line}'.")
    else:
        # Check for common formatting errors in sub-instructions
        stripped_line = line.strip()
        if stripped_line.startswith('Text '):
            raise ValueError(f"Line {line_number}: Invalid Text instruction format. Must be 'Text: XXXX YYYY'")
        elif stripped_line.startswith('Room '):
            raise ValueError(f"Line {line_number}: Invalid Room instruction format. Must be 'Room XX: values'")

class Instruction:
    def __init__(self, type, count, data):
        self.type = type
        self.count = count
        self.data = data

def parse_menu_flags(lines, i, code_type):
    """Helper function to parse menu flags for both raise and lower operations"""
    menu_values = []
    next_pos = i + 1
    while next_pos < len(lines):
        next_line = lines[next_pos].split(';')[0].strip()
        if not next_line or next_line in INSTRUCTION_MARKERS:
            break
        
        parts = next_line.split()
        if parts:
            try:
                value = int(parts[0], 16)
                menu_values.append(value)
            except ValueError:
                print(f"Warning: Skipping invalid menu value: {parts[0]}")
        next_pos += 1
    
    return menu_values, next_pos

def parse_dsa_command(line, dsa_table, code_type, data_size=1):
    """Helper function to parse DSA-related commands"""
    parts = line.strip().split()
    if len(parts) >= 4 and parts[0] == "World" and parts[2] == "Room":
        try:
            # Validate World ID
            if not all(c in '0123456789ABCDEFabcdef' for c in parts[1]):
                raise ValueError(f"World ID '{parts[1]}' must be in hexadecimal")
            world_id = int(parts[1], 16)
            if world_id < 0 or world_id > 255:
                raise ValueError(f"World ID '{parts[1]}' must be an unsigned byte (0x00 to 0xFF)")
            
            # Validate Room ID
            if not all(c in '0123456789ABCDEFabcdef' for c in parts[3]):
                raise ValueError(f"Room ID '{parts[3]}' must be in hexadecimal")
            room_id = int(parts[3], 16)
            if room_id < 0 or room_id > 255:
                raise ValueError(f"Room ID '{parts[3]}' must be an unsigned byte (0x00 to 0xFF)")
            
            if dsa_table and (world_id, room_id) in dsa_table:
                index = dsa_table[(world_id, room_id)]
                result = bytearray([code_type, data_size, index & 0xFF, (index >> 8) & 0xFF])
                return result, 4  # Return data and size
            else:
                raise ValueError(f"World {world_id:02X} Room {room_id:02X} not found in DSA table")
                
        except ValueError as e:
            if any(msg in str(e) for msg in ["must be in hexadecimal", "must be an unsigned byte", "not found in DSA table"]):
                raise
            raise ValueError(f"Could not parse DSA command values: {line}")
    return None, 0

def parse_progress_flags(lines, i, code_type):
    """Helper function to parse progress flags for both raise and lower operations"""
    progress_count = 0
    next_pos = i + 1
    while next_pos < len(lines):
        next_line = lines[next_pos].split(';')[0].strip()
        if not next_line or next_line in INSTRUCTION_MARKERS:
            break
        progress_count += 1
        next_pos += 1
    
    result = bytearray([code_type, progress_count])
    offset = 2  # code + count
    
    for _ in range(progress_count):
        i += 1
        progress_line = lines[i].split(';')[0].strip()
        value = int(progress_line[0:4], 16)
        result.extend([value & 0xFF, (value >> 8) & 0xFF])
        offset += 2
    
    return result, offset, next_pos

def parse_instructions(text):
    dsa_table = load_dsa_table()
    lines = text.split("\n")
    
    # First pass: Count progress flags and store their positions
    progress_flags = []
    current_flag = None
    
    # Add line number tracking
    for i, line in enumerate(lines, 1):
        line = line.split(';')[0].strip()
        if not line:
            continue

        # Check line syntax
        check_line_syntax(line, i)
        
        # Check for progress flag header (existing code)
        if len(line) >= 4 and all(c in '0123456789ABCDEFabcdef' for c in line[0:4]) and ':' in line:
            current_flag = int(line[0:4], 16)
            progress_flags.append(current_flag)

    # Calculate header size (2 bytes per progress flag)
    header_size = len(progress_flags) * 2
    
    # Second pass: Generate data and track offsets
    data = bytearray()
    offsets = []
    current_offset = header_size
    
    i = 0
    while i < len(lines):
        # Remove comments and strip whitespace
        line = lines[i].split(';')[0].strip()
        
        # Skip empty lines
        if not line:
            i += 1
            continue
            
        # If line starts with a hex number, it's a new progress flag section
        if len(line) >= 4 and all(c in '0123456789ABCDEFabcdef' for c in line[0:4]):
            # Check if next non-empty line is [SKIP]
            next_line = ""
            next_pos = i + 1
            while next_pos < len(lines) and not next_line:
                next_line = lines[next_pos].split(';')[0].strip()
                if not next_line:
                    next_pos += 1
                    continue
                break
                
            if next_line == "[SKIP]":
                offsets.append(0)  # Add 0x0000 offset for skipped flags
                i = next_pos + 1  # Skip past the [SKIP] line
                continue
            
            offsets.append(current_offset)
            i += 1
            continue
            
        if line == "[END]":
            data.extend([CODE_END, 0])
            current_offset += 2
            i += 1
            continue
        
        if line.startswith("World Map:"):
            data_str = line[len("World Map:"):].strip()
            hex_vals = data_str.split()
            
            data.append(CODE_SCENARIO)
            data.append(1)  # Count is 1
            for hex_val in hex_vals:
                data.append(int(hex_val, 16))
                
            current_offset += 2 + len(hex_vals)  # code + count + data
            i += 1
            continue

        if line == "Raise Progress:":
            result, offset, next_pos = parse_progress_flags(lines, i, CODE_SET_PROGRESS)
            data.extend(result)
            current_offset += offset
            i = next_pos
            continue

        if line == "Lower Progress:":
            result, offset, next_pos = parse_progress_flags(lines, i, CODE_RESET_PROGRESS)
            data.extend(result)
            current_offset += offset
            i = next_pos
            continue

        if line == "Spawn ID Change:":
            spawn_count = 0
            next_pos = i + 1
            while next_pos < len(lines):
                next_line = lines[next_pos].split(';')[0].strip()
                if not next_line or next_line in INSTRUCTION_MARKERS:
                    break
                spawn_count += 4
                next_pos += 1
            
            data.append(CODE_SET)
            data.append(spawn_count)
            current_offset += 2  # code + count
            
            next_pos = i + 1
            while next_pos < len(lines):
                next_line = lines[next_pos].split(';')[0].strip()
                if not next_line or next_line in INSTRUCTION_MARKERS:
                    break
                
                spawn_line = next_line
                room_str = spawn_line[5:7]
                room_val = int(room_str, 16)
                data.append(room_val & 0xFF)
                data.append((room_val >> 8) & 0xFF)
                current_offset += 2
                
                numbers = spawn_line.split(':')[1].strip().split()
                for num in numbers:
                    if num == "-1":
                        data.extend([0xFF, 0xFF])
                    else:
                        try:
                            # Parse as hex if it's a hex string, otherwise as decimal
                            value = int(num, 16) if all(c in '0123456789ABCDEFabcdef' for c in num) else int(num)
                            if value < 0 or value > 255:
                                raise ValueError(f"Line {next_pos + 1}: Spawn ID value '{num}' must be an unsigned byte (0 to 255)")
                            data.append(value & 0xFF)
                            data.append(0)  # High byte is always 0 for spawn IDs
                        except ValueError as e:
                            if "must be an unsigned byte" in str(e):
                                raise
                            raise ValueError(f"Line {next_pos + 1}: Invalid spawn ID value: '{num}'")
                    current_offset += 2
                
                next_pos += 1
            i = next_pos - 1
            i += 1
            continue

        if line.startswith("Block:"):
            result, size = parse_dsa_command(line[6:], dsa_table, CODE_DSA_DISABLE, 3)
            if result:
                data.extend(result)
                # Handle text values if present
                text_line = lines[i + 1].split(';')[0].strip() if i + 1 < len(lines) else ""
                if text_line.startswith("Text:"):
                    text_parts = text_line[5:].strip().split()
                    # Validate we have exactly two text values
                    if len(text_parts) != 2:
                        raise ValueError(f"Line {i + 2}: Text instruction requires exactly 2 text strings, found {len(text_parts)}")
                    
                    try:
                        # Try to parse each value as a hex number
                        text_values = []
                        for text_id in text_parts:
                            if not all(c in '0123456789ABCDEFabcdef' for c in text_id):
                                raise ValueError(f"Line {i + 2}: Text string '{text_id}' must be in hexidecimal.")
                            value = int(text_id, 16) + 0x8000
                            if value > 0xFFFF:
                                raise ValueError(f"Line {i + 2}: Text string '{text_id}' must fit an unsigned short (0x0000 to 0x7FFF)")
                            text_values.append(value)
                        
                        # Add the validated values
                        for value in text_values:
                            data.append(value & 0xFF)
                            data.append((value >> 8) & 0xFF)
                        size += 4
                        i += 1
                    except ValueError as e:
                        if "must be in hexidecimal" in str(e) or "must fit an unsigned short" in str(e):
                            raise
                        raise ValueError(f"Line {i + 2}: Invalid text value format")
                    
                current_offset += size
            i += 1
            continue

        if line.startswith("Unblock:"):
            result, size = parse_dsa_command(line[8:], dsa_table, CODE_DSA_ENABLE)
            if result:
                data.extend(result)
                current_offset += size
            i += 1
            continue

        if line.startswith("Remove Warp:"):
            result, size = parse_dsa_command(line[12:], dsa_table, CODE_DSA_RESET)
            if result:
                data.extend(result)
                current_offset += size
            i += 1
            continue

        if line.startswith("Add Warp:"):
            result, size = parse_dsa_command(line[10:], dsa_table, CODE_DSA_LOST)
            if result:
                data.extend(result)
                current_offset += size
            i += 1
            continue

        if line.startswith("BGM Set:"):
            value_str = line[8:].strip().split(';')[0].strip()
            try:
                value = int(value_str)
                
                data.append(CODE_BGMSET)
                data.append(1)
                data.append(value & 0xFF)
                data.append((value >> 8) & 0xFF)
                current_offset += 4  # code + count + value
            except ValueError:
                print(f"Warning: Could not parse BGM Set value: {line}")
            i += 1
            continue

        if line.startswith("Raise Menu:"):
            menu_values, next_pos = parse_menu_flags(lines, i, CODE_MENUFLAG)
            data.append(CODE_MENUFLAG)
            data.append(len(menu_values))
            current_offset += 2
            
            for value in menu_values:
                data.append(value)
                data.append(0)
                current_offset += 2
            
            i = next_pos
            continue

        if line.startswith("Lower Menu:"):
            menu_values, next_pos = parse_menu_flags(lines, i, CODE_RESET_MENUFLAG)
            data.append(CODE_RESET_MENUFLAG)
            data.append(len(menu_values))
            current_offset += 2
            
            for value in menu_values:
                data.append(value)
                data.append(0)
                current_offset += 2
            
            i = next_pos
            continue

        i += 1
    
    # Combine header and data
    header = bytearray()
    for offset in offsets:
        header.append(offset & 0xFF)         # Low byte
        header.append((offset >> 8) & 0xFF)  # High byte
    
    return bytes(header + data)

def process_file(filepath):
    with open(filepath, 'r') as f:
        text = f.read()
    binary_data = parse_instructions(text)
    
    # Save the binary data to a .bin file
    output_path = filepath.rsplit('.', 1)[0] + '.bin'
    with open(output_path, 'wb') as f:
        f.write(binary_data)
    
    return binary_data

if __name__ == "__main__":
    import sys
    import argparse
    
    # Create argument parser
    parser = argparse.ArgumentParser(description='Process KH2 progress flag files.')
    parser.add_argument('files', nargs='*', help='Text files to process')
    parser.add_argument('--cli', action='store_true', help='Run in command line mode (no input prompts)')
    
    args = parser.parse_args()
    
    try:
        # Check if files were provided
        if not args.files:
            if not args.cli:
                print("Please drag a text file onto this script to process it.")
                input("Press Enter to exit...")
            sys.exit(1)
        
        success = True
        # Process each file that was provided
        for filepath in args.files:
            try:
                print(f"Processing file: {filepath}")  # Debug output
                binary_data = process_file(filepath)
                print(f"Successfully processed {filepath}")
                print(f"Output saved to {filepath.rsplit('.', 1)[0] + '.bin'}")
            except Exception as e:
                success = False
                print(f"Error processing {filepath}: {str(e)}")
                print("Full error details:")
                import traceback
                traceback.print_exc()
    
    except Exception as e:
        success = False
        print(f"An unexpected error occurred: {str(e)}")
        print("Full error details:")
        import traceback
        traceback.print_exc()
    
    finally:
        # Only show "Press Enter to exit" if not in CLI mode
        if not args.cli:
            if not success:
                print("\nErrors occurred during processing.")