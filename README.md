# File Management Tool

A Python GUI application for bulk file operations with regex filtering.

## Features

- **Open Folder**: Browse and load files from any directory
- **Search/Filter**: Filter files using plain text or regex patterns
- **File Preview**: Double-click any file to preview its contents
- **Selection Interface**: Select/deselect files with Select All, Deselect All, and Invert Selection
- **Bulk Delete**: Delete multiple selected files at once
- **Bulk Rename**: Rename files using find/replace patterns (supports regex)
- **Bulk Copy**: Copy selected files to another directory

## Requirements

- Python 3.6+
- tkinter (included with Python standard library)

## Usage

### Option 1: Double-Click to Run (Easiest)

**Windows:**
- Double-click `run_file_manager.pyw` (no console window)
- OR double-click `run_file_manager.bat` (shows console window)

### Option 2: Command Line

```bash
python file_manager.py
```

### Getting Started

1. Click **Browse...** to select a folder
2. Use the search box to filter files (enable "Use Regex" for regex patterns)
3. Select files by clicking them (Ctrl+click for multiple, Shift+click for range)
4. Use the bulk action buttons to delete, rename, or copy selected files

### Search Options

- **Pattern**: Enter text or regex to filter files by name
- **Use Regex**: Enable regex pattern matching
- **Case Sensitive**: Make search case-sensitive
- **Include Subdirectories**: Recursively include files from subfolders

### Bulk Rename

1. Enter a pattern to find in the "Rename Pattern" field
2. Enter the replacement text in the "Replace" field
3. Click "Rename" to preview and confirm changes
4. If "Use Regex" is enabled, the pattern is treated as a regex

### Tips

- Double-click a file to preview its contents
- Click column headers to sort files
- The status bar shows the current file count and operation results
