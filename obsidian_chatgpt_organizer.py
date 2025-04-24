import os
import re
import glob
import yaml
import shutil
from datetime import datetime
from collections import Counter
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from tqdm import tqdm

# Download necessary NLTK data
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')

# Define topic keywords for heuristic matching
TOPIC_KEYWORDS = {
    'python': ['python', 'django', 'flask', 'pandas', 'numpy', 'matplotlib', 'tensorflow', 'pytorch'],
    'javascript': ['javascript', 'js', 'node', 'react', 'vue', 'angular', 'typescript', 'npm'],
    'startup': ['startup', 'founder', 'venture', 'pitch', 'entrepreneurship', 'business model', 'mvp'],
    'marketing': ['marketing', 'seo', 'advertising', 'customer', 'brand', 'social media', 'content'],
    'vc': ['vc', 'venture capital', 'investor', 'funding', 'series a', 'angel', 'term sheet'],
    'ai': ['ai', 'artificial intelligence', 'machine learning', 'ml', 'deep learning', 'llm', 'neural'],
    'data': ['data', 'database', 'sql', 'nosql', 'analytics', 'visualization', 'dashboard'],
    'web': ['web', 'html', 'css', 'frontend', 'backend', 'fullstack', 'responsive'],
    'mobile': ['mobile', 'ios', 'android', 'app', 'swift', 'kotlin', 'react native'],
    'cloud': ['cloud', 'aws', 'azure', 'gcp', 'serverless', 'docker', 'kubernetes'],
    'security': ['security', 'encryption', 'authentication', 'vulnerability', 'firewall', 'cybersecurity'],
    'blockchain': ['blockchain', 'crypto', 'bitcoin', 'ethereum', 'nft', 'token', 'web3'],
    'design': ['design', 'ui', 'ux', 'figma', 'sketch', 'wireframe', 'prototype'],
    'career': ['career', 'resume', 'interview', 'job', 'salary', 'promotion', 'skills'],
    'productivity': ['productivity', 'workflow', 'efficiency', 'automation', 'tool', 'process'],
    'health': ['health', 'fitness', 'nutrition', 'medical', 'exercise', 'wellness', 'diet'],
    'education': ['education', 'learning', 'course', 'tutorial', 'teach', 'student', 'training'],
}

# Topic transition phrases that might indicate a new topic
TOPIC_TRANSITION_PHRASES = [
    "now let's switch to", 
    "moving on to", 
    "let's change the subject", 
    "on a different topic", 
    "switching gears",
    "let's talk about something else",
    "changing the subject",
    "new topic:",
    "regarding your other question",
    "to address your next point",
    "on another note",
]

def extract_date_from_markdown(content):
    """Extract date from the markdown content if available"""
    date_match = re.search(r'<sub>(\d{2}-\d{2}-\d{4})</sub>', content)
    if date_match:
        try:
            return datetime.strptime(date_match.group(1), '%m-%d-%Y').date()
        except ValueError:
            pass
    return None

def extract_tags_from_content(content):
    """Extract likely topic tags based on keyword frequency"""
    # Normalize content
    content = content.lower()
    
    # Tokenize and remove stopwords
    stop_words = set(stopwords.words('english'))
    tokens = word_tokenize(content)
    filtered_tokens = [w for w in tokens if w.isalnum() and w not in stop_words]
    
    # Count occurrence of each topic's keywords
    topic_scores = {topic: 0 for topic in TOPIC_KEYWORDS}
    
    for token in filtered_tokens:
        for topic, keywords in TOPIC_KEYWORDS.items():
            if token in keywords or any(keyword in content and len(keyword.split()) > 1 for keyword in keywords):
                topic_scores[topic] += 1
    
    # Filter to topics that appeared at least twice
    relevant_topics = [topic for topic, score in topic_scores.items() if score > 1]
    
    # Always include chatgpt tag
    tags = ['chatgpt'] + relevant_topics
    
    return tags

def generate_summary(content, max_length=100):
    """Generate a brief summary from the conversation content"""
    # Extract first user query
    user_query_match = re.search(r'\*\*[^*]+\*\*:\s*(.*?)\n', content)
    if user_query_match:
        summary = user_query_match.group(1).strip()
        return summary[:max_length] + ('...' if len(summary) > max_length else '')
    
    # Fallback to first line
    first_line = content.split('\n', 1)[0].strip()
    if first_line:
        if first_line.startswith('**'):
            # Remove author tag if present
            first_line = re.sub(r'^\*\*[^*]+\*\*:\s*', '', first_line)
        return first_line[:max_length] + ('...' if len(first_line) > max_length else '')
    
    return "ChatGPT Conversation"

def detect_topic_transitions(content):
    """Detect where topics change in the conversation"""
    transitions = []
    
    # Split into messages
    messages = re.split(r'\n\n\*\*', content)
    
    current_index = 0
    for i, message in enumerate(messages):
        message_lower = message.lower()
        
        # Skip first message as it can't be a transition
        if i > 0:
            for phrase in TOPIC_TRANSITION_PHRASES:
                if phrase in message_lower:
                    # Calculate the position in the original text
                    msg_start = content.find(message, current_index)
                    phrase_pos = msg_start + message_lower.find(phrase)
                    transitions.append(phrase_pos)
                    break
                    
        # Update current index to avoid finding the same message again
        current_index = content.find(message, current_index) + len(message)
    
    return transitions

