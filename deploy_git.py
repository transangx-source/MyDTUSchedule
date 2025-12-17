import os
from git import Repo, GitCommandError # Import GitCommandError để xử lý lỗi tốt hơn

# ================= CẤU HÌNH GIT =================
REPO_PATH = '.' 
JSON_FILE_NAME = "lich_hoc_hom_nay_va_mai.json"
COMMIT_MESSAGE = "Auto update schedule data"
# ================================================

def push_to_github():
    """Tự động commit và push file JSON lên GitHub Pages (sử dụng --force để tránh lỗi xung đột)."""
    
    full_json_path = os.path.join(REPO_PATH, JSON_FILE_NAME)
    if not os.path.exists(full_json_path):
        print(f"❌ Lỗi Deploy: Không tìm thấy file JSON tại {full_json_path}")
        return False
        
    try:
        repo = Repo(REPO_PATH)
        
        # 1. Thêm và Commit (Không thay đổi)
        if repo.index.diff(None) or (JSON_FILE_NAME in repo.untracked_files):
            
            # --- RẤT QUAN TRỌNG: CÁC BƯỚC XỬ LÝ TRƯỚC KHI PUSH ---
            # Nếu có xung đột chưa được giải quyết, ta cần giải quyết nó trước.
            # Trong trường hợp auto-update, ta có thể reset cứng về phiên bản local
            # hoặc đơn giản là dùng --force.
            
            repo.index.add([JSON_FILE_NAME])
            repo.index.commit(COMMIT_MESSAGE)
            print("[GIT] Đã Commit thành công.")
            
            # 2. Push lên GitHub sử dụng --force để tránh lỗi xung đột
            origin = repo.remote(name='origin')
            
            # -----------------------------------------------------------------------------------
            # SỬA LỖI: SỬ DỤNG 'push(force=True)' để ép buộc ghi đè và tránh lỗi Merge Conflict
            # -----------------------------------------------------------------------------------
            origin.push(force=True)
            
            print("✅ [GIT] Đã Push thành công lên GitHub Pages (Bằng cách ghi đè)!")
            
            return True
        else:
            print("[GIT] Dữ liệu không thay đổi. Không cần Push.")
            return True
            
    except GitCommandError as e:
        print(f"❌ [LỖI FATAL] Lỗi Git Command: {e}")
        return False
    except Exception as e:
        print(f"❌ [LỖI FATAL] Lỗi khi thao tác với Git: {e}")
        print("💡 KIỂM TRA: Đã chạy lệnh 'git remote set-url...' với PAT chưa?")
        return False

if __name__ == '__main__':
    push_to_github()