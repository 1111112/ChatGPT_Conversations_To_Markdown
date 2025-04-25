# ChatGPT Conversations to Markdown
ChatGPT Conversations to Markdown is a Python script that converts your exported ChatGPT conversations into readable and well-formatted Markdown files by using the `conversations.json` file. The script provides a convenient way to archive and share your interactions with ChatGPT.

## Features
* Convert ChatGPT conversations stored in JSON format to Markdown
* Customize user and assistant names using a configuration file
* Include creation time in front of the title in the generated Markdown files
* Filter out conversations created before a specific year (default: 2025)
* Optional summarization feature (can be enabled in config.json for future implementation)
* Customize the format of file names, dates, and message separators
* Process individual JSON files or all JSON files in a directory

## Installation
1. Clone the repository or download the ZIP file and extract it to a folder on your computer.
```
git clone https://github.com/daugaard47/ChatGPT_Conversations_To_Markdown.git
```
2. Change into the project directory:
```
cd ChatGPT_Conversations_To_Markdown
```
3. Create a virtual environment (optional but recommended):
```
python -m venv venv
```
4. Activate the virtual environment:
```
# For Windows:
venv\Scripts\activate

# For Linux or macOS:
source venv/bin/activate
```

5. Install the required Python dependencies:
```
pip install tqdm python-dateutil
```

## Usage
1. Create your own `config.json` file based on the provided `config.template.json`. Update it with your desired settings, such as user and assistant names, input and output paths, and other formatting options.
   - Set `filter_before_year` to control which conversations are included (default: 2025)
   - Set `enable_summarization` to false/true to control the summarization feature (default: false)
2. Create your JSON input directory and add the JSON file e.g. conversations.json you received from the export of the ChatGPT conversations to this location. Add this path to your config file.
3. Create the Output Directory and add this path to your config file. Your markdown files will appear here after the script runs.
4. Create your own shell script based on the provided `run_chatgpt_processor.template.sh` or run the script directly:
```
python chatgpt_json_to_markdown.py
```
5. The script will process your conversations and save them as Markdown files in the specified output directory.
6. When the script is done, you will see a message like this:
```
All Done! You can access your files here: <output_directory>
```

## Configuration Options
The `config.json` file includes the following options:

```json
{
  "user_name": "User",                  // Your name in the conversations
  "assistant_name": "ChatGPT",          // Assistant name in the conversations
  "input_mode": "directory",            // "file" or "directory"
  "input_path": "./data/input",         // Input file or directory path
  "output_directory": "./data/output",  // Output directory for Markdown files
  "date_format": "%Y-%m-%d",            // Format for dates in output
  "file_name_format": "{title}",        // Format for output filenames
  "include_date": true,                 // Include date in the formatted output
  "message_separator": "\n\n",          // Separator between messages
  "skip_empty_messages": true,          // Skip messages with no content
  "max_file_size_mb": 100,              // Maximum allowed input file size
  "filter_before_year": 2025,           // Skip conversations before this year
  "enable_summarization": false         // Enable summarization placeholder
}
```

## Important Note
The repository includes template files for configuration (`config.template.json`) and running the script (`run_chatgpt_processor.template.sh`). You should create your own versions of these files with your personal settings:
- Copy `config.template.json` to `config.json` and update the paths and settings
- Copy `run_chatgpt_processor.template.sh` to `run_chatgpt_processor.sh` and update the paths

Both personal configuration files are excluded from git to protect your privacy.

Now you can easily read, share, or archive your ChatGPT conversations in a more human-readable format. Enjoy!
