#!/usr/bin/env python3
"""
Cleanup script for AI Grader test files.
Removes temporary files from testing while optionally keeping grades.
"""

import os
import shutil
from utils.config import FINAL_PDFS_DIR, MERGED_PDFS_DIR, SUBMISSIONS_DIR, DEBUG_DIR, GRADES_DIR

def get_directory_size(path):
    """Calculate total size of directory in MB"""
    total = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.exists(fp):
                    total += os.path.getsize(fp)
    except Exception as e:
        print(f"Error calculating size: {e}")
    return total / (1024 * 1024)  # Convert to MB

def count_files(path):
    """Count total files in directory"""
    count = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            count += len(filenames)
    except:
        pass
    return count

def show_status():
    """Show current storage status"""
    print("\n" + "="*60)
    print("📊 CURRENT STORAGE STATUS")
    print("="*60)
    
    dirs = [
        ("Submissions", SUBMISSIONS_DIR),
        ("Final PDFs", FINAL_PDFS_DIR),
        ("Merged PDFs", MERGED_PDFS_DIR),
        ("Debug Outputs", DEBUG_DIR),
        ("Grades (CSV)", GRADES_DIR),
    ]
    
    total_size = 0
    total_files = 0
    
    for name, path in dirs:
        if os.path.exists(path):
            size = get_directory_size(path)
            files = count_files(path)
            total_size += size
            total_files += files
            print(f"{name:20} {files:6} files  {size:8.2f} MB")
        else:
            print(f"{name:20} {'N/A':>6}        {'0.00':>8} MB")
    
    print("-" * 60)
    print(f"{'TOTAL':20} {total_files:6} files  {total_size:8.2f} MB")
    print("="*60 + "\n")

def cleanup_temp_files(keep_grades=True):
    """Clean temporary files, optionally keeping grades"""
    
    dirs_to_clean = [
        ("Submissions", SUBMISSIONS_DIR),
        ("Final PDFs", FINAL_PDFS_DIR),
        ("Merged PDFs", MERGED_PDFS_DIR),
        ("Debug Outputs", DEBUG_DIR),
    ]
    
    if not keep_grades:
        dirs_to_clean.append(("Grades", GRADES_DIR))
    
    print("\n🧹 CLEANING TEMPORARY FILES...")
    print("-" * 60)
    
    cleaned_count = 0
    for name, path in dirs_to_clean:
        if os.path.exists(path):
            try:
                # Count files before deletion
                file_count = count_files(path)
                size = get_directory_size(path)
                
                # Remove and recreate directory
                shutil.rmtree(path)
                os.makedirs(path, exist_ok=True)
                
                print(f"✓ Cleaned {name:20} {file_count:6} files  {size:8.2f} MB")
                cleaned_count += 1
            except Exception as e:
                print(f"✗ Error cleaning {name}: {e}")
        else:
            print(f"- {name:20} (directory doesn't exist)")
    
    print("-" * 60)
    print(f"✓ Cleaned {cleaned_count} directories\n")

def main():
    print("\n" + "="*60)
    print("🧹 AI GRADER - CLEANUP UTILITY")
    print("="*60)
    
    # Show current status
    show_status()
    
    # Ask user what they want to do
    print("OPTIONS:")
    print("1. Clean all temp files (keep grades CSV)")
    print("2. Clean all temp files (including grades)")
    print("3. Just show status (no cleanup)")
    print("4. Exit")
    print()
    
    choice = input("Enter your choice (1-4): ").strip()
    
    if choice == "1":
        confirm = input("\n⚠️  Clean all temp files but KEEP grades? [y/N]: ").lower()
        if confirm == "y":
            cleanup_temp_files(keep_grades=True)
            show_status()
        else:
            print("Cancelled.")
    
    elif choice == "2":
        confirm = input("\n⚠️  Clean ALL files including grades? [y/N]: ").lower()
        if confirm == "y":
            cleanup_temp_files(keep_grades=False)
            show_status()
        else:
            print("Cancelled.")
    
    elif choice == "3":
        print("No cleanup performed.")
    
    elif choice == "4":
        print("Exiting.")
    
    else:
        print("Invalid choice.")

if __name__ == "__main__":
    main()

