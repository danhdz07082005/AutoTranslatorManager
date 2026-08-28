import os
from pathlib import Path

def generate_docs():
    base_dir = Path("D:/game/l/gvnvh/gvngv2/4/AutoTranslatorManager")
    out_dir = Path("D:/game/l/gvnvh/gvngv2/4")
    
    ignore_dirs = {".git", "__pycache__", "venv", "node_modules", "logs", "data", "tests", "build", ".pytest_cache", "scratch"}
    ignore_files = {".DS_Store"}
    
    files_fe = []
    files_be = []
    files_other = []
    files_md = []
    
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for f in files:
            if f in ignore_files:
                continue
            
            p = Path(root) / f
            ext = p.suffix.lower()
            rel_path = p.relative_to(base_dir.parent)
            
            if ext in [".html", ".css", ".js"]:
                files_fe.append((rel_path, p))
            elif ext == ".py":
                files_be.append((rel_path, p))
            elif ext == ".md":
                files_md.append((rel_path, p))
            elif ext in [".json", ".yaml", ".bat", ".ini", ".txt", ".gitignore"] or not ext:
                if "requirements" in p.name or "gitignore" in p.name or "bat" in p.name or ".json" in p.name or "doorstop" in p.name:
                    files_other.append((rel_path, p))
    
    def write_collection(out_name, file_list):
        out_path = out_dir / out_name
        with open(out_path, "w", encoding="utf-8") as out_f:
            for rel_path, abs_path in file_list:
                out_f.write(f"File: {rel_path}\n")
                out_f.write("="*len(f"File: {rel_path}") + "\n")
                try:
                    with open(abs_path, "r", encoding="utf-8") as in_f:
                        out_f.write(in_f.read())
                except Exception as e:
                    try:
                        with open(abs_path, "r", encoding="utf-8-sig") as in_f:
                            out_f.write(in_f.read())
                    except:
                        out_f.write(f"// ERROR READING CONTENT: {e}")
                out_f.write("\n\n")

    write_collection("1_fe_code.txt", files_fe)
    write_collection("2_be_code.txt", files_be)
    write_collection("3_other_code.txt", files_other)
    write_collection("4_md_code.txt", files_md)
    
    flow_content = """# B\u00ed k\u00edp v\u00f5 c\u00f4ng: Auto Translator Manager System Flow
    
## 1. T\u1ed5ng quan ki\u1ebfn tr\u00fac
- **Frontend**: HTML/JS/CSS thu\u1ea7n v\u1edbi Vanilla JS v\u00e0 BootStrap. T\u01b0\u01a1ng t\u00e1c th\u00f4ng qua HTTP Fetch.
- **Backend Server**: Python HTTP Server (`http.server` v\u00e0 custom API router). Ch\u1ecbu tr\u00e1ch nhi\u1ec7m redirect y\u00eau c\u1ea7u v\u00e0o c\u00e1c API endpoints t\u1ea1i `BackendApi`.
- **Core (Backend)**: G\u1ed3m c\u00e1c th\u00e0nh ph\u1ea7n \u0111\u1ed9c l\u1eadp (JobManager, ProcessMonitor, GameDeployer, TranslationCache).
- **Database**: L\u01b0u tr\u1eef ho\u00e0n to\u00e0n tr\u00ean c\u00e1c file `.json` local.

## 2. Lu\u1ed3ng Ch\u1ea1y Kh\u1edfi \u0110\u1ed9ng (Startup Flow)
1. **User g\u1ecdi `start.bat`:** B\u1eadt m\u00f4i tr\u01b0\u1eddng Python v\u00e0 kh\u1edfi \u0111\u1ed9ng `main.py`.
2. **Kh\u1edfi t\u1ea1o (`main.py`)**: `bootstrap_app()` s\u1ebd d\u1ecdn d\u1eb9p th\u01b0 m\u1ee5c r\u00e1c, thi\u1ebft l\u1eadp t\u1eadp tin `data/` v\u00e0 `logs/` n\u1ebfu ch\u01b0a c\u00f3.
3. **C\u1ea5p c\u1ed5ng Port ng\u1eabu nhi\u00ean**: T\u1ea1o Socket r\u1ed7ng \u0111\u1ec3 OS c\u1ea5p m\u1ed9t Port an to\u00e0n (tr\u00e1nh xung \u0111\u1ed9t port) sau \u0111\u00f3 set v\u00e0o bi\u1ebfn m\u00f4i tr\u01b0\u1eddng `ATM_SERVER_PORT`.
4. **B\u1eadt HTTP Server**: B\u1eadt 1 thread (Daemon) \u0111\u1ec3 ch\u1ea1y instance `http.server`.
5. **M\u1edf tr\u00ecnh duy\u1ec7t**: T\u1ef1 \u0111\u1ed9ng b\u1eadt UI qua URL: `http://127.0.0.1:<port>`.
6. **M\u00e0n h\u00ecnh Hello**: Frontend `index.html` hi\u1ec3n th\u1ecb Splash Screen b\u1eb1ng CSS \u0111\u1ebfm l\u00f9i 3 gi\u00e2y `setTimeout`, r\u1ed3i chuy\u1ec3n Fade Out v\u00e0 hi\u1ec3n th\u1ecb trang ch\u1ee7.
7. **\u0110\u1ed3ng b\u1ed9 n\u1ec1n**: Frontend b\u1eafn fetch calls GET l\u1ea5y danh s\u00e1ch `games` v\u00e0 render UI (c\u00e1c \u00f4 Cards Game).

## 3. Danh S\u00e1ch API - C\u00e1c Endpoints & Tham S\u1ed1

### 3.1. H\u1ec7 Th\u1ed1ng v\u00e0 C\u1ea5u h\u00ecnh
- **`GET /api/languages`**: L\u1ea5y ng\u00f4n ng\u1eef (kh\u00f4ng c\u1ea7n param).
- **`GET /api/settings`**: L\u1ea5y to\u00e0n b\u1ed9 c\u1ea5u h\u00ecnh t\u1eeb `config.json`.
- **`POST /api/settings/update`**: L\u01b0u m\u1ed9t setting c\u1ee5 th\u1ec3. Params JSON: `{"deepl_api_key": "...", "log_level": "..."}`.

### 3.2. Qu\u1ea3n L\u00fd Game
- **`GET /api/games`**: L\u1ea5y List Games.
- **`POST /api/games/add`**: Kh\u00f4ng tham s\u1ed1, Server s\u1ebd g\u1ecdi `tkinter` \u0111\u1ec3 hi\u1ec7n pop-up File Dialog b\u1eaft ch\u1ecdn Game `.exe`.
- **`POST /api/games/<game_id>/update`**: C\u1eadp nh\u1eadt settings. Params JSON: `{"input_lang": "auto", "output_lang": "vi", "translator": "google"}`.
- **`DELETE /api/games/<game_id>`**: Xo\u00e1 game b\u1ecfi `games.json`.

### 3.3. Start, Stop, Play (Real-time translation)
- **`POST /api/games/<game_id>/start`**: B\u1eadt game K\u00c8M AUTO-TRANSLATE.
- **`POST /api/games/<game_id>/play`**: Ch\u1ec9 b\u1eadt game Vanilla.
- **`POST /api/games/<game_id>/stop`**: T\u1eaft game v\u00e0 t\u1ef1 d\u1ecdn r\u00e1c payload.
- **`GET /api/games/<game_id>/status`**: Return: `{"status": "running/idle/stopped", "log": ["..."]}`.

### 3.4. Offline Extract/Translate (RPGMaker / RenPy)
- **`GET /api/games/<game_id>/coverage`**: T\u00ednh ph\u1ea7n tr\u0103m d\u1ecbch offline.
- **`POST /api/games/<game_id>/extract`**: T\u1ea1o Task (Job) \u0111\u1ec3 Parse text JSON c\u1ee7a game (Tr\u1ea3 v\u1ec1 `{"job_id": "..."}`).
- **`POST /api/games/<game_id>/patch`**: T\u1ea1o Task b\u1eafn request H\u00e0ng \u0110\u1ee3i d\u1ecbch API Google sau \u0111\u00f3 inject ng\u01b0\u1ee3c file v\u00e0o game.
- **`GET /api/jobs/<job_id>`**: Polling m\u1ed7i 500ms d\u01b0\u1edbi FE. Return: `{"status": "Running", "current": 10, "total": 100, "log": "..."}`.
- **`POST /api/jobs/<job_id>/cancel`**: H\u1ee7y Job.

### 3.5. D\u1eef Li\u1ec7u v\u00e0 Glossary (Thu\u1eadt ng\u1eef)
- **`GET /api/data/cache`**: URL Params: `?q=&page=&limit=`.
- **`POST /api/data/cache/update`**: S\u1eeda Translation Memory. Params JSON: `{"game_id": "...", "key": "...", "value": "..."}`.
- **`GET /api/data/stats`**: Tr\u1ea3 v\u1ec1 th\u1ed1ng k\u00ea text \u0111\u00e3 d\u1ecbch.
- **`POST /api/data/glossary/import/preview`**: Tham s\u1ed1 JSON: `{"content": "...", "format_type": "csv"}`.
- **`POST /api/data/glossary/import/apply`**: Áp dụng Preview list (ghi \u0111\u00e8 ho\u1eb7c n\u1ed1i ti\u1ebfp v\u00e0o file glossary c\u1ee7a game).
- **`POST /api/data/clear`**: D\u1ecdn s\u1ea1ch b\u1ed9 nh\u1edb ti\u1ebfm \u1ea9n (`{"clear_type": "global/game"}`).

## 4. Lu\u1ed3ng Injection Core & Qu\u00e1 tr\u00ecnh s\u1eeda b\u1ec7nh "M\u00f9 Ch\u1eef" (Love Confessions)
1. **Game b\u1ea5m Start**, h\u1ec7 th\u1ed1ng s\u1ebd detect engine (Unity/RPG Maker/Renpy) th\u00f4ng qua Pattern Recognition (`GameDetector`).
2. S\u1eed d\u1ee5ng `GameDeployer`, ATM l\u1ea5y payload t\u01b0\u01a1ng \u1ee9ng t\u1eeb th\u01b0 m\u1ee5c `resources/payloads`.
3. V\u1edbi **Unity**, ATM th\u00eam th\u01b0 m\u1ee5c BepInEx, sinh `AutoTranslatorConfig.ini`. Tr\u01b0\u1edbc \u0111\u00e2y INI g\u1eb7p l\u1ed7i Hardcode ép `FromLanguage=ja` n\u1ebfu user ch\u1ecdn `auto`, \u0111\u1ed3ng th\u1eddi thi\u1ebfu to\u00e0n b\u1ed9 block `[TextFrameworks]`. \u0110i\u1ec1u n\u00e0y g\u00e2y "m\u00f9 ch\u1eef" cho game l\u1ea1 d\u00f9ng ti\u1ebfng Anh. Hi\u1ec7n t\u1ea1i \u0111\u00e3 \u0111\u01b0\u1ee3c fix s\u1eed d\u1ee5ng `FromLanguage=auto` chu\u1ea9n x\u00e1c, bật c\u00e1c hook nh\u01b0 `EnableIMGUI`, `EnableNGUI`, s\u1eed d\u1ee5ng Endpoint RPC `GoogleTranslate` k\u00e8m Batching/MinDialogueChars, gi\u00fap hi\u1ec7u su\u1ea5t v\u00e0 \u0111\u1ed9 \u1ed5n \u0111\u1ecbnh s\u00e1nh ngang v\u1edbi k\u1ef7 l\u1ee5c 3s c\u1ee7a "DichTrucTiep".
4. Kh\u1edfi t\u1ea1o `ProcessMonitor` \u0111\u1ec3 gi\u00e1m s\u00e1t c\u00e2y ti\u1ebfn tr\u00ecnh.
5. Khi ph\u00e1t hi\u1ec7n ti\u1ebfn tr\u00ecnh d\u1eebng l\u1ea1i, b\u1eadt CallBack `cleanup`. Xo\u00e1 s\u1ea1ch \u1ee9ng d\u1ee5ng \u0111\u00e3 inject v\u00e0 \u0111\u1ed3ng b\u1ed9 ng\u01b0\u1ee3c file l\u1ecbch s\u1eed d\u1ecbch v\u00e0o database v\u00e0 copy `LogOutput.log` v\u1ec1 local \u0111\u1ec3 d\u1ec5 d\u00e0ng b\u1eaft l\u1ed7i l\u1ea7n sau.
"""
    
    with open(out_dir / "5_system_flow.md", "w", encoding="utf-8") as f:
        f.write(flow_content)

if __name__ == "__main__":
    generate_docs()
    print("Done generating 5 documentation files.")
