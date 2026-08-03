import os
import uuid
import webview
from atm.storage.repositories.profile_repository import ProfileRepository
from atm.config.schema import GameProfile
from atm.core.detectors.game_detector import GameDetector
from atm.core.events.event_bus import EventBus, SystemEvents

class BackendApi:
    def __init__(self):
        self.profile_repo = ProfileRepository()
        self.window = None
        self.active_deployers = {} # game_id -> deployer

    def set_window(self, window):
        self.window = window

    def get_games(self):
        """Trả về danh sách game profile cho JS"""
        profiles = self.profile_repo.get_all()
        return [p.model_dump() for p in profiles]

    def add_game(self):
        """Mở hộp thoại file, tạo profile và trả về kết quả"""
        if not self.window:
            return {"error": "Window not initialized"}
            
        import tkinter as tk
        from tkinter import filedialog
        
        # Tạo hidden window để dùng filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        file_path = filedialog.askopenfilename(
            title="Chọn file chạy của Game (.exe)",
            filetypes=[("Executable Files", "*.exe"), ("All files", "*.*")]
        )
        root.destroy()
        
        if file_path:
            # Sửa lại thành list để xử lý bên dưới (để tương thích với logic cũ)
            result = [file_path]
        else:
            result = None
        
        if result and len(result) > 0:
            file_path = result[0]
            game_name = os.path.basename(os.path.dirname(file_path))
            if not game_name:
                game_name = "Unknown Game"
                
            engine = GameDetector.detect_engine(file_path)
            
            profile = GameProfile(
                id=str(uuid.uuid4()),
                game_name=game_name,
                exe_path=file_path,
                engine=engine,
                translator="google",
                input_lang="ja",
                output_lang="vi"
            )
            
            self.profile_repo.save(profile)
            return {"status": "success", "game": profile.model_dump()}
            
        return None # User cancelled

    def start_game(self, game_id: str):
        """Khởi chạy game"""
        profile = self.profile_repo.get_by_id(game_id)
        if not profile:
            return {"status": "error", "error": "Game profile not found"}
            
        from atm.core.deployment.game_deployer import GameDeployer
        
        payload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "payloads", "bepinex")
        
        if not os.path.exists(payload_dir):
            return {"status": "error", "error": f"Chưa cài đặt Payload (BepInEx). Xin hãy tạo thư mục {payload_dir} và cho file vào!"}
            
        deployer = GameDeployer()
        self.active_deployers[game_id] = deployer
        deployer.deploy_and_launch(profile, payload_dir)
        return {"status": "success"}
        
    def stop_game(self, game_id: str):
        if game_id in self.active_deployers:
            deployer = self.active_deployers[game_id]
            deployer.monitor.stop()
            del self.active_deployers[game_id]
        return {"status": "success"}
        
    def delete_game(self, game_id: str):
        """Xóa game"""
        # (TODO: Thêm hàm delete trong repository nếu chưa có)
        try:
            # Fallback xoá triệt để: Xóa bằng ID và tìm cả tên cũ
            profiles = self.profile_repo.get_all()
            for p in profiles:
                if p.id == game_id:
                    self.profile_repo.delete(p.id)
                    # Thử xoá cả tên cũ
                    safe_name = "".join(c for c in p.game_name if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')
                    old_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "profiles", f"{safe_name}.json")
                    if os.path.exists(old_path):
                        os.remove(old_path)
                    
                    new_profiles = [prof for prof in profiles if prof.id != game_id]
                    self.profile_repo._profiles = {prof.id: prof for prof in new_profiles}
                    return {"status": "success"}
            return {"status": "error", "error": "Game not found"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
