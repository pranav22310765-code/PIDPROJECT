import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading

from pathlib import Path

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DRAG_DROP_AVAILABLE = True
except ImportError:
    DRAG_DROP_AVAILABLE = False
    print("Warning: tkinterdnd2 not installed. Drag-and-drop will be disabled.")
    print("Install with: pip install tkinterdnd2")

import PDFProcessor_wo_ocr


class ModernPDFApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Data Extractor")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        self.root.configure(bg="#f8f9fa")

        # Application state
        self.tree = None
        self.current_df = None
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="Ready")
        
        # Processing settings
        self.dpi_var = tk.IntVar(value=300)  # Default DPI
        self.conf_var = tk.DoubleVar(value=0.25)  # Default confidence threshold

        # Configure modern styling
        self.configure_styles()

        # Create main layout
        self.create_layout()

        # Setup drag and drop (assuming tkinterdnd2 is available)
        self.setup_drag_drop()

    def configure_styles(self):
        """Configure modern styling for ttk widgets"""
        self.style = ttk.Style()

        # Use a modern theme as base
        available_themes = self.style.theme_names()
        if 'vista' in available_themes:
            self.style.theme_use('vista')
        elif 'clam' in available_themes:
            self.style.theme_use('clam')

        # Configure custom styles
        self.style.configure("Modern.TFrame",
                             background="#ffffff",
                             relief="flat",
                             borderwidth=1)

        self.style.configure("Card.TFrame",
                             background="#ffffff",
                             relief="solid",
                             borderwidth=1)

        self.style.configure("Modern.TButton",
                             background="#ffffff",
                             foreground="#009DF0",
                             borderwidth=0,
                             focuscolor="none",
                             padding=(20, 10),
                             font=('Segoe UI', 10))

        self.style.map("Modern.TButton",
                       background=[('active', '#0088d1'),
                                   ('pressed', '#0071b3'),
                                   ('disabled', '#cccccc')])

        self.style.configure("Secondary.TButton",
                             background="#ffffff",
                             foreground="#009DF0",
                             borderwidth=0,
                             focuscolor="none",
                             padding=(15, 8),
                             font=('Segoe UI', 9))

        self.style.map("Secondary.TButton",
                       background=[('active', '#545b62'),
                                   ('pressed', '#3a3f44')])

        self.style.configure("Modern.Treeview",
                             background="#ffffff",
                             foreground="#212529",
                             rowheight=30,
                             fieldbackground="#ffffff",
                             font=('Segoe UI', 9),
                             borderwidth=1,
                             relief="solid")

        self.style.configure("Modern.Treeview.Heading",
                             background="#e9ecef",
                             foreground="#495057",
                             font=('Segoe UI', 9, 'bold'),
                             relief="flat",
                             borderwidth=1)

        self.style.map('Modern.Treeview',
                       background=[('selected', '#009DF0')],
                       foreground=[('selected', '#ffffff')])

        self.style.configure("Modern.Horizontal.TProgressbar",
                             background="#009DF0",
                             troughcolor="#e9ecef",
                             borderwidth=0,
                             lightcolor="#009DF0",
                             darkcolor="#009DF0")

    def create_layout(self):
        """Create the main application layout"""
        # Main container
        self.main_frame = ttk.Frame(self.root, style="Modern.TFrame")
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Header
        self.create_header()

        # Content area
        self.content_frame = ttk.Frame(self.main_frame, style="Modern.TFrame")
        self.content_frame.pack(fill=tk.BOTH, expand=True, pady=(20, 0))

        # Initially show upload UI
        self.show_upload_ui()

        # Footer with status bar
        self.create_footer()

    def create_header(self):
        """Create the application header"""
        header_frame = ttk.Frame(self.main_frame, style="Modern.TFrame")
        header_frame.pack(fill=tk.X, pady=(0, 10))

        # Title and subtitle
        title_label = tk.Label(header_frame,
                               text="PDF Data Extractor",
                               font=('Segoe UI', 24, 'bold'),
                               bg="#f8f9fa",
                               fg="#212529")
        title_label.pack(anchor=tk.W)

        subtitle_label = tk.Label(header_frame,
                                  text="Extract tabular data from PDF documents",
                                  font=('Segoe UI', 11),
                                  bg="#f8f9fa",
                                  fg="#6c757d")
        subtitle_label.pack(anchor=tk.W, pady=(5, 0))

        # Separator
        separator = ttk.Separator(header_frame, orient=tk.HORIZONTAL)
        separator.pack(fill=tk.X, pady=(15, 0))

    def create_footer(self):
        """Create the footer with status bar"""
        self.footer_frame = ttk.Frame(self.main_frame, style="Modern.TFrame")
        self.footer_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))

        # Status bar
        status_frame = ttk.Frame(self.footer_frame, style="Card.TFrame")
        status_frame.pack(fill=tk.X, pady=(10, 0))

        self.status_label = tk.Label(status_frame,
                                     textvariable=self.status_var,
                                     font=('Segoe UI', 9),
                                     bg="#ffffff",
                                     fg="#495057",
                                     anchor=tk.W,
                                     padx=10,
                                     pady=5)
        self.status_label.pack(fill=tk.X)

    def show_upload_ui(self):
        """Show the upload/drag-drop interface"""
        # Clear content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # Upload card
        self.upload_card = ttk.Frame(self.content_frame, style="Card.TFrame")
        self.upload_card.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)

        # Upload content
        upload_content = ttk.Frame(self.upload_card, style="Modern.TFrame")
        upload_content.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # Upload icon (using text as placeholder)
        icon_label = tk.Label(upload_content,
                              text="📄",
                              font=('Segoe UI', 48),
                              bg="#ffffff",
                              fg="#009DF0")
        icon_label.pack(pady=(0, 20))

        # Upload text
        upload_label = tk.Label(upload_content,
                                text="Drag and drop a PDF file here",
                                font=('Segoe UI', 16),
                                bg="#ffffff",
                                fg="#495057")
        upload_label.pack()

        # Or text
        or_label = tk.Label(upload_content,
                            text="or",
                            font=('Segoe UI', 12),
                            bg="#ffffff",
                            fg="#6c757d")
        or_label.pack(pady=(10, 15))

        # Browse button
        self.browse_button = ttk.Button(upload_content,
                                        text="Browse Files",
                                        command=self.browse_file,
                                        style="Modern.TButton")
        self.browse_button.pack()

        # Supported formats
        formats_label = tk.Label(upload_content,
                                 text="Supported format: PDF",
                                 font=('Segoe UI', 9),
                                 bg="#ffffff",
                                 fg="#6c757d")
        formats_label.pack(pady=(15, 0))
        
        # Current settings info
        settings_info = tk.Label(upload_content,
                                text=f"DPI: {self.dpi_var.get()} | Confidence: {self.conf_var.get():.2f}",
                                font=('Segoe UI', 8),
                                bg="#ffffff",
                                fg="#009DF0")
        settings_info.pack(pady=(5, 0))

    def show_data_view(self, dataframe):
        """Show the data grid view"""
        # Clear content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # Data view frame
        data_frame = ttk.Frame(self.content_frame, style="Modern.TFrame")
        data_frame.pack(fill=tk.BOTH, expand=True)

        # Toolbar
        self.create_toolbar(data_frame)

        # Data grid with scrollbars
        grid_frame = ttk.Frame(data_frame, style="Card.TFrame")
        grid_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # Create treeview
        self.tree = ttk.Treeview(grid_frame, style="Modern.Treeview")

        # Scrollbars
        v_scrollbar = ttk.Scrollbar(grid_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(grid_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        # Grid layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")

        grid_frame.grid_rowconfigure(0, weight=1)
        grid_frame.grid_columnconfigure(0, weight=1)

        # Configure treeview
        self.tree["columns"] = list(dataframe.columns)
        self.tree["show"] = "headings"

        for col in dataframe.columns:
            self.tree.heading(col, text=col, anchor=tk.W)
            self.tree.column(col, width=150, anchor=tk.W, minwidth=100)

        # Insert data
        for _, row in dataframe.iterrows():
            self.tree.insert("", "end", values=list(row))

        # Update status
        self.status_var.set(f"Loaded {len(dataframe)} rows × {len(dataframe.columns)} columns")

    def create_toolbar(self, parent):
        """Create toolbar with action buttons"""
        toolbar = ttk.Frame(parent, style="Modern.TFrame")
        toolbar.pack(fill=tk.X, pady=(0, 10))

        # Left side buttons
        left_frame = ttk.Frame(toolbar, style="Modern.TFrame")
        left_frame.pack(side=tk.LEFT)

        self.export_button = ttk.Button(left_frame,
                                        text="📊 Export to Excel",
                                        command=self.export_to_xlsx,
                                        style="Modern.TButton")
        self.export_button.pack(side=tk.LEFT, padx=(0, 10))

        # Right side buttons
        right_frame = ttk.Frame(toolbar, style="Modern.TFrame")
        right_frame.pack(side=tk.RIGHT)

        self.settings_button = ttk.Button(right_frame,
                                         text="⚙️ Settings",
                                         command=self.show_settings,
                                         style="Secondary.TButton")
        self.settings_button.pack(side=tk.RIGHT, padx=(0, 10))

        self.reset_button = ttk.Button(right_frame,
                                       text="🔄 Load New PDF",
                                       command=self.reset_ui,
                                       style="Secondary.TButton")
        self.reset_button.pack(side=tk.RIGHT)

    def show_progress_ui(self):
        """Show progress indicator"""
        # Clear content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # Progress card
        progress_card = ttk.Frame(self.content_frame, style="Card.TFrame")
        progress_card.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)

        # Progress content
        progress_content = ttk.Frame(progress_card, style="Modern.TFrame")
        progress_content.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # Progress icon
        icon_label = tk.Label(progress_content,
                              text="⚙️",
                              font=('Segoe UI', 48),
                              bg="#ffffff",
                              fg="#009DF0")
        icon_label.pack(pady=(0, 20))

        # Progress text
        progress_label = tk.Label(progress_content,
                                  text="Processing PDF...",
                                  font=('Segoe UI', 16),
                                  bg="#ffffff",
                                  fg="#495057")
        progress_label.pack()

        # Progress bar
        self.progress_bar = ttk.Progressbar(progress_content,
                                            variable=self.progress_var,
                                            maximum=100,
                                            length=400,
                                            style="Modern.Horizontal.TProgressbar")
        self.progress_bar.pack(pady=20)

        # Progress percentage
        self.progress_text = tk.Label(progress_content,
                                      text="0%",
                                      font=('Segoe UI', 12),
                                      bg="#ffffff",
                                      fg="#6c757d")
        self.progress_text.pack()

    def setup_drag_drop(self):
        """Setup drag and drop functionality"""
        if DRAG_DROP_AVAILABLE and hasattr(self, 'upload_card'):
            try:
                self.upload_card.drop_target_register(DND_FILES)
                self.upload_card.dnd_bind('<<Drop>>', self.on_drop)
                
                # Update the upload label to indicate drag-drop is active
                for widget in self.upload_card.winfo_children():
                    if isinstance(widget, ttk.Frame):
                        for child in widget.winfo_children():
                            if isinstance(child, tk.Label) and "Drag and drop" in child.cget("text"):
                                child.config(fg="#009DF0")  # Highlight to show it's active
            except Exception as e:
                print(f"Could not setup drag-and-drop: {e}")

    def on_drop(self, event):
        """Handle dropped files"""
        try:
            # Extract file path from drop event
            files = self.root.tk.splitlist(event.data)
            if files:
                file_path = files[0]  # Take the first file if multiple are dropped
                # Remove curly braces and quotes if present
                file_path = file_path.strip('{}').strip('"').strip("'")
                
                if file_path:
                    self.handle_file(file_path)
        except Exception as e:
            messagebox.showerror("Drop Error", f"Failed to process dropped file:\n{str(e)}")

    def browse_file(self):
        """Open file browser dialog"""
        file_path = filedialog.askopenfilename(
            title="Select PDF File",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")],
            initialdir=str(Path.home())
        )
        if file_path:
            self.handle_file(file_path)

    def handle_file(self, file_path):
        """Handle selected file"""
        if not file_path.lower().endswith('.pdf'):
            messagebox.showerror("Invalid File", "Please select a PDF file.")
            return

        self.status_var.set(f"Loading: {Path(file_path).name}")
        self.show_progress_ui()

        # Start processing in background thread
        threading.Thread(target=self.process_pdf, args=(file_path,), daemon=True).start()

    def process_pdf(self, file_path):
        """Process PDF file (mock implementation)"""
        try:
            # Process PDF with YOLO model
            import pandas as pd
            
            # Use the latest trained model weights
            model_path = "runs/detect/train_field_control_system/weights/best.pt"
            
            # Get current settings
            dpi = self.dpi_var.get()
            conf = self.conf_var.get()
            
            # Update status with settings info
            self.root.after(0, lambda: self.status_var.set(
                f"Processing with DPI={dpi}, Confidence={conf:.2f}..."
            ))
            
            # Process PDF and get detection results
            results = PDFProcessor_wo_ocr.process_pdf_with_yolo(
                pdf_path=file_path,
                yolo_model_path=model_path,
                out_json_path=None,  # Don't save JSON, just return results
                dpi=dpi,
                conf=conf,
                progress_callback=self.update_progress
            )
            
            # Convert results to DataFrame for display
            df = pd.DataFrame(results)
            
            # Prepare display columns
            display_data = []
            for _, row in df.iterrows():
                # Extract primary information
                class_name = row['class_name']
                primary_instrument = row.get('primary_instrument', 'Unknown')
                texts = row.get('texts_inside', [])
                instruments = row.get('instruments_recognized', [])
                
                # Extract coordinates for location display
                bbox_pdf = row.get('bbox_pdf', [0, 0, 0, 0])
                bbox_pixels = row.get('bbox_pixels', [0, 0, 0, 0])
                
                # Format coordinates as readable string (center point and dimensions)
                if bbox_pdf:
                    x0, y0, x1, y1 = bbox_pdf
                    center_x = round((x0 + x1) / 2, 1)
                    center_y = round((y0 + y1) / 2, 1)
                    width = round(x1 - x0, 1)
                    height = round(y1 - y0, 1)
                    location_str = f"({center_x}, {center_y}) | Size: {width}x{height}pt"
                else:
                    location_str = "N/A"
                
                # Build a readable text representation
                text_str = ', '.join(texts) if texts else 'No text'
                
                # Extract instrument details
                instrument_codes = []
                instrument_names = []
                tag_numbers = []
                
                for inst in instruments:
                    # Add code if recognized
                    if inst.get('code'):
                        instrument_codes.append(inst['code'])
                        instrument_names.append(inst['instrument_name'])
                    
                    # Add tag number only if it's not empty
                    if 'tag_number' in inst:
                        tag = inst['tag_number']
                        if tag:  # Only add if tag is not empty string
                            tag_numbers.append(tag)
                
                display_data.append({
                    'Component Type': class_name,
                    'Location': location_str,
                    'Detected Text': text_str,
                    'Instrument Code': ', '.join(instrument_codes) if instrument_codes else '-',
                    'Instrument Name': primary_instrument,
                    'Tag Numbers': ', '.join(tag_numbers) if tag_numbers else '-',
                    'Confidence': f"{row.get('conf_score', 0):.2f}" if 'conf_score' in row else 'N/A'
                })
            
            display_df = pd.DataFrame(display_data)

            self.current_df = display_df
            self.root.after(0, lambda: self.show_data_view(display_df))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to process PDF:\n{str(e)}"))
            self.root.after(0, self.show_upload_ui)

    def update_progress(self, percent):
        """Update progress bar"""
        self.progress_var.set(percent)
        if hasattr(self, 'progress_text'):
            self.progress_text.config(text=f"{percent}%")

    def export_to_xlsx(self):
        """Export data to Excel"""
        if self.current_df is None:
            messagebox.showerror("No Data", "No data available to export.")
            return

        file_path = filedialog.asksaveasfilename(
            title="Save Excel File",
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx"), ("All Files", "*.*")],
            initialdir=str(Path.home())
        )

        if file_path:
            try:
                self.current_df.to_excel(file_path, index=False)
                messagebox.showinfo("Success", f"Data exported successfully!\n{file_path}")
                self.status_var.set(f"Exported to: {Path(file_path).name}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export data:\n{str(e)}")

    def reset_ui(self):
        """Reset UI to initial state"""
        self.current_df = None
        self.progress_var.set(0)
        self.status_var.set("Ready")
        self.show_upload_ui()

    def show_settings(self):
        """Show settings dialog for DPI and confidence threshold"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Processing Settings")
        settings_window.geometry("400x300")
        settings_window.resizable(False, False)
        settings_window.configure(bg="#f8f9fa")
        
        # Center the window
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # Main frame
        main_frame = ttk.Frame(settings_window, style="Modern.TFrame", padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = tk.Label(main_frame,
                              text="Processing Settings",
                              font=('Segoe UI', 16, 'bold'),
                              bg="#f8f9fa",
                              fg="#212529")
        title_label.pack(pady=(0, 20))
        
        # DPI Setting
        dpi_frame = ttk.Frame(main_frame, style="Modern.TFrame")
        dpi_frame.pack(fill=tk.X, pady=10)
        
        dpi_label = tk.Label(dpi_frame,
                            text="PDF Rendering DPI:",
                            font=('Segoe UI', 10),
                            bg="#f8f9fa",
                            fg="#495057")
        dpi_label.pack(anchor=tk.W)
        
        dpi_info = tk.Label(dpi_frame,
                           text="Higher DPI = better quality but slower processing",
                           font=('Segoe UI', 8),
                           bg="#f8f9fa",
                           fg="#6c757d")
        dpi_info.pack(anchor=tk.W, pady=(2, 5))
        
        dpi_spinbox = ttk.Spinbox(dpi_frame,
                                  from_=150,
                                  to=600,
                                  increment=50,
                                  textvariable=self.dpi_var,
                                  width=10,
                                  font=('Segoe UI', 10))
        dpi_spinbox.pack(anchor=tk.W)
        
        # Confidence Threshold Setting
        conf_frame = ttk.Frame(main_frame, style="Modern.TFrame")
        conf_frame.pack(fill=tk.X, pady=10)
        
        conf_label = tk.Label(conf_frame,
                             text="Detection Confidence Threshold:",
                             font=('Segoe UI', 10),
                             bg="#f8f9fa",
                             fg="#495057")
        conf_label.pack(anchor=tk.W)
        
        conf_info = tk.Label(conf_frame,
                            text="Lower = more detections, Higher = fewer false positives",
                            font=('Segoe UI', 8),
                            bg="#f8f9fa",
                            fg="#6c757d")
        conf_info.pack(anchor=tk.W, pady=(2, 5))
        
        conf_scale_frame = ttk.Frame(conf_frame, style="Modern.TFrame")
        conf_scale_frame.pack(fill=tk.X)
        
        conf_scale = ttk.Scale(conf_scale_frame,
                              from_=0.1,
                              to=0.9,
                              variable=self.conf_var,
                              orient=tk.HORIZONTAL)
        conf_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        conf_value_label = tk.Label(conf_scale_frame,
                                    textvariable=self.conf_var,
                                    font=('Segoe UI', 10),
                                    bg="#f8f9fa",
                                    fg="#212529",
                                    width=5)
        conf_value_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Update label when scale changes
        def update_conf_label(*args):
            conf_value_label.config(text=f"{self.conf_var.get():.2f}")
        self.conf_var.trace_add('write', update_conf_label)
        update_conf_label()
        
        # Preset buttons
        preset_frame = ttk.Frame(main_frame, style="Modern.TFrame")
        preset_frame.pack(fill=tk.X, pady=20)
        
        preset_label = tk.Label(preset_frame,
                               text="Quick Presets:",
                               font=('Segoe UI', 10),
                               bg="#f8f9fa",
                               fg="#495057")
        preset_label.pack(anchor=tk.W, pady=(0, 5))
        
        preset_buttons_frame = ttk.Frame(preset_frame, style="Modern.TFrame")
        preset_buttons_frame.pack(fill=tk.X)
        
        def apply_preset(dpi, conf):
            self.dpi_var.set(dpi)
            self.conf_var.set(conf)
        
        ttk.Button(preset_buttons_frame,
                  text="Fast (200 DPI)",
                  command=lambda: apply_preset(200, 0.30),
                  style="Secondary.TButton").pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(preset_buttons_frame,
                  text="Balanced (300 DPI)",
                  command=lambda: apply_preset(300, 0.25),
                  style="Secondary.TButton").pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(preset_buttons_frame,
                  text="Quality (400 DPI)",
                  command=lambda: apply_preset(400, 0.20),
                  style="Secondary.TButton").pack(side=tk.LEFT)
        
        # Buttons
        button_frame = ttk.Frame(main_frame, style="Modern.TFrame")
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Button(button_frame,
                  text="Apply",
                  command=settings_window.destroy,
                  style="Modern.TButton").pack(side=tk.RIGHT, padx=(5, 0))
        
        ttk.Button(button_frame,
                  text="Cancel",
                  command=lambda: [self.dpi_var.set(300), self.conf_var.set(0.25), settings_window.destroy()],
                  style="Secondary.TButton").pack(side=tk.RIGHT)



if __name__ == "__main__":
    # Use TkinterDnD root if available for drag-and-drop support
    if DRAG_DROP_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    
    app = ModernPDFApp(root)
    root.mainloop()
