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
        from tkinter import filedialog
        import os
        from atm.config.schema import GameProfile
        from atm.storage.repositories.profile_repository import ProfileRepository
        
        # Mở hộp thoại chọn file exe
        file_path = filedialog.askopenfilename(
            title="Chọn file chạy của Game (.exe)",
            filetypes=[("Executable Files", "*.exe"), ("All Files", "*.*")]
        )
        
        if file_path:
            game_name = os.path.basename(os.path.dirname(file_path))
            if not game_name:
                game_name = "Unknown Game"
                
            # Tạo profile mới
            profile = GameProfile(
                game_name=game_name,
                exe_path=file_path,
                engine="Unknown", # Sẽ được detect sau
                translator="google",
                input_lang="ja",
                output_lang="vi"
            )
            
            repo = ProfileRepository()
            repo.save(profile)
            
            # Cập nhật UI (tạm thời thay đổi text để báo thành công)
            self.empty_label.configure(text=f"Đã thêm game: {game_name}\nĐường dẫn: {file_path}")
            # TODO: Cần vẽ lại danh sách game

