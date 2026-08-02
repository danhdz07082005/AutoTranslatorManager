import customtkinter as ctk
from atm.core.events.event_bus import EventBus, SystemEvents

class MainApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        
        self.title("Auto Translator Manager")
        self.geometry("900x600")
        
        # Grid layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # Sidebar
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="ATM Launcher", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        self.btn_library = ctk.CTkButton(self.sidebar_frame, text="Library", command=self.show_library)
        self.btn_library.grid(row=1, column=0, padx=20, pady=10)
        
        self.btn_history = ctk.CTkButton(self.sidebar_frame, text="History", command=self.show_history)
        self.btn_history.grid(row=2, column=0, padx=20, pady=10)
        
        self.btn_settings = ctk.CTkButton(self.sidebar_frame, text="Settings", command=self.show_settings)
        self.btn_settings.grid(row=3, column=0, padx=20, pady=10)
        
        # Main content area (placeholder for now)
        self.main_frame = ctk.CTkFrame(self, corner_radius=10)
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        
        self.content_label = ctk.CTkLabel(self.main_frame, text="Welcome to Auto Translator Manager!", font=ctk.CTkFont(size=24))
        self.content_label.pack(expand=True)
        
        # Subscribing to events to update UI
        EventBus.subscribe(SystemEvents.GAME_STARTING, self.on_game_starting)
        EventBus.subscribe(SystemEvents.CLEANUP_FINISHED, self.on_cleanup_finished)
        
    def show_library(self) -> None:
        self.content_label.configure(text="Game Library View (Coming soon)")
        
    def show_history(self) -> None:
        self.content_label.configure(text="Translation History View (Coming soon)")
        
    def show_settings(self) -> None:
        self.content_label.configure(text="Settings & Marketplace View (Coming soon)")
        
    def on_game_starting(self, data: any) -> None:
        self.content_label.configure(text=f"Deploying and Launching Game...\nPlease wait.")
        
    def on_cleanup_finished(self, data: any) -> None:
        self.content_label.configure(text="Game exited. Cleanup finished.\nReady.")
