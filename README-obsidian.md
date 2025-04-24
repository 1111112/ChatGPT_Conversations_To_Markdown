# ChatGPT to Obsidian Organizer

This script processes ChatGPT conversation Markdown files and organizes them for use in Obsidian. It performs the following operations:

1. Skips empty or broken Markdown files
2. Skips conversations from before 2025
3. Cleans and standardizes Markdown formatting
4. Automatically extracts topics per conversation using keyword analysis
5. Splits conversations with multiple topics into separate files
6. Generates descriptive filenames with dates
7. Adds YAML frontmatter with metadata (tags, date, summary, source ID)

## Features

- **Topic Detection**: Automatically identifies conversation topics like Python, Startup, Marketing, etc.
- **Content Splitting**: Detects topic transitions and splits files accordingly
- **Smart Summaries**: Extracts the first user query or message as a summary
- **YAML Frontmatter**: Adds properly formatted frontmatter for Obsidian
- **Filename Generation**: Creates standardized filenames with date and topic information

## Installation

1. Clone this repository:
```
git clone https://github.com/daugaard47/ChatGPT_Conversations_To_Markdown.git
cd ChatGPT_Conversations_To_Markdown
```

2. Install the required dependencies:
```
pip install -r requirements.txt
```

## Usage

Run the script:
```
python obsidian_chatgpt_organizer.py
```

You'll be prompted for:
1. The input directory containing your ChatGPT Markdown files
2. The output directory for the processed Obsidian-ready files

## How It Works

1. **Input**: The script reads all .md files from the specified input directory
2. **Processing**:
   - Extracts date information from the content or filename
   - Identifies topic transitions and splits content when appropriate
   - Analyzes content to determine relevant topic tags
   - Generates a concise summary from the conversation
   - Creates YAML frontmatter with metadata
3. **Output**: Creates new Markdown files with standardized names and frontmatter

## Example Output

Each processed file will have a name like `2025-04-21 - startup-pitch-idea-feedback.md` and will contain frontmatter:

```yaml
---
tags: [chatgpt, startup, business]
date: 2025-04-21
summary: How can I improve my SaaS startup pitch to investors?
source_conversation_id: abc123def456
---

**Summer**: How can I improve my SaaS startup pitch to investors?

**ChatGPT**: To improve your SaaS startup pitch...
```

## Customization

You can modify the `TOPIC_KEYWORDS` dictionary in the script to add or adjust the topic categories and their associated keywords to better match your specific content. 