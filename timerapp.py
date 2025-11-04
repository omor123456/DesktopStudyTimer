import tkinter as tk
from tkinter import messagebox
import sqlite3
from datetime import datetime
import threading

# Desktop timer app with SQLite persistence and threaded countdown
# Architecture: UI thread handles display, worker threads handle DB/timer logic
class StudyTimer:
    def __init__(self, root):
        self.root = root
        self.root.title("Study Timer")
        self.root.config(bg="#2c3e50")
        self.root.minsize(400, 450)
        
        # Purpose: Initialize DB connection before UI to ensure data layer ready
        self._init_db()
        
        # Purpose: Track timer state across threads (read by UI, modified by worker)
        self.time_left = 0
        self.timer_running = False
        self.start_time = None
        
        self._build_ui()
    
    def _init_db(self):
        """Purpose: Create SQLite connection with thread-safe flag for concurrent access"""
        self.conn = sqlite3.connect('study_sessions.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        # Purpose: Store completed sessions with actual vs planned duration for analytics
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                duration INTEGER NOT NULL,
                completed_at TEXT NOT NULL,
                actual_time REAL
            )
        ''')
        self.conn.commit()
    
    def _build_ui(self):
        """Purpose: Build all UI components in single method to avoid scattered initialization"""
        tk.Label(self.root, text="Study Timer", font=("Arial", 24, "bold"), 
                bg='#2c3e50', fg='white').pack(pady=15)
        
        # Purpose: Validation prevents non-numeric input that would crash int() conversion
        vcmd = (self.root.register(lambda v: v == "" or (v.isdigit() and 0 <= int(v) <= 999)), '%P')
        
        input_frame = tk.Frame(self.root, bg='#2c3e50')
        input_frame.pack(pady=15)
        
        tk.Label(input_frame, text="Minutes:", font=("Arial", 12), 
                bg='#2c3e50', fg='white').grid(row=0, column=0, padx=10)
        
        self.minutes_entry = tk.Entry(input_frame, width=8, font=("Arial", 16),
                                     validate='key', validatecommand=vcmd, justify='center',
                                     bg='#34495e', fg='white')
        self.minutes_entry.insert(0, "25")
        self.minutes_entry.grid(row=0, column=1, padx=10)
        # Purpose: Real-time display update improves UX by showing formatted time as user types
        self.minutes_entry.bind('<KeyRelease>', self._update_display_from_entry)
        self.minutes_entry.bind('<Return>', lambda e: self._start_timer())
        
        tk.Label(input_frame, text="Seconds:", font=("Arial", 12), 
                bg='#2c3e50', fg='white').grid(row=1, column=0, padx=10)
        
        self.seconds_entry = tk.Entry(input_frame, width=8, font=("Arial", 16),
                                      validate='key', validatecommand=vcmd, justify='center',
                                      bg='#34495e', fg='white')
        self.seconds_entry.insert(0, "0")
        self.seconds_entry.grid(row=1, column=1, padx=10)
        self.seconds_entry.bind('<KeyRelease>', self._update_display_from_entry)
        self.seconds_entry.bind('<Return>', lambda e: self._start_timer())
        
        self.countdown_label = tk.Label(self.root, text="25:00", font=("Arial", 48, "bold"), 
                                       bg='#2c3e50', fg='#3498db')
        self.countdown_label.pack(pady=20)
        
        # Purpose: Canvas progress bar avoids external dependencies (ttk.Progressbar)
        self.canvas = tk.Canvas(self.root, width=350, height=20, bg='#34495e', highlightthickness=0)
        self.canvas.pack(pady=10, padx=20)
        self.progress_bar = self.canvas.create_rectangle(0, 0, 0, 20, fill='#27ae60', width=0)
        
        button_frame = tk.Frame(self.root, bg='#2c3e50')
        button_frame.pack(pady=15)
        
        self.start_btn = tk.Button(button_frame, text="Start", command=self._start_timer, 
                                   font=("Arial", 14, "bold"), bg='#27ae60', fg='white', width=10)
        self.start_btn.grid(row=0, column=0, padx=8)
        
        tk.Button(button_frame, text="Stop", command=self._stop_timer, 
                 font=("Arial", 14, "bold"), bg='#e74c3c', fg='white', width=10).grid(row=0, column=1, padx=8)
        
        tk.Button(self.root, text="View History", command=self._show_history, 
                 font=("Arial", 12), bg='#9b59b6', fg='white', width=20).pack(pady=10)
        
        self.stats_label = tk.Label(self.root, text="", font=("Arial", 11, "bold"), 
                                   bg='#2c3e50', fg='#ecf0f1')
        self.stats_label.pack(pady=15)
        
        self._update_stats()
    
    def _update_display_from_entry(self, event=None):
        """Purpose: Sync countdown display with entry fields only when timer inactive"""
        if self.timer_running:
            return
        
        try:
            mins = int(self.minutes_entry.get() or 0)
            secs = int(self.seconds_entry.get() or 0)
            
            # Purpose: Auto-normalize seconds >= 60 to prevent confusion (e.g., 90s → 1m 30s)
            if secs >= 60:
                mins += secs // 60
                secs %= 60
                self.seconds_entry.delete(0, tk.END)
                self.seconds_entry.insert(0, str(secs))
                self.minutes_entry.delete(0, tk.END)
                self.minutes_entry.insert(0, str(mins))
            
            self.countdown_label.config(text=f"{mins:02d}:{secs:02d}")
        except ValueError:
            pass
    
    def _start_timer(self):
        """Purpose: Validate input and spawn worker thread to avoid blocking UI"""
        if self.timer_running:
            return
        
        try:
            mins = int(self.minutes_entry.get() or 0)
            secs = int(self.seconds_entry.get() or 0)
            self.time_left = mins * 60 + secs
            
            if self.time_left <= 0:
                messagebox.showerror("Invalid Time", "Enter time > 0")
                return
            
            self.total_time = self.time_left
            self.timer_running = True
            self.start_time = datetime.now()
            
            # Purpose: Disable inputs during countdown to prevent mid-timer changes
            self.start_btn.config(state='disabled')
            self.minutes_entry.config(state='disabled')
            self.seconds_entry.config(state='disabled')
            
            # Purpose: Daemon thread auto-exits on app close, preventing hang
            threading.Thread(target=self._run_timer, daemon=True).start()
        except ValueError:
            messagebox.showerror("Invalid Input", "Enter valid numbers")
    
    def _run_timer(self):
        """Purpose: Countdown loop in worker thread, schedule UI updates via after() for thread safety"""
        while self.time_left > 0 and self.timer_running:
            mins, secs = divmod(self.time_left, 60)
            
            # Purpose: Calculate progress as percentage of canvas width for smooth visual feedback
            width = self.canvas.winfo_width() or 350
            progress = width * (1 - self.time_left / self.total_time)
            
            # Purpose: after(0) schedules UI update on main thread, avoiding tkinter thread violations
            self.root.after(0, self._update_ui, mins, secs, progress)
            
            threading.Event().wait(1)  # Purpose: Sleep 1s without blocking other threads
            self.time_left -= 1
        
        # Purpose: Only trigger completion if timer wasn't manually stopped
        if self.time_left == 0 and self.timer_running:
            self.root.after(0, self._complete_session)
    
    def _update_ui(self, mins, secs, progress):
        """Purpose: Update label and progress bar on main thread (called via after())"""
        self.countdown_label.config(text=f"{mins:02d}:{secs:02d}")
        self.canvas.coords(self.progress_bar, 0, 0, progress, 20)
    
    def _complete_session(self):
        """Purpose: Handle completion logic and persist session data"""
        self.timer_running = False
        self.countdown_label.config(text="Done! 🎉", fg='#2ecc71')
        
        # Purpose: Track actual vs planned duration for user insights
        actual = (datetime.now() - self.start_time).total_seconds()
        threading.Thread(target=lambda: self._save_session(actual), daemon=True).start()
        
        messagebox.showinfo("Completed!", "Study session completed! 🎉")
        self._reset()
    
    def _stop_timer(self):
        """Purpose: Halt countdown and reset UI state"""
        self.timer_running = False
        self._reset()
    
    def _reset(self):
        """Purpose: Re-enable inputs and restore display to entry values"""
        self.start_btn.config(state='normal')
        self.minutes_entry.config(state='normal')
        self.seconds_entry.config(state='normal')
        
        mins = int(self.minutes_entry.get() or 25)
        secs = int(self.seconds_entry.get() or 0)
        self.countdown_label.config(text=f"{mins:02d}:{secs:02d}", fg='#3498db')
        self.canvas.coords(self.progress_bar, 0, 0, 0, 20)
        self._update_stats()
    
    def _save_session(self, actual_time):
        """Purpose: Insert completed session to DB in worker thread to avoid UI lag"""
        duration = int(self.minutes_entry.get() or 0) * 60 + int(self.seconds_entry.get() or 0)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        self.cursor.execute('INSERT INTO sessions (duration, completed_at, actual_time) VALUES (?, ?, ?)',
                           (duration, timestamp, actual_time))
        self.conn.commit()
        
        # Purpose: Refresh stats after save completes
        self.root.after(0, self._update_stats)
    
    def _update_stats(self):
        """Purpose: Query session totals and update stats label"""
        def fetch():
            self.cursor.execute('SELECT COUNT(*), SUM(duration) FROM sessions')
            count, total_secs = self.cursor.fetchone()
            count = count or 0
            total_secs = total_secs or 0
            
            hrs, mins = divmod(total_secs, 3600)
            mins //= 60
            
            self.root.after(0, lambda: self.stats_label.config(
                text=f"Total Sessions: {count} | Total Time: {hrs}h {mins}m"))
        
        threading.Thread(target=fetch, daemon=True).start()
    
    def _show_history(self):
        """Purpose: Fetch recent sessions and display with average duration"""
        def fetch():
            self.cursor.execute('SELECT duration, completed_at, actual_time FROM sessions ORDER BY id DESC LIMIT 15')
            sessions = self.cursor.fetchall()
            
            if not sessions:
                self.root.after(0, lambda: messagebox.showinfo("History", "No sessions yet! 📚"))
                return
            
            # Purpose: Calculate average to show user productivity trends
            avg = sum(s[0] for s in sessions) / len(sessions)
            text = f"📊 Recent Sessions (Avg: {avg/60:.1f} min)\n\n"
            
            for i, (dur, time, actual) in enumerate(sessions, 1):
                mins, secs = divmod(dur, 60)
                actual_str = f" (actual: {actual:.0f}s)" if actual else ""
                text += f"{i}. {mins}m {secs}s - {time}{actual_str}\n"
            
            self.root.after(0, lambda: messagebox.showinfo("History", text))
        
        threading.Thread(target=fetch, daemon=True).start()
    
    def on_closing(self):
        """Purpose: Clean shutdown - stop timer, close DB, destroy window"""
        self.timer_running = False
        self.conn.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = StudyTimer(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
