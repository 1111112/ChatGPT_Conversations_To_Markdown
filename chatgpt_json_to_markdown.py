import json
import os
import sys
import glob
import pprint
from datetime import datetime
from tqdm import tqdm
import re

# Set to True to enable detailed structure debugging
DEBUG_MODE = True
# Number of entries to print detailed structure for when debugging
DEBUG_ENTRIES = 1
# Enable to print details about dates for debugging date filtering
DEBUG_DATES = True

def read_json_file(file_path, max_file_size_mb=100):
    """Read and parse JSON file with error handling."""
    try:
        # Check file size before attempting to read
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > max_file_size_mb:
            print(f"Warning: File {file_path} is {file_size_mb:.2f}MB, which exceeds the default limit of {max_file_size_mb}MB.")
            response = input(f"Do you want to continue reading this file? (y/n): ")
            if response.lower() != 'y':
                print(f"Skipping file {file_path} due to size.")
                return None
                
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            if DEBUG_MODE:
                print(f"\nFile structure analysis for {os.path.basename(file_path)}:")
                if isinstance(data, list):
                    print(f"- Contains a list with {len(data)} entries")
                    if data and len(data) > 0 and DEBUG_ENTRIES > 0:
                        print(f"- First entry keys: {list(data[0].keys()) if isinstance(data[0], dict) else type(data[0])}")
                        print("- Structure of first entry:")
                        pprint.pprint(data[0], depth=2, compact=True)
                else:
                    print(f"- Contains a dictionary with keys: {list(data.keys())}")
            return data
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON in {file_path}: {e}")
        return None
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None

def dump_structure(obj, name="object", max_depth=3):
    """Helper to analyze structure of an object"""
    if obj is None:
        print(f"{name} is None")
        return
        
    if isinstance(obj, dict):
        print(f"{name} is a dict with keys: {list(obj.keys())}")
        if max_depth > 0:
            for key, value in obj.items():
                dump_structure(value, f"{name}['{key}']", max_depth-1)
    elif isinstance(obj, list):
        print(f"{name} is a list with {len(obj)} items")
        if len(obj) > 0 and max_depth > 0:
            dump_structure(obj[0], f"{name}[0]", max_depth-1)
    else:
        print(f"{name} is {type(obj)}: {obj if len(str(obj)) < 100 else str(obj)[:100]+'...'}")

def extract_messages_safely(entry):
    """Extract messages from various possible entry structures"""
    if not isinstance(entry, dict):
        return []
        
    # Try different known structures to extract messages
    # 1. Standard structure with mapping
    if "mapping" in entry:
        mapping = entry.get("mapping", {})
        if not mapping:
            return []
            
        messages = []
        for item_id, item in mapping.items():
            if isinstance(item, dict) and "message" in item:
                message = item.get("message")
                if message:
                    messages.append(message)
        return messages
        
    # 2. Direct message list
    if "messages" in entry:
        messages = entry.get("messages", [])
        return [msg for msg in messages if msg]
        
    # 3. Other possible structures can be added here
    
    # If we reach here, couldn't extract messages from known structures
    if DEBUG_MODE:
        print("Unknown entry structure, available keys:", list(entry.keys()))
    return []

def _get_message_content(message):
    """Extract content from message with comprehensive format handling."""
    try:
        if not message or not isinstance(message, dict):
            return ""
            
        if "content" not in message:
            # Try alternative fields that might contain content
            for field in ["text", "value", "body"]:
                if field in message:
                    return str(message[field])
            return ""
            
        content = message["content"]
        
        # Handle different content structures
        if isinstance(content, str):
            return content
            
        elif isinstance(content, dict):
            # Handle various dictionary formats
            if "parts" in content:
                parts = content["parts"]
                # Extract and join text content from parts
                return "\n".join(
                    part["text"] if isinstance(part, dict) and "text" in part else str(part) 
                    for part in parts if part
                )
            elif "text" in content:
                return content["text"]
            elif "result" in content:
                return content["result"]
            elif "content_type" in content:
                # Handle content_type variations
                if content["content_type"] == "user_editable_context":
                    return content.get("user_profile", "Context information (no details available)")
                else:
                    return f"Content of type: {content['content_type']}"
            else:
                # Try to extract any string content from the dict
                text_fields = [v for k, v in content.items() if isinstance(v, str) and len(v) > 0]
                if text_fields:
                    return "\n".join(text_fields)
                return f"[Message content in unknown format]"
        
        # Handle list format
        elif isinstance(content, list):
            return "\n".join(str(item) for item in content if item)
            
        # Fall back to string representation
        return str(content)
            
    except Exception as e:
        if DEBUG_MODE:
            print(f"Error extracting message content: {e}")
            dump_structure(message, "message with error")
        return "[Content extraction error]"

