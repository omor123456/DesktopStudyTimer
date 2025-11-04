import tkinter as tk
from tkinter import messagebox
import threading

# Minimal Pomodoro timer: UI thread for display, worker thread for countdown
class StudyTimer:
    def __init__(self, root):
        self.root = root
        self.root.title("Pomodoro Timer")
        self.root.config(bg="#2c3e50")
        
        # Purpose: Track timer state across threads
        self.time_left = 0
        self.timer_running = False
        
        self._build_ui()
    
    def _build_ui(self):
        """Purpose: Create input, display, and control buttons"""
        # Title
        tk.Label(self.root, text="Pomodoro Timer", font=("Arial", 24, "bold"),
                bg="#2c3e50", fg="white").pack(pady=20)
        
        # Input frame
        input_frame = tk.Frame(self.root, bg="#2c3e50")
        input_frame.pack(pady=15)
        
        tk.Label(input_frame, text="Minutes:", font=("Arial", 12),
                bg="#2c3e50", fg="white").grid(row=0, column=0, padx=10)
        
        # Purpose: Entry widget lets user type custom time
        self.minutes_entry = tk.Entry(input_frame, width=8, font=("Arial", 16),
                                     justify="center", bg="#34495e", fg="white")
        self.minutes_entry.insert(0, "25")  # Default Pomodoro time
        self.minutes_entry.grid(row=0, column=1, padx=10)
        self.minutes_entry.bind('<Return>', lambda e: self._start_timer())
        
        # Purpose: Label shows countdown in MM:SS format
        self.countdown_label = tk.Label(self.root, text="25:00",
                                       font=("Arial", 48, "bold"),
                                       bg="#2c3e50", fg="#3498db")
        self.countdown_label.pack(pady=30)
        
        # Purpose: Canvas draws progress bar without external libraries
        self.canvas = tk.Canvas(self.root, width=300, height=20,
                               bg="#34495e", highlightthickness=0)
        self.canvas.pack(pady=10)
        self.progress_bar = self.canvas.create_rectangle(0, 0, 0, 20,
                                                         fill="#27ae60", width=0)
        
        # Control buttons
        button_frame = tk.Frame(self.root, bg="#2c3e50")
        button_frame.pack(pady=20)
        
        self.start_btn = tk.Button(button_frame, text="Start",
                                   command=self._start_timer,
                                   font=("Arial", 14, "bold"),
                                   bg="#27ae60", fg="white", width=10)
        self.start_btn.grid(row=0, column=0, padx=8)
        
        tk.Button(button_frame, text="Stop", command=self._stop_timer,
                 font=("Arial", 14, "bold"), bg="#e74c3c",
                 fg="white", width=10).grid(row=0, column=1, padx=8)
    
    def _start_timer(self):
        """Purpose: Validate input and spawn countdown thread"""
        if self.timer_running:
            return
        
        try:
            mins = int(self.minutes_entry.get() or 0)
            
            if mins <= 0:
                messagebox.showerror("Error", "Enter minutes > 0")
                return
            
            # Purpose: Convert minutes to seconds for countdown
            self.time_left = mins * 60
            self.total_time = self.time_left
            self.timer_running = True
            
            # Purpose: Disable input during countdown to prevent changes
            self.start_btn.config(state="disabled")
            self.minutes_entry.config(state="disabled")
            
            # Purpose: Daemon thread exits automatically when app closes
            threading.Thread(target=self._countdown, daemon=True).start()
            
        except ValueError:
            messagebox.showerror("Error", "Enter valid number")
    
    def _countdown(self):
        """Purpose: Decrement timer every second in worker thread"""
        while self.time_left > 0 and self.timer_running:
            # Purpose: divmod() converts seconds to (minutes, seconds) tuple
            mins, secs = divmod(self.time_left, 60)
            
            # Purpose: Calculate progress as percentage of total time
            progress = 300 * (1 - self.time_left / self.total_time)
            
            # Purpose: after(0) schedules UI update on main thread (tkinter requirement)
            self.root.after(0, self._update_display, mins, secs, progress)
            
            # Purpose: threading.Event().wait(1) sleeps 1 second without blocking
            threading.Event().wait(1)
            self.time_left -= 1
        
        # Purpose: Only show completion if timer wasn't stopped early
        if self.time_left == 0 and self.timer_running:
            self.root.after(0, self._complete)
    
    def _update_display(self, mins, secs, progress):
        """Purpose: Update label and progress bar (called on main thread)"""
        # Purpose: :02d formats numbers with leading zeros (e.g., 5 -> 05)
        self.countdown_label.config(text=f"{mins:02d}:{secs:02d}")
        # Purpose: coords() moves rectangle's right edge to show progress
        self.canvas.coords(self.progress_bar, 0, 0, progress, 20)
    
    def _complete(self):
        """Purpose: Show completion message and reset UI"""
        self.timer_running = False
        self.countdown_label.config(text="Done! 🎉", fg="#2ecc71")
        messagebox.showinfo("Complete", "Pomodoro session finished!")
        self._reset()
    
    def _stop_timer(self):
        """Purpose: Stop countdown and reset UI"""
        self.timer_running = False
        self._reset()
    
    def _reset(self):
        """Purpose: Re-enable controls and restore initial display"""
        self.start_btn.config(state="normal")
        self.minutes_entry.config(state="normal")
        
        mins = int(self.minutes_entry.get() or 25)
        self.countdown_label.config(text=f"{mins:02d}:00", fg="#3498db")
        # Purpose: Reset progress bar to empty
        self.canvas.coords(self.progress_bar, 0, 0, 0, 20)
    
    def cleanup(self):
        """Purpose: Stop timer before closing app"""
        self.timer_running = False
        self.root.destroy()

# Purpose: __name__ check prevents execution when imported as module
if __name__ == "__main__":
    root = tk.Tk() # Create main window of the app without this we won't a visual window
    app = StudyTimer(root) # Instantiate the StudyTimer class with the main window
    root.protocol("WM_DELETE_WINDOW", app.cleanup)
    root.mainloop()
