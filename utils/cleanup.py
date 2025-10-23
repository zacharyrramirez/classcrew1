import os
import shutil
import time

def cleanup_directory(dir_path, confirm=False):
    """
    Deletes all contents in the given directory (if it exists), 
    then recreates the directory as empty.
    Returns True if any files/folders were deleted, False otherwise.
    Optionally asks for confirmation if confirm=True.
    """
    if confirm:
        ans = input(f"Are you SURE you want to delete everything in '{dir_path}'? [y/N]: ").lower()
        if ans != "y":
            print("Aborted cleanup.")
            return False

    if os.path.exists(dir_path):
        try:
            shutil.rmtree(dir_path)
            os.makedirs(dir_path, exist_ok=True)
            return True
        except Exception as e:
            print(f"❌ Error cleaning directory {dir_path}: {e}")
            return False
    else:
        os.makedirs(dir_path, exist_ok=True)
        return False

def cleanup_multiple(dirs, confirm=False):
    """
    Accepts a list of directory paths. Cleans each using cleanup_directory.
    Returns a dict mapping directory -> True/False (True = cleaned).
    """
    results = {}
    for d in dirs:
        results[d] = cleanup_directory(d, confirm=confirm)
    return results

def cleanup_old_files(dir_path, days=7):
    """
    Deletes files in dir_path older than 'days' days.
    Returns a list of deleted file names.
    """
    now = time.time()
    deleted = []
    if not os.path.isdir(dir_path):
        return deleted

    for fname in os.listdir(dir_path):
        fpath = os.path.join(dir_path, fname)
        if os.path.isfile(fpath):
            try:
                if now - os.path.getmtime(fpath) > days * 86400:
                    os.remove(fpath)
                    deleted.append(fname)
            except Exception as e:
                print(f"❌ Could not delete {fpath}: {e}")
    return deleted

def cleanup_assignment_files(assignment_id):
    """
    Cleans all files for a given assignment from FINAL_PDFS_DIR, MERGED_PDFS_DIR, and SUBMISSIONS_DIR.
    Leaves grades and debug_outputs untouched.
    """
    from utils.config import FINAL_PDFS_DIR, MERGED_PDFS_DIR, SUBMISSIONS_DIR
    import shutil
    for base_dir in [FINAL_PDFS_DIR, MERGED_PDFS_DIR, SUBMISSIONS_DIR]:
        target = os.path.join(base_dir, str(assignment_id))
        if os.path.exists(target):
            try:
                shutil.rmtree(target)
                print(f"🧹 Cleaned {target}")
            except Exception as e:
                print(f"❌ Error cleaning {target}: {e}")