def get_author_role_safely(message):
    """Safely extract author role from various possible message structures"""
    if not isinstance(message, dict):
        return "unknown"
        
    # Try standard path
    if "author" in message and isinstance(message["author"], dict):
        return message["author"].get("role", "unknown")
        
    # Try direct fields
    if "role" in message:
        return message["role"]
        
    # More alternatives can be added
        
    return "unknown"

def get_create_time_safely(message):
    """Safely extract creation time from various possible message structures"""
    if not isinstance(message, dict):
        return None
        
    # Try standard field
    if "create_time" in message:
        value = message.get("create_time")
        if isinstance(value, (int, float)) and value > 0:
            return value
        
    # Try alternatives
    for field in ["timestamp", "time", "created_at", "date"]:
        if field in message:
            value = message.get(field)
            if isinstance(value, (int, float)) and value > 0:
                return value
            elif isinstance(value, str):
                # Try to parse ISO format date string
                try:
                    from dateutil import parser
                    dt = parser.parse(value)
                    return dt.timestamp()
                except (ImportError, ValueError):
                    pass
                
    return None

def _get_title(title, first_message=None, create_time=None):
    """Generate a title for the conversation with date prefix if available."""
    if not title or title.strip() == "":
        # Try to extract a title from the first message if available
        if first_message and isinstance(first_message, dict):
            content = _get_message_content(first_message)
            # Use the first line or first few words as fallback title
            if content:
                first_line = content.split('\n')[0][:50]
                title = first_line if len(first_line) > 3 else "Untitled Conversation"
            else:
                title = "Untitled Conversation"
        else:
            title = "Untitled Conversation"
    
    return title

def process_conversations(data, output_dir, config):
    """Process all conversations with improved handling."""
    processed = 0
    skipped = 0
    skipped_old = 0
    filter_before_year = config.get('filter_before_year', 2025)
    
    for entry in tqdm(data, desc="Processing conversations"):
        try:
            # Skip non-dict entries
            if not isinstance(entry, dict):
                print(f"Skipping entry, expected dict but got {type(entry).__name__}")
                skipped += 1
                continue

            # Get conversation metadata
            title = entry.get("title", "")
            mapping = entry.get("mapping", {})
            conversation_id = entry.get("id", "unknown")
            
            # Get conversation creation time
            conversation_create_time = entry.get("create_time")
            update_time = entry.get("update_time")
            
            # Check conversation creation time format
            if isinstance(conversation_create_time, str):
                try:
                    from dateutil import parser
                    conversation_create_time = parser.parse(conversation_create_time).timestamp()
                except (ImportError, ValueError):
                    if DEBUG_DATES:
                        print(f"Failed to parse conversation create_time string: {conversation_create_time}")
                    conversation_create_time = None
            
            # Filter by conversation date early if possible
            if conversation_create_time and isinstance(conversation_create_time, (int, float)) and conversation_create_time > 0:
                conversation_year = datetime.fromtimestamp(conversation_create_time).year
                if conversation_year < filter_before_year:
                    if DEBUG_DATES:
                        print(f"Skipping conversation from {conversation_year} (before {filter_before_year}): {title}")
                    skipped_old += 1
                    continue
            
            # Skip if mapping is missing or empty
            if not mapping:
                print(f"Skipping entry with no mapping data, title: {title}")
                skipped += 1
                continue

            # Extract and sort messages
            messages = []
            for item_id, item in mapping.items():
                if not isinstance(item, dict) or "message" not in item:
                    continue
                
                message = item.get("message")
                if message is None:
                    continue
                
                # Ensure message has required fields to prevent NoneType errors
                if not isinstance(message, dict):
                    continue
                    
                if "author" not in message or not isinstance(message.get("author"), dict):
                    message["author"] = {"role": "unknown"}
                    
                messages.append(message)
            
            # Skip if no messages found
            if not messages:
                print(f"Skipping entry with no messages, title: {title}")
                skipped += 1
                continue
                
            # Sort messages by create_time
            messages.sort(key=lambda x: x.get("create_time", 0) or 0)
            
            # Get earliest message create_time for date in filename and filtering
            message_create_time = None
            if messages:
                message_create_time = get_create_time_safely(messages[0])
            
            # Use the earliest available timestamp
            create_time = conversation_create_time
            if not create_time or create_time <= 0:
                create_time = message_create_time
            
            # Final filter check - use most reliable timestamp
            if create_time and isinstance(create_time, (int, float)) and create_time > 0:
                conversation_year = datetime.fromtimestamp(create_time).year
                if DEBUG_DATES:
                    print(f"Conversation '{title}' date: {datetime.fromtimestamp(create_time).strftime('%Y-%m-%d')}")
                
                if conversation_year < filter_before_year:
                    if DEBUG_DATES:
                        print(f"Skipping conversation from {conversation_year} (before {filter_before_year}): {title}")
                    skipped_old += 1
                    continue
            else:
                if DEBUG_DATES:
                    print(f"Warning: No valid timestamp found for conversation: {title}")
            
            # Generate title without date prefix
            inferred_title = _get_title(title, messages[0] if messages else None)
            
            # Get date string for title prefix
            date_str = ""
            if create_time and isinstance(create_time, (int, float)) and create_time > 0:
                try:
                    date_str = datetime.fromtimestamp(create_time).strftime(config['date_format'])
                except (ValueError, TypeError) as e:
                    if DEBUG_DATES:
                        print(f"Error formatting date for {create_time}: {e}")
            
            # Create filename with date prefix
            sanitized_title = ''.join(c for c in inferred_title if c.isalnum() or c in [' ', '_', '-']).rstrip()
            if date_str:
                file_name = f"{date_str}_{sanitized_title.replace(' ', '_')}.md"
            else:
                file_name = f"{sanitized_title.replace(' ', '_')}.md"
            file_path = os.path.join(output_dir, file_name)
            
            # Generate content
            content = ""
            
            # Add title with creation time at the beginning
            if date_str:
                content += f"# {date_str} {inferred_title}{config['message_separator']}"
            else:
                content += f"# {inferred_title}{config['message_separator']}"
            
            # Add conversation ID as metadata
            content += f"<sub>Conversation ID: {conversation_id}</sub>{config['message_separator']}"
            
            # Add creation time metadata
            if create_time and isinstance(create_time, (int, float)) and create_time > 0:
                formatted_date = datetime.fromtimestamp(create_time).strftime("%Y-%m-%d %H:%M:%S")
                content += f"<sub>Creation time: {formatted_date}</sub>{config['message_separator']}"
            
            # Add placeholder for future summarization feature
            if config.get('enable_summarization', False):
                # This will be implemented in the future
                content += f"**Summary:** [Not implemented yet]{config['message_separator']}"
            
            # Add messages
            for message in messages:
                try:
                    author_role = message.get("author", {}).get("role", "unknown")
                    msg_content = _get_message_content(message)
                    
                    # Skip empty messages if configured
                    if not config['skip_empty_messages'] or msg_content.strip():
                        author_name = config['user_name'] if author_role == "user" else config['assistant_name']
                        content += f"**{author_name}**: {msg_content}{config['message_separator']}"
                except Exception as e:
                    print(f"Error processing message: {e}")
                    continue
            
            # Skip if content is too short (likely empty conversation)
            if len(content.strip()) < 10:
                print(f"Skipping conversation with insufficient content: {inferred_title}")
                skipped += 1
                continue
                
            # Write to file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            processed += 1
            
        except Exception as e:
            print(f"Error processing entry: {e}")
            skipped += 1
    
    if skipped_old > 0:
        print(f"Skipped {skipped_old} conversations created before {filter_before_year}")
        
    return processed, skipped

