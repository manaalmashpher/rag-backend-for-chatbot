"""
Build script for Railway deployment
Builds the frontend and serves it from FastAPI
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(command, cwd=None):
    """Run a command and return success status"""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=cwd, 
            check=True, 
            capture_output=True, 
            text=True
        )
        print(f"✅ {command}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {command}")
        print(f"Error: {e.stderr}")
        return False

def main():
    """Build frontend and prepare for deployment"""
    print("🚀 Starting build process for Railway deployment...")
    
    # Check if we're in the right directory
    if not os.path.exists("package.json"):
        print("❌ package.json not found. Make sure you're in the project root.")
        sys.exit(1)
    
    # Install frontend dependencies
    print("📦 Installing frontend dependencies...")
    if not run_command("npm install"):
        print("❌ Failed to install frontend dependencies")
        sys.exit(1)
    
    # Build frontend
    print("🔨 Building frontend...")
    if not run_command("npm run build"):
        print("❌ Failed to build frontend")
        sys.exit(1)
    
    # Check if dist directory exists
    if not os.path.exists("dist"):
        print("❌ dist directory not found after build")
        sys.exit(1)
    
    # Run database migration if DATABASE_URL is set (production)
    if os.getenv('DATABASE_URL') and os.getenv('DATABASE_URL').startswith('postgres'):
        print("🗄️ Running database migration...")
        if not run_command("python migrate_database.py"):
            print("⚠️ Database migration failed, but continuing...")
    
    print("✅ Frontend build completed successfully!")
    print("🎯 Ready for Railway deployment!")

if __name__ == "__main__":
    main()
