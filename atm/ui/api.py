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
            
        file_types = ('Executable Files (*.exe)', 'All files (*.*)')
        result = self.window.create_file_dialog(
            webview.OPEN_DIALOG, 
            allow_multiple=False, 
            file_types=file_types
        )
        
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
            
        # Emit event để Bootstrap bắt và chạy
        EventBus.publish(SystemEvents.GAME_STARTING, profile)
        return {"status": "success"}
        
    def delete_game(self, game_id: str):
        """Xóa game"""
        # (TODO: Thêm hàm delete trong repository nếu chưa có)
        try:
            self.profile_repo.delete(game_id)
            return {"status": "success"}
        except Exception as e:
            # Fallback nếu chưa implement delete trong repo
            profiles = self.profile_repo.get_all()
            profiles = [p for p in profiles if p.id != game_id]
            self.profile_repo._profiles = {p.id: p for p in profiles}
            self.profile_repo._save_all()
            return {"status": "success"}
