import csv
import json
import io
from typing import List, Dict, Any
from atm.storage.repositories.profile_repository import ProfileRepository

class GlossaryManager:
    def __init__(self, profile_repo: ProfileRepository):
        self.profile_repo = profile_repo

    def export_glossary(self, game_id: str, format_type: str = 'csv') -> str:
        profile = self.profile_repo.get_by_id(game_id)
        if not profile:
            raise ValueError("Game not found")

        glossary = profile.glossary or {}
        
        if format_type == 'json':
            return json.dumps([{"source": k, "target": v} for k, v in glossary.items()], ensure_ascii=False, indent=2)
        elif format_type == 'csv':
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['source', 'target', 'notes'])
            for k, v in glossary.items():
                writer.writerow([k, v, ''])
            return output.getvalue()
        else:
            raise ValueError("Unsupported format")

    def preview_import(self, game_id: str, content: str, format_type: str) -> Dict[str, Any]:
        profile = self.profile_repo.get_by_id(game_id)
        if not profile:
            raise ValueError("Game not found")

        existing_glossary = profile.glossary or {}
        
        parsed_entries = []
        if format_type == 'json':
            try:
                data = json.loads(content)
                for item in data:
                    parsed_entries.append({"source": item['source'], "target": item['target']})
            except Exception as e:
                raise ValueError(f"Invalid JSON: {e}")
        elif format_type == 'csv':
            try:
                reader = csv.DictReader(io.StringIO(content))
                for row in reader:
                    parsed_entries.append({"source": row.get('source', ''), "target": row.get('target', '')})
            except Exception as e:
                raise ValueError(f"Invalid CSV: {e}")
                
        preview_results = {
            "new": [],
            "conflict": [],
            "duplicate": [],
            "invalid": []
        }
        
        for entry in parsed_entries:
            src = entry.get("source")
            tgt = entry.get("target")
            if not src or not tgt:
                preview_results["invalid"].append(entry)
                continue
                
            if src in existing_glossary:
                existing_tgt = existing_glossary[src]
                if existing_tgt == tgt:
                    preview_results["duplicate"].append(entry)
                else:
                    conflict_info = {"source": src, "target": tgt, "existing_target": existing_tgt}
                    preview_results["conflict"].append(conflict_info)
            else:
                preview_results["new"].append(entry)
                
        return preview_results

    def apply_import(self, game_id: str, parsed_data: List[Dict[str, str]], strategy: str = 'merge') -> None:
        """
        All-or-Nothing Commit.
        strategy: 'merge' (replace conflicts, keep others), 'replace' (wipe old glossary completely)
        """
        profile = self.profile_repo.get_by_id(game_id)
        if not profile:
            raise ValueError("Game not found")

        try:
            # Validate toàn bộ trước khi update
            new_entries = {}
            for item in parsed_data:
                src = item.get('source')
                tgt = item.get('target')
                if not src or not tgt:
                    raise ValueError("Invalid entry found during commit")
                new_entries[src] = tgt
            
            if strategy == 'replace':
                final_glossary = new_entries
            else:
                final_glossary = (profile.glossary or {}).copy()
                final_glossary.update(new_entries)
                
            # Atomic commit to profile repo
            profile.glossary = final_glossary
            self.profile_repo.save(profile)
        except Exception as e:
            # Nếu có lỗi ở 1 dòng bất kỳ, rollback (không save)
            raise ValueError(f"Import failed during commit: {e}")
