#!/usr/bin/env python3
"""
Script to clear all projects from Supabase database.
This will delete all projects and related data.
"""

import os
import sys
from dotenv import load_dotenv

# Add src to path to import database module
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from database import get_supabase_client

def clear_all_projects():
    """Clear all projects from the database and storage."""
    try:
        # Load environment variables
        load_dotenv()
        
        # Get Supabase client
        supabase_wrapper = get_supabase_client()
        # Get the actual Supabase client from the wrapper
        supabase = supabase_wrapper.client
        
        print("🗑️  Clearing all projects from Supabase...")
        
        # First, clear all files from storage buckets
        print("🗂️  Clearing storage files...")
        
        # List and delete all files from presentations bucket
        try:
            presentations_files = supabase.storage.from_('presentations').list()
            if presentations_files:
                file_paths = [file['name'] for file in presentations_files if file['name']]
                if file_paths:
                    supabase.storage.from_('presentations').remove(file_paths)
                    print(f"✅ Deleted {len(file_paths)} presentation files")
                else:
                    print("✅ No presentation files to delete")
            else:
                print("✅ Presentations bucket is empty")
        except Exception as e:
            print(f"⚠️  Warning: Could not clear presentations bucket: {str(e)}")
        
        # List and delete all files from html-debug bucket
        try:
            html_files = supabase.storage.from_('html-debug').list()
            if html_files:
                file_paths = [file['name'] for file in html_files if file['name']]
                if file_paths:
                    supabase.storage.from_('html-debug').remove(file_paths)
                    print(f"✅ Deleted {len(file_paths)} HTML debug files")
                else:
                    print("✅ No HTML debug files to delete")
            else:
                print("✅ HTML debug bucket is empty")
        except Exception as e:
            print(f"⚠️  Warning: Could not clear html-debug bucket: {str(e)}")
        
        # List and delete all files from images bucket (if it exists)
        try:
            image_files = supabase.storage.from_('images').list()
            if image_files:
                file_paths = [file['name'] for file in image_files if file['name']]
                if file_paths:
                    supabase.storage.from_('images').remove(file_paths)
                    print(f"✅ Deleted {len(file_paths)} image files")
                else:
                    print("✅ No image files to delete")
            else:
                print("✅ Images bucket is empty")
        except Exception as e:
            print(f"⚠️  Warning: Could not clear images bucket: {str(e)}")
        
        # Now delete database records
        print("🗄️  Clearing database records...")
        
        # Delete all projects (this will cascade to related tables due to foreign key constraints)
        result = supabase.table('projects').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        
        print(f"✅ Successfully deleted {len(result.data)} projects")
        
        # Also clear any orphaned slides if they exist
        slides_result = supabase.table('slides').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        print(f"✅ Cleared {len(slides_result.data)} orphaned slides")
        
        # Clear workflow states
        workflow_result = supabase.table('workflow_states').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        print(f"✅ Cleared {len(workflow_result.data)} workflow states")
        
        print("🎉 Database and storage cleared successfully!")
        
    except Exception as e:
        print(f"❌ Error clearing projects: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    print("⚠️  WARNING: This will delete ALL projects from the database!")
    confirm = input("Are you sure you want to continue? (type 'yes' to confirm): ")
    
    if confirm.lower() == 'yes':
        success = clear_all_projects()
        sys.exit(0 if success else 1)
    else:
        print("❌ Operation cancelled")
        sys.exit(1)