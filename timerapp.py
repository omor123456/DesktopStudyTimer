import tkinter as tk
from tkinter import messagebox
import sqlite3
from datetime import datetime
import threading

class StudyTimer:
    def __init__(self, root):
        self.root = root
        self.root.title("Study Timer - Optimized")
        
        # Auto-scale window - remove fixed geometry
        self.root.config(bg="#2c3e50")
        
        # Initialize database
        self.init_database()
        
        # Timer variables
        self.time_left = 0
        self.timer_running = False
        self.timer_thread = None
        self.start_time = None
        
        self._build_ui()
        
        # Allow window resizing
        self.root.resizable(True, True)
        
        # Set minimum window size
        self.root.minsize(400, 450)
        
        # Auto-fit to content
        self.root.update_idletasks()
        
    def _build_ui(self):
        # Title Label
        title = tk.Label(self.root, text="Study Timer", font=("Arial", 24, "bold"), 
                        bg='#2c3e50', fg='white')
        title.pack(pady=15, fill='x')
        
        # Instructions
        instruction = tk.Label(self.root, text="Set your study time:", 
                              font=("Arial", 12), bg='#2c3e50', fg='white')
        instruction.pack(pady=8)
        
        # Frame for manual time input
        input_frame = tk.Frame(self.root, bg='#2c3e50')
        input_frame.pack(pady=15)
        
        # Validation command for Entry - only allows digits
        vcmd = (self.root.register(self._validate_number), '%P')
        
        # Minutes input
        min_label = tk.Label(input_frame, text="Minutes:", 
                            font=("Arial", 12), bg='#2c3e50', fg='white')
        min_label.grid(row=0, column=0, padx=10, pady=5)
        
        self.minutes_entry = tk.Entry(input_frame, width=8, font=("Arial", 16),
                                     validate='key', validatecommand=vcmd,
                                     justify='center', bg='#34495e', fg='white',
                                     insertbackground='white')
        self.minutes_entry.insert(0, "25")
        self.minutes_entry.grid(row=0, column=1, padx=10, pady=5)
        self.minutes_entry.bind('<KeyRelease>', self._update_display_from_entry)
        self.minutes_entry.bind('<FocusIn>', self._on_entry_focus_in)
        
        # Seconds input
        sec_label = tk.Label(input_frame, text="Seconds:", 
                            font=("Arial", 12), bg='#2c3e50', fg='white')
        sec_label.grid(row=1, column=0, padx=10, pady=5)
        
        self.seconds_entry = tk.Entry(input_frame, width=8, font=("Arial", 16),
                                      validate='key', validatecommand=vcmd,
                                      justify='center', bg='#34495e', fg='white',
                                      insertbackground='white')
        self.seconds_entry.insert(0, "0")
        self.seconds_entry.grid(row=1, column=1, padx=10, pady=5)
        self.seconds_entry.bind('<KeyRelease>', self._update_display_from_entry)
        self.seconds_entry.bind('<FocusIn>', self._on_entry_focus_in)
        
        # Helper text
        helper = tk.Label(self.root, text="Press Enter or click Start to begin", 
                         font=("Arial", 9, "italic"), bg='#2c3e50', fg='#95a5a6')
        helper.pack(pady=5)
        
        # Countdown display
        self.countdown_label = tk.Label(self.root, text="25:00", 
                                       font=("Arial", 48, "bold"), 
                                       bg='#2c3e50', fg='#3498db')
        self.countdown_label.pack(pady=20, fill='x')
        
        # Progress bar using Canvas
        self.canvas = tk.Canvas(self.root, width=350, height=20, 
                               bg='#34495e', highlightthickness=0)
        self.canvas.pack(pady=10, padx=20, fill='x', expand=False)
        self.progress_bar = self.canvas.create_rectangle(0, 0, 0, 20, 
                                                         fill='#27ae60', width=0)
        
        # Buttons frame
        button_frame = tk.Frame(self.root, bg='#2c3e50')
        button_frame.pack(pady=15)
        
        # Start button
        self.start_btn = tk.Button(button_frame, text="Start", 
                                   command=self._start_timer_thread, 
                                   font=("Arial", 14, "bold"), bg='#27ae60', 
                                   fg='white', width=10, height=1,
                                   activebackground='#229954')
        self.start_btn.grid(row=0, column=0, padx=8)
        
        # Stop button
        self.stop_btn = tk.Button(button_frame, text="Stop", 
                                  command=self.stop_timer, 
                                  font=("Arial", 14, "bold"), bg='#e74c3c', 
                                  fg='white', width=10, height=1,
                                  activebackground='#c0392b')
        self.stop_btn.grid(row=0, column=1, padx=8)
        
        # View history button
        history_btn = tk.Button(self.root, text="View History", 
                               command=self._show_history_thread, 
                               font=("Arial", 12), bg='#9b59b6', 
                               fg='white', width=20,
                               activebackground='#7d3c98')
        history_btn.pack(pady=10)
        
        # Stats label
        self.stats_label = tk.Label(self.root, text="Total sessions: 0", 
                                   font=("Arial", 11, "bold"), bg='#2c3e50', fg='#ecf0f1')
        self.stats_label.pack(pady=15, fill='x')
        
        # Bind Enter key to start timer
        self.minutes_entry.bind('<Return>', lambda e: self._start_timer_thread())
        self.seconds_entry.bind('<Return>', lambda e: self._start_timer_thread())
        
        self._update_stats()
    
    def _validate_number(self, value):
        """Validate that input is a number or empty"""
        if value == "":
            return True
        try:
            if 0 <= int(value) <= 999:
                return True
            return False
        except ValueError:
            return False
    
    def _on_entry_focus_in(self, event):
        """Select all text when entry gains focus"""
        event.widget.select_range(0, tk.END)
        event.widget.icursor(tk.END)
    
    def _update_display_from_entry(self, event=None):
        """Update countdown display when Entry values change"""
        if not self.timer_running:
            try:
                minutes = int(self.minutes_entry.get() or 0)
                seconds = int(self.seconds_entry.get() or 0)
                
                # Auto-convert seconds to minutes if >= 60
                if seconds >= 60:
                    minutes += seconds // 60
                    seconds = seconds % 60
                    self.seconds_entry.delete(0, tk.END)
                    self.seconds_entry.insert(0, str(seconds))
                    self.minutes_entry.delete(0, tk.END)
                    self.minutes_entry.insert(0, str(minutes))
                
                self.countdown_label.config(text=f"{minutes:02d}:{seconds:02d}")
            except:
                pass
    
    def init_database(self):
        """Initialize SQLite database"""
        self.conn = sqlite3.connect('study_sessions.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                duration INTEGER NOT NULL,
                completed_at TEXT NOT NULL,
                actual_time REAL
            )
        ''')
        self.conn.commit()
    
    def _start_timer_thread(self):
        """Start timer in separate thread"""
        if not self.timer_running:
            try:
                minutes = int(self.minutes_entry.get() or 0)
                seconds = int(self.seconds_entry.get() or 0)
                
                self.time_left = minutes * 60 + seconds
                
                if self.time_left <= 0:
                    messagebox.showerror("Invalid Time", "Please enter a valid time greater than 0!")
                    return
                
                self.total_time = self.time_left
                self.timer_running = True
                self.start_time = datetime.now()
                
                # Disable inputs
                self.start_btn.config(state='disabled')
                self.minutes_entry.config(state='disabled')
                self.seconds_entry.config(state='disabled')
                
                # Start timer thread
                self.timer_thread = threading.Thread(target=self._run_timer, daemon=True)
                self.timer_thread.start()
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter valid numbers!")
    
    def _run_timer(self):
        """Timer logic running in separate thread"""
        while self.time_left > 0 and self.timer_running:
            minutes = self.time_left // 60
            seconds = self.time_left % 60
            
            # Calculate progress percentage dynamically
            canvas_width = self.canvas.winfo_width() or 350
            progress = min(canvas_width * (1 - self.time_left / self.total_time), canvas_width)
            
            # Schedule UI updates on main thread (thread-safe)
            self.root.after(0, self._update_display, minutes, seconds, progress)
            
            threading.Event().wait(1)
            self.time_left -= 1
        
        if self.time_left == 0 and self.timer_running:
            self.root.after(0, self._timer_complete)
    
    def _update_display(self, minutes, seconds, progress):
        """Update UI elements - called from main thread"""
        self.countdown_label.config(text=f"{minutes:02d}:{seconds:02d}")
        self.canvas.coords(self.progress_bar, 0, 0, progress, 20)
    
    def _timer_complete(self):
        """Handle timer completion"""
        self.timer_running = False
        self.countdown_label.config(text="Done! 🎉", fg='#2ecc71')
        
        # Calculate actual time
        end_time = datetime.now()
        actual_duration = (end_time - self.start_time).total_seconds()
        
        self._save_session_thread(actual_duration)
        messagebox.showinfo("Completed!", "Great job! Study session completed! 🎉")
        self.reset_timer()
    
    def stop_timer(self):
        """Stop the timer"""
        self.timer_running = False
        if self.timer_thread and self.timer_thread.is_alive():
            self.timer_thread.join(timeout=1)
        self.reset_timer()
    
    def reset_timer(self):
        """Reset timer to initial state"""
        self.start_btn.config(state='normal')
        self.minutes_entry.config(state='normal')
        self.seconds_entry.config(state='normal')
        
        minutes = int(self.minutes_entry.get() or 25)
        seconds = int(self.seconds_entry.get() or 0)
        self.countdown_label.config(text=f"{minutes:02d}:{seconds:02d}", fg='#3498db')
        self.canvas.coords(self.progress_bar, 0, 0, 0, 20)
        self._update_stats()
    
    def _save_session_thread(self, actual_time):
        """Save session in separate thread"""
        def save():
            minutes = int(self.minutes_entry.get() or 0)
            seconds = int(self.seconds_entry.get() or 0)
            duration = minutes * 60 + seconds
            completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            self.cursor.execute('''
                INSERT INTO sessions (duration, completed_at, actual_time) 
                VALUES (?, ?, ?)
            ''', (duration, completed_at, actual_time))
            self.conn.commit()
            
            self.root.after(0, self._update_stats)
        
        threading.Thread(target=save, daemon=True).start()
    
    def _update_stats(self):
        """Update statistics display"""
        def calculate():
            self.cursor.execute('SELECT COUNT(*), SUM(duration) FROM sessions')
            result = self.cursor.fetchone()
            count = result[0] or 0
            total_seconds = result[1] or 0
            
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            
            self.root.after(0, lambda: self.stats_label.config(
                text=f"Total Sessions: {count} | Total Time: {hours}h {minutes}m"))
        
        threading.Thread(target=calculate, daemon=True).start()
    
    def _show_history_thread(self):
        """Show history in separate thread"""
        def fetch_and_display():
            self.cursor.execute('''
                SELECT duration, completed_at, actual_time 
                FROM sessions 
                ORDER BY id DESC 
                LIMIT 15
            ''')
            sessions = self.cursor.fetchall()
            
            if sessions:
                durations = [s[0] for s in sessions]
                avg_duration = sum(durations) / len(durations)
                
                history_text = f"📊 Recent Sessions (Avg: {avg_duration/60:.1f} min)\n\n"
                for i, session in enumerate(sessions, 1):
                    mins = session[0] // 60
                    secs = session[0] % 60
                    actual = f" (actual: {session[2]:.0f}s)" if session[2] else ""
                    history_text += f"{i}. {mins}m {secs}s - {session[1]}{actual}\n"
                
                self.root.after(0, lambda: messagebox.showinfo("Study History", history_text))
            else:
                self.root.after(0, lambda: messagebox.showinfo("Study History", 
                                                               "No sessions recorded yet!\nStart your first study session! 📚"))
        
        threading.Thread(target=fetch_and_display, daemon=True).start()
    
    def on_closing(self):
        """Clean up resources on exit"""
        self.timer_running = False
        if self.timer_thread and self.timer_thread.is_alive():
            self.timer_thread.join(timeout=1)
        self.conn.close()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = StudyTimer(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