def split_content_by_topics(content):
    """Split the content at topic transitions"""
    transitions = detect_topic_transitions(content)
    
    if not transitions:
        # No transitions found, return the whole content
        return [content]
    
    # Split content at transition points
    parts = []
    start = 0
    
    for pos in transitions:
        # Find the beginning of the message containing the transition
        message_start = content.rfind('\n\n**', 0, pos)
        if message_start == -1:
            message_start = 0
        
        # Add content up to this transition
        parts.append(content[start:message_start])
        start = message_start
    
    # Add the final section
    parts.append(content[start:])
    
    # Filter out any empty parts
    return [part for part in parts if part.strip()]

def process_markdown_file(file_path, output_dir):
    """Process a single markdown file according to requirements"""
    try:
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Skip empty files
        if not content.strip():
            print(f"Skipping empty file: {file_path}")
            return False
        
        # Extract date from content or filename or fallback to file modification time
        date = extract_date_from_markdown(content)
        if not date:
            # Try to extract from filename (YYYY-MM-DD format)
            filename_date_match = re.search(r'(\d{4}-\d{2}-\d{2})', os.path.basename(file_path))
            if filename_date_match:
                try:
                    date = datetime.strptime(filename_date_match.group(1), '%Y-%m-%d').date()
                except ValueError:
                    date = datetime.fromtimestamp(os.path.getmtime(file_path)).date()
            else:
                date = datetime.fromtimestamp(os.path.getmtime(file_path)).date()
        
        # Get the original filename without extension to extract conversation ID if present
        base_filename = os.path.basename(file_path)
        conversation_id = None
        id_match = re.search(r'[a-f0-9]{8,}', base_filename)
        if id_match:
            conversation_id = id_match.group(0)
        
        # Split content if multiple topics detected
        content_parts = split_content_by_topics(content)
        
        processed_files = []
        
        for i, part_content in enumerate(content_parts):
            # Extract tags and generate summary for this part
            tags = extract_tags_from_content(part_content)
            summary = generate_summary(part_content)
            
            # Create YAML frontmatter
            frontmatter = {
                'tags': tags,
                'date': date.strftime('%Y-%m-%d'),
                'summary': summary
            }
            
            if conversation_id:
                frontmatter['source_conversation_id'] = conversation_id
                
            # Generate new filename
            primary_tag = tags[1] if len(tags) > 1 else 'chat'  # First non-chatgpt tag
            part_suffix = f" part {i+1}" if len(content_parts) > 1 else ""
            
            # Create a slug from the summary
            summary_slug = '-'.join(re.findall(r'[a-z0-9]+', summary.lower())[:5])
            if not summary_slug:
                summary_slug = 'chatgpt-conversation'
                
            new_filename = f"{date.strftime('%Y-%m-%d')} - {primary_tag}-{summary_slug}{part_suffix}.md"
            
            # Make sure the filename is valid
            new_filename = re.sub(r'[<>:"/\\|?*]', '', new_filename)
            new_filename = new_filename[:240]  # Ensure filename isn't too long
            
            output_path = os.path.join(output_dir, new_filename)
            
            # Add frontmatter to content
            content_with_frontmatter = f"---\n{yaml.dump(frontmatter, sort_keys=False)}---\n\n{part_content}"
            
            # Write to new file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content_with_frontmatter)
                
            processed_files.append(output_path)
            
        return len(processed_files) > 0
            
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        return False

def main():
    input_dir = input("Enter the path to your ChatGPT Markdown files: ")
    output_dir = input("Enter the path for processed Obsidian-ready files: ")
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Get all markdown files
    markdown_files = glob.glob(os.path.join(input_dir, "*.md"))
    
    # Print diagnostic information
    print(f"Found {len(markdown_files)} Markdown files in {input_dir}")
    
    if len(markdown_files) == 0:
        print("No Markdown files found. Checking for other possible extensions...")
        json_files = glob.glob(os.path.join(input_dir, "*.json"))
        txt_files = glob.glob(os.path.join(input_dir, "*.txt"))
        print(f"Found {len(json_files)} JSON files and {len(txt_files)} TXT files")
        
        if len(json_files) > 0:
            print("If you have JSON files, you might need to run chatgpt_json_to_markdown.py first")
            
        # Try listing some files in the directory to help diagnose
        print("\nSome files in the directory:")
        all_files = os.listdir(input_dir)[:10]  # List first 10 files
        for file in all_files:
            print(f" - {file}")
    
    successful = 0
    skipped = 0
    
    for file_path in tqdm(markdown_files, desc="Processing files"):
        result = process_markdown_file(file_path, output_dir)
        if result:
            successful += 1
        else:
            skipped += 1
    
    print(f"Processing complete! Successfully processed {successful} files and skipped {skipped} files.")
    print(f"Output files are in: {output_dir}")

if __name__ == "__main__":
    main() 