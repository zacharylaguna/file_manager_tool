"""
File Management Tool
A Python GUI application for bulk file operations with regex filtering.
"""

import os
import re
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from datetime import datetime
import threading


class ProgressDialog:
    """Progress bar dialog for bulk operations."""
    def __init__(self, parent, title, total_items):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x180")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (180 // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        self.total_items = total_items
        self.current = 0
        self.cancelled = False
        
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Preparing...")
        self.status_label.pack(pady=(0, 10))
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(main_frame, length=360, mode='determinate', maximum=total_items)
        self.progress_bar.pack(pady=(0, 10))
        
        # Progress text
        self.progress_label = ttk.Label(main_frame, text="0 / 0")
        self.progress_label.pack(pady=(0, 10))
        
        # Cancel button
        self.cancel_btn = ttk.Button(main_frame, text="Cancel", command=self._cancel, width=15)
        self.cancel_btn.pack()
        
    def _cancel(self):
        self.cancelled = True
        self.cancel_btn.config(state='disabled', text="Cancelling...")
        
    def update(self, current, status_text):
        """Update progress bar and status."""
        self.current = current
        self.progress_bar['value'] = current
        self.status_label.config(text=status_text)
        self.progress_label.config(text=f"{current} / {self.total_items}")
        self.dialog.update()
        
    def close(self):
        """Close the progress dialog."""
        self.dialog.grab_release()
        self.dialog.destroy()


class FileManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("File Management Tool")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        self.current_folder = None
        self.folder_history = []  # Stack for back navigation
        self.all_items = []  # Now includes both files and folders
        self.filtered_items = []
        self.selected_items = set()
        self.item_id_to_path = {}  # Map tree item IDs to file paths for faster lookup
        self.selection_update_pending = None  # For debouncing selection updates
        
        self._setup_styles()
        self._create_ui()
        
    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TButton', padding=6)
        style.configure('Action.TButton', padding=10)
        style.configure('Treeview', rowheight=25)
        style.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'))
        
    def _create_ui(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top section - Folder selection
        self._create_folder_section(main_frame)
        
        # Search/Filter section
        self._create_search_section(main_frame)
        
        # File list section
        self._create_file_list_section(main_frame)
        
        # Action buttons section
        self._create_action_section(main_frame)
        
        # Status bar
        self._create_status_bar(main_frame)
        
    def _create_folder_section(self, parent):
        folder_frame = ttk.LabelFrame(parent, text="Folder", padding="5")
        folder_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Navigation buttons
        self.back_btn = ttk.Button(folder_frame, text="← Back", command=self._go_back, width=8)
        self.back_btn.pack(side=tk.LEFT, padx=(0, 5))
        self.back_btn.config(state='disabled')
        
        self.up_btn = ttk.Button(folder_frame, text="↑ Up", command=self._go_up, width=6)
        self.up_btn.pack(side=tk.LEFT, padx=(0, 10))
        self.up_btn.config(state='disabled')
        
        self.folder_path_var = tk.StringVar()
        folder_entry = ttk.Entry(folder_frame, textvariable=self.folder_path_var, state='readonly')
        folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        browse_btn = ttk.Button(folder_frame, text="Browse...", command=self._browse_folder)
        browse_btn.pack(side=tk.LEFT)
        
        refresh_btn = ttk.Button(folder_frame, text="Refresh", command=self._refresh_files)
        refresh_btn.pack(side=tk.LEFT, padx=(5, 0))
        
    def _create_search_section(self, parent):
        search_frame = ttk.LabelFrame(parent, text="Search / Filter", padding="5")
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Search entry
        ttk.Label(search_frame, text="Pattern:").pack(side=tk.LEFT)
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self._filter_files())
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        search_entry.pack(side=tk.LEFT, padx=(5, 10))
        
        # Regex checkbox
        self.use_regex_var = tk.BooleanVar(value=False)
        regex_check = ttk.Checkbutton(search_frame, text="Use Regex", variable=self.use_regex_var,
                                       command=self._filter_files)
        regex_check.pack(side=tk.LEFT, padx=(0, 10))
        
        # Case sensitive checkbox
        self.case_sensitive_var = tk.BooleanVar(value=False)
        case_check = ttk.Checkbutton(search_frame, text="Case Sensitive", variable=self.case_sensitive_var,
                                      command=self._filter_files)
        case_check.pack(side=tk.LEFT, padx=(0, 10))
        
        # Include subdirectories checkbox
        self.include_subdirs_var = tk.BooleanVar(value=False)
        subdirs_check = ttk.Checkbutton(search_frame, text="Include Subdirectories", 
                                         variable=self.include_subdirs_var,
                                         command=self._refresh_files)
        subdirs_check.pack(side=tk.LEFT, padx=(0, 10))
        
        # Type filter
        ttk.Label(search_frame, text="Show:").pack(side=tk.LEFT, padx=(10, 5))
        self.show_type_var = tk.StringVar(value="all")
        type_combo = ttk.Combobox(search_frame, textvariable=self.show_type_var, 
                                   values=["all", "files", "folders"], width=8, state='readonly')
        type_combo.pack(side=tk.LEFT)
        type_combo.bind('<<ComboboxSelected>>', lambda e: self._filter_files())
        
    def _create_file_list_section(self, parent):
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Selection buttons
        select_frame = ttk.Frame(list_frame)
        select_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(select_frame, text="Select All", command=self._select_all).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(select_frame, text="Deselect All", command=self._deselect_all).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(select_frame, text="Invert Selection", command=self._invert_selection).pack(side=tk.LEFT)
        
        self.selection_label = ttk.Label(select_frame, text="Selected: 0 items")
        self.selection_label.pack(side=tk.RIGHT)
        
        # Treeview for file list
        columns = ('type', 'name', 'size', 'modified', 'path')
        self.file_tree = ttk.Treeview(list_frame, columns=columns, show='headings', selectmode='extended')
        
        self.file_tree.heading('type', text='Type', command=lambda: self._sort_column('type'))
        self.file_tree.heading('name', text='Name', command=lambda: self._sort_column('name'))
        self.file_tree.heading('size', text='Size', command=lambda: self._sort_column('size'))
        self.file_tree.heading('modified', text='Modified', command=lambda: self._sort_column('modified'))
        self.file_tree.heading('path', text='Path', command=lambda: self._sort_column('path'))
        
        self.file_tree.column('type', width=60)
        self.file_tree.column('name', width=280)
        self.file_tree.column('size', width=100)
        self.file_tree.column('modified', width=150)
        self.file_tree.column('path', width=280)
        
        # Scrollbars
        v_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.file_tree.yview)
        h_scroll = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.file_tree.xview)
        self.file_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        self.file_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Bind selection event
        self.file_tree.bind('<<TreeviewSelect>>', self._on_selection_change)
        self.file_tree.bind('<Double-1>', self._preview_file)
        
        # Sort state
        self.sort_column = 'name'
        self.sort_reverse = False
        
    def _create_action_section(self, parent):
        action_frame = ttk.LabelFrame(parent, text="Bulk Actions", padding="10")
        action_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Delete button
        delete_btn = ttk.Button(action_frame, text="🗑️ Delete Selected", 
                                command=self._bulk_delete, style='Action.TButton')
        delete_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Rename section
        ttk.Separator(action_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        ttk.Label(action_frame, text="Rename Pattern:").pack(side=tk.LEFT)
        self.rename_pattern_var = tk.StringVar()
        rename_entry = ttk.Entry(action_frame, textvariable=self.rename_pattern_var, width=20)
        rename_entry.pack(side=tk.LEFT, padx=(5, 5))
        
        ttk.Label(action_frame, text="Replace:").pack(side=tk.LEFT)
        self.rename_replace_var = tk.StringVar()
        replace_entry = ttk.Entry(action_frame, textvariable=self.rename_replace_var, width=20)
        replace_entry.pack(side=tk.LEFT, padx=(5, 5))
        
        rename_btn = ttk.Button(action_frame, text="✏️ Rename", command=self._bulk_rename)
        rename_btn.pack(side=tk.LEFT, padx=(5, 10))
        
        # Copy section
        ttk.Separator(action_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        copy_btn = ttk.Button(action_frame, text="📋 Copy To...", command=self._bulk_copy)
        copy_btn.pack(side=tk.LEFT)
        
    def _create_status_bar(self, parent):
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X)
        
        self.status_var = tk.StringVar(value="Ready. Open a folder to begin.")
        status_label = ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_label.pack(fill=tk.X)
        
    def _browse_folder(self):
        folder = filedialog.askdirectory(title="Select Folder")
        if folder:
            self.folder_history.clear()  # Clear history when browsing to new location
            self._navigate_to_folder(folder, add_to_history=False)
            
    def _refresh_files(self):
        if not self.current_folder:
            return
            
        self.all_items = []
        self.selected_items.clear()
        
        try:
            if self.include_subdirs_var.get():
                for root, dirs, files in os.walk(self.current_folder):
                    for dir_name in dirs:
                        dir_path = os.path.join(root, dir_name)
                        self.all_items.append(self._get_item_info(dir_path, is_folder=True))
                    for file in files:
                        file_path = os.path.join(root, file)
                        self.all_items.append(self._get_item_info(file_path, is_folder=False))
            else:
                for item in os.listdir(self.current_folder):
                    item_path = os.path.join(self.current_folder, item)
                    is_folder = os.path.isdir(item_path)
                    self.all_items.append(self._get_item_info(item_path, is_folder=is_folder))
                        
            self._filter_files()
            file_count = sum(1 for i in self.all_items if i['type'] == 'file')
            folder_count = sum(1 for i in self.all_items if i['type'] == 'folder')
            self.status_var.set(f"Loaded {file_count} files and {folder_count} folders from {self.current_folder}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load items: {str(e)}")
            
    def _get_item_info(self, item_path, is_folder=False):
        stat = os.stat(item_path)
        if is_folder:
            try:
                item_count = len(os.listdir(item_path))
                size_display = f"{item_count} items"
            except PermissionError:
                size_display = "Access denied"
                item_count = 0
        else:
            size_display = None  # Will be formatted later
            item_count = stat.st_size
        return {
            'name': os.path.basename(item_path),
            'path': item_path,
            'size': stat.st_size if not is_folder else 0,
            'size_display': size_display,
            'item_count': item_count,
            'modified': datetime.fromtimestamp(stat.st_mtime),
            'type': 'folder' if is_folder else 'file'
        }
        
    def _format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
        
    def _filter_files(self):
        pattern = self.search_var.get()
        show_type = self.show_type_var.get()
        
        # Start with all items
        items = self.all_items[:]
        
        # Filter by type
        if show_type == "files":
            items = [i for i in items if i['type'] == 'file']
        elif show_type == "folders":
            items = [i for i in items if i['type'] == 'folder']
        
        # Filter by pattern
        if not pattern:
            self.filtered_items = items
        else:
            self.filtered_items = []
            
            try:
                if self.use_regex_var.get():
                    flags = 0 if self.case_sensitive_var.get() else re.IGNORECASE
                    regex = re.compile(pattern, flags)
                    for item_info in items:
                        if regex.search(item_info['name']):
                            self.filtered_items.append(item_info)
                else:
                    search_pattern = pattern if self.case_sensitive_var.get() else pattern.lower()
                    for item_info in items:
                        name = item_info['name'] if self.case_sensitive_var.get() else item_info['name'].lower()
                        if search_pattern in name:
                            self.filtered_items.append(item_info)
            except re.error as e:
                self.status_var.set(f"Invalid regex: {str(e)}")
                return
                
        self._update_file_list()
        self.status_var.set(f"Showing {len(self.filtered_items)} of {len(self.all_items)} items")
        
    def _update_file_list(self):
        self.file_tree.delete(*self.file_tree.get_children())
        self.item_id_to_path.clear()
        
        for item_info in self.filtered_items:
            type_icon = "📁" if item_info['type'] == 'folder' else "📄"
            size_str = item_info['size_display'] if item_info['size_display'] else self._format_size(item_info['size'])
            values = (
                type_icon,
                item_info['name'],
                size_str,
                item_info['modified'].strftime('%Y-%m-%d %H:%M'),
                item_info['path']
            )
            item_id = self.file_tree.insert('', tk.END, values=values)
            self.item_id_to_path[item_id] = item_info['path']
            
            if item_info['path'] in self.selected_items:
                self.file_tree.selection_add(item_id)
                
        self._update_selection_label()
        
    def _sort_column(self, column):
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = False
            
        if column == 'size':
            self.filtered_items.sort(key=lambda x: x['size'], reverse=self.sort_reverse)
        elif column == 'modified':
            self.filtered_items.sort(key=lambda x: x['modified'], reverse=self.sort_reverse)
        elif column == 'name':
            self.filtered_items.sort(key=lambda x: x['name'].lower(), reverse=self.sort_reverse)
        elif column == 'type':
            self.filtered_items.sort(key=lambda x: x['type'], reverse=self.sort_reverse)
        else:
            self.filtered_items.sort(key=lambda x: x['path'].lower(), reverse=self.sort_reverse)
            
        self._update_file_list()
        
    def _on_selection_change(self, event):
        # Debounce selection updates to avoid lag with large selections
        if self.selection_update_pending:
            self.root.after_cancel(self.selection_update_pending)
        self.selection_update_pending = self.root.after(50, self._update_selection)
    
    def _update_selection(self):
        """Update selected items set (debounced)."""
        self.selection_update_pending = None
        self.selected_items.clear()
        # Use the cached mapping instead of calling item() for each selection
        for item_id in self.file_tree.selection():
            path = self.item_id_to_path.get(item_id)
            if path:
                self.selected_items.add(path)
        self._update_selection_label()
        
    def _update_selection_label(self):
        count = len(self.selected_items)
        self.selection_label.config(text=f"Selected: {count} item{'s' if count != 1 else ''}")
        
    def _select_all(self):
        for item_id in self.file_tree.get_children():
            self.file_tree.selection_add(item_id)
        self._on_selection_change(None)
        
    def _deselect_all(self):
        self.file_tree.selection_remove(*self.file_tree.get_children())
        self._on_selection_change(None)
        
    def _invert_selection(self):
        all_items = self.file_tree.get_children()
        selected = set(self.file_tree.selection())
        
        for item_id in all_items:
            if item_id in selected:
                self.file_tree.selection_remove(item_id)
            else:
                self.file_tree.selection_add(item_id)
        self._on_selection_change(None)
        
    def _go_back(self):
        """Navigate to the previous folder in history."""
        if self.folder_history:
            prev_folder = self.folder_history.pop()
            self._navigate_to_folder(prev_folder, add_to_history=False)
            
    def _go_up(self):
        """Navigate to the parent folder."""
        if self.current_folder:
            parent = os.path.dirname(self.current_folder)
            if parent and parent != self.current_folder:
                self._navigate_to_folder(parent, add_to_history=True)
                
    def _navigate_to_folder(self, folder_path, add_to_history=True):
        """Navigate to a specific folder."""
        if add_to_history and self.current_folder:
            self.folder_history.append(self.current_folder)
            
        self.current_folder = folder_path
        self.folder_path_var.set(folder_path)
        self._refresh_files()
        self._update_nav_buttons()
        
    def _update_nav_buttons(self):
        """Update the state of navigation buttons."""
        # Back button
        if self.folder_history:
            self.back_btn.config(state='normal')
        else:
            self.back_btn.config(state='disabled')
            
        # Up button
        if self.current_folder:
            parent = os.path.dirname(self.current_folder)
            if parent and parent != self.current_folder:
                self.up_btn.config(state='normal')
            else:
                self.up_btn.config(state='disabled')
        else:
            self.up_btn.config(state='disabled')
            
    def _on_double_click(self, event):
        """Handle double-click: enter folder or preview file."""
        selection = self.file_tree.selection()
        if not selection:
            return
            
        item_id = selection[0]
        values = self.file_tree.item(item_id, 'values')
        item_path = values[4]  # path is index 4
        
        # Check if it's a folder - navigate into it
        if values[0] == "📁":
            self._navigate_to_folder(item_path, add_to_history=True)
            return
        
        # Otherwise preview the file
        self._preview_file_content(item_path, values[1])
        
    def _preview_file(self, event):
        """Legacy handler - redirects to _on_double_click."""
        self._on_double_click(event)
        
    def _preview_file_content(self, file_path, file_name):
        """Open a preview window for a file."""
        # Open preview window
        preview_win = tk.Toplevel(self.root)
        preview_win.title(f"Preview: {file_name}")
        preview_win.geometry("600x400")
        
        text_widget = tk.Text(preview_win, wrap=tk.WORD)
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read(10000)  # Read first 10KB
                if len(content) == 10000:
                    content += "\n\n... [File truncated for preview]"
                text_widget.insert('1.0', content)
        except Exception as e:
            text_widget.insert('1.0', f"Cannot preview file: {str(e)}")
            
        text_widget.config(state='disabled')
        
    def _bulk_delete(self):
        if not self.selected_items:
            messagebox.showwarning("No Selection", "Please select items to delete.")
            return
        
        # Count files and folders
        files_to_delete = []
        folders_to_delete = []
        for item in self.all_items:
            if item['path'] in self.selected_items:
                if item['type'] == 'folder':
                    folders_to_delete.append(item['path'])
                else:
                    files_to_delete.append(item['path'])
        
        msg = f"Are you sure you want to delete:\n"
        if files_to_delete:
            msg += f"  - {len(files_to_delete)} file(s)\n"
        if folders_to_delete:
            msg += f"  - {len(folders_to_delete)} folder(s) and their contents\n"
        msg += "\nThis action cannot be undone!"
        
        if not messagebox.askyesno("Confirm Delete", msg):
            return
        
        # Create progress dialog
        total = len(files_to_delete) + len(folders_to_delete)
        progress = ProgressDialog(self.root, "Deleting Items", total)
        
        deleted = 0
        errors = []
        
        # Delete files first
        for i, file_path in enumerate(files_to_delete, 1):
            if progress.cancelled:
                break
            progress.update(i + len([f for f in files_to_delete[:i-1] if f in [x[0] for x in errors]]), 
                          f"Deleting file: {os.path.basename(file_path)}")
            try:
                os.remove(file_path)
                deleted += 1
            except Exception as e:
                errors.append(f"{os.path.basename(file_path)}: {str(e)}")
        
        # Delete folders (use shutil.rmtree for non-empty folders)
        for i, folder_path in enumerate(folders_to_delete, 1):
            if progress.cancelled:
                break
            progress.update(len(files_to_delete) + i, 
                          f"Deleting folder: {os.path.basename(folder_path)}")
            try:
                shutil.rmtree(folder_path)
                deleted += 1
            except Exception as e:
                errors.append(f"{os.path.basename(folder_path)}: {str(e)}")
        
        progress.close()
        self._refresh_files()
        
        if errors:
            messagebox.showwarning("Delete Complete", 
                                   f"Deleted {deleted} items.\n\nErrors:\n" + "\n".join(errors[:5]))
        else:
            messagebox.showinfo("Delete Complete", f"Successfully deleted {deleted} items.")
            
        self.status_var.set(f"Deleted {deleted} items")
        
    def _bulk_rename(self):
        if not self.selected_items:
            messagebox.showwarning("No Selection", "Please select items to rename.")
            return
            
        pattern = self.rename_pattern_var.get()
        replacement = self.rename_replace_var.get()
        
        if not pattern:
            messagebox.showwarning("No Pattern", "Please enter a rename pattern.")
            return
            
        # Preview changes
        preview_changes = []
        for item_path in self.selected_items:
            old_name = os.path.basename(item_path)
            try:
                if self.use_regex_var.get():
                    new_name = re.sub(pattern, replacement, old_name)
                else:
                    new_name = old_name.replace(pattern, replacement)
                    
                if old_name != new_name:
                    preview_changes.append((item_path, old_name, new_name))
            except re.error as e:
                messagebox.showerror("Regex Error", f"Invalid regex pattern: {str(e)}")
                return
                
        if not preview_changes:
            messagebox.showinfo("No Changes", "No items would be renamed with this pattern.")
            return
            
        # Show preview
        preview_text = "\n".join([f"{old} → {new}" for _, old, new in preview_changes[:10]])
        if len(preview_changes) > 10:
            preview_text += f"\n... and {len(preview_changes) - 10} more"
            
        if not messagebox.askyesno("Confirm Rename", 
                                    f"Rename {len(preview_changes)} items?\n\n{preview_text}"):
            return
        
        # Create progress dialog
        progress = ProgressDialog(self.root, "Renaming Items", len(preview_changes))
        
        renamed = 0
        errors = []
        
        for i, (item_path, old_name, new_name) in enumerate(preview_changes, 1):
            if progress.cancelled:
                break
            progress.update(i, f"Renaming: {old_name}")
            try:
                dir_path = os.path.dirname(item_path)
                new_path = os.path.join(dir_path, new_name)
                os.rename(item_path, new_path)
                renamed += 1
            except Exception as e:
                errors.append(f"{old_name}: {str(e)}")
        
        progress.close()
        self._refresh_files()
        
        if errors:
            messagebox.showwarning("Rename Complete", 
                                   f"Renamed {renamed} items.\n\nErrors:\n" + "\n".join(errors[:5]))
        else:
            messagebox.showinfo("Rename Complete", f"Successfully renamed {renamed} items.")
            
        self.status_var.set(f"Renamed {renamed} items")
        
    def _bulk_copy(self):
        if not self.selected_items:
            messagebox.showwarning("No Selection", "Please select items to copy.")
            return
            
        dest_folder = filedialog.askdirectory(title="Select Destination Folder")
        if not dest_folder:
            return
        
        # Separate files and folders
        files_to_copy = []
        folders_to_copy = []
        for item in self.all_items:
            if item['path'] in self.selected_items:
                if item['type'] == 'folder':
                    folders_to_copy.append(item['path'])
                else:
                    files_to_copy.append(item['path'])
        
        msg = f"Copy to {dest_folder}:\n"
        if files_to_copy:
            msg += f"  - {len(files_to_copy)} file(s)\n"
        if folders_to_copy:
            msg += f"  - {len(folders_to_copy)} folder(s)\n"
            
        if not messagebox.askyesno("Confirm Copy", msg):
            return
        
        # Create progress dialog
        total = len(files_to_copy) + len(folders_to_copy)
        progress = ProgressDialog(self.root, "Copying Items", total)
        
        copied = 0
        errors = []
        
        # Copy files
        for i, file_path in enumerate(files_to_copy, 1):
            if progress.cancelled:
                break
            file_name = os.path.basename(file_path)
            progress.update(i, f"Copying file: {file_name}")
            try:
                dest_path = os.path.join(dest_folder, file_name)
                
                # Handle duplicate names
                if os.path.exists(dest_path):
                    base, ext = os.path.splitext(file_name)
                    counter = 1
                    while os.path.exists(dest_path):
                        dest_path = os.path.join(dest_folder, f"{base}_{counter}{ext}")
                        counter += 1
                        
                shutil.copy2(file_path, dest_path)
                copied += 1
            except Exception as e:
                errors.append(f"{os.path.basename(file_path)}: {str(e)}")
        
        # Copy folders
        for i, folder_path in enumerate(folders_to_copy, 1):
            if progress.cancelled:
                break
            folder_name = os.path.basename(folder_path)
            progress.update(len(files_to_copy) + i, f"Copying folder: {folder_name}")
            try:
                dest_path = os.path.join(dest_folder, folder_name)
                
                # Handle duplicate names
                if os.path.exists(dest_path):
                    counter = 1
                    while os.path.exists(dest_path):
                        dest_path = os.path.join(dest_folder, f"{folder_name}_{counter}")
                        counter += 1
                        
                shutil.copytree(folder_path, dest_path)
                copied += 1
            except Exception as e:
                errors.append(f"{os.path.basename(folder_path)}: {str(e)}")
        
        progress.close()
                
        if errors:
            messagebox.showwarning("Copy Complete", 
                                   f"Copied {copied} items.\n\nErrors:\n" + "\n".join(errors[:5]))
        else:
            messagebox.showinfo("Copy Complete", f"Successfully copied {copied} items to:\n{dest_folder}")
            
        self.status_var.set(f"Copied {copied} items to {dest_folder}")


def main():
    root = tk.Tk()
    app = FileManagerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
