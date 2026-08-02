import customtkinter as ctk

class HistoryView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.label = ctk.CTkLabel(self, text="Translation History", font=ctk.CTkFont(size=24, weight="bold"))
        self.label.pack(pady=20)
        
        # Area để hiện list game có log
        self.log_frame = ctk.CTkScrollableFrame(self)
        self.log_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.info_label = ctk.CTkLabel(self.log_frame, text="Synced translation logs will appear here.")
        self.info_label.pack(pady=20)