def main():
    config_path = "config.json"
    try:
        config = read_json_file(config_path)
        if not config:
            print("Failed to load config. Using defaults.")
            config = {
                "user_name": "User",
                "assistant_name": "ChatGPT",
                "input_mode": "file",
                "input_path": "conversations.json",
                "output_directory": "markdown_output",
                "date_format": "%Y-%m-%d",
                "file_name_format": "{title}",
                "include_date": True,
                "message_separator": "\n\n",
                "skip_empty_messages": True,
                "max_file_size_mb": 100,
                "filter_before_year": 2025,
                "enable_summarization": False
            }

        input_path = config['input_path']
        output_dir = config['output_directory']
        max_file_size = config.get('max_file_size_mb', 100)
        filter_before_year = config.get('filter_before_year', 2025)
        enable_summarization = config.get('enable_summarization', False)
        
        print(f"Using filter_before_year: {filter_before_year}")
        print(f"Enable summarization: {enable_summarization}")

        # Try to import dateutil for better date parsing
        try:
            import dateutil.parser
            print("Using dateutil for enhanced date parsing")
        except ImportError:
            print("dateutil not found. Basic date parsing will be used.")
            print("Consider installing python-dateutil for better timestamp handling.")
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        if config['input_mode'] == 'directory':
            processed_total = 0
            skipped_total = 0
            
            json_files = glob.glob(os.path.join(input_path, '*.json'))
            print(f"Found {len(json_files)} JSON files in {input_path}")
            
            for json_file in json_files:
                print(f"Processing {json_file}...")
                data = read_json_file(json_file, max_file_size_mb=max_file_size)
                if data:
                    processed, skipped = process_conversations(data, output_dir, config)
                    processed_total += processed
                    skipped_total += skipped
                    
            print(f"Completed processing all files. Processed: {processed_total}, Skipped: {skipped_total}")
        else:
            # Single file mode
            data = read_json_file(input_path, max_file_size_mb=max_file_size)
            if data:
                processed, skipped = process_conversations(data, output_dir, config)
                print(f"Completed. Processed: {processed}, Skipped: {skipped}")

        print(f"All done! You can access your files here: {output_dir}")
        
    except Exception as e:
        print(f"Error in main execution: {e}")
        if DEBUG_MODE:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
