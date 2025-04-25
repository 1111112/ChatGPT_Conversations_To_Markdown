#!/bin/bash

# Set paths 
MARKDOWN_DIR="./data/output/chatgpt_markdown"
OBSIDIAN_DIR="./data/output/obsidian_chatgpt"
JSON_DIR="./data/input/chatgpt_history"

# Display menu
echo "=== ChatGPT Conversation Processor ==="
echo "1. Convert JSON to Markdown"
echo "2. Process Markdown files for Obsidian"
echo "3. Run both steps"
echo "4. Exit"
echo ""
read -p "Enter your choice (1-4): " choice

case $choice in
  1)
    echo "Converting JSON to Markdown..."
    python3 chatgpt_json_to_markdown.py
    ;;
  2)
    echo "Processing Markdown for Obsidian..."
    # Use python with input redirection to answer the prompts
    python3 obsidian_chatgpt_organizer.py << INPUTS
$MARKDOWN_DIR
$OBSIDIAN_DIR
INPUTS
    ;;
  3)
    echo "Running full pipeline..."
    python3 chatgpt_json_to_markdown.py && \
    python3 obsidian_chatgpt_organizer.py << INPUTS
$MARKDOWN_DIR
$OBSIDIAN_DIR
INPUTS
    ;;
  4)
    echo "Exiting..."
    exit 0
    ;;
  *)
    echo "Invalid choice."
    exit 1
    ;;
esac

echo "All done!" 