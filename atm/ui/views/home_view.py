import customtkinter as ctk

class HomeView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.label = ctk.CTkLabel(self, text="My Game Library", font=ctk.CTkFont(size=24, weight="bold"))
        self.label.pack(pady=20)
        
        # Placeholder cho danh sách game profile
        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.empty_label = ctk.CTkLabel(self.list_frame, text="No games found. Add a game to get started!")
        self.empty_label.pack(pady=50)
        
        self.btn_add = ctk.CTkButton(self, text="+ Add Game", command=self.add_game)
        self.btn_add.pack(pady=20)
        
    def add_game(self):
        # Mở dialog chọn file exe
        print("Add game clicked")
