#!/usr/bin/env python3
"""
Setup script for JSON QA Web Application
Creates necessary directories and validates environment
"""

import os
import sys
import subprocess
from pathlib import Path

def create_directories():
    """Create required directories if they don't exist."""
    directories = [
        'json_docs',
        'corrected', 
        'pdf_docs',
        'schemas',
        'locks',
        'audit_logs',
        'utils',
        '.streamlit'
    ]
    
    print("Creating directory structure...")
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✓ {directory}/")
    
    # Create __init__.py for utils package
    init_file = Path('utils/__init__.py')
    if not init_file.exists():
        init_file.touch()
        print("✓ utils/__init__.py")

def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    
    print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
    return True

def install_dependencies():
    """Install required Python packages."""
    print("\nInstalling dependencies...")
    try:
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'
        ])
        print("✓ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def validate_installation():
    """Validate that key packages are importable."""
    print("\nValidating installation...")
    packages = [
        'streamlit',
        'pydantic', 
        'deepdiff',
        'streamlit_pdf_viewer',
        'yaml'
    ]
    
    for package in packages:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"❌ {package} - not found")
            return False
    
    return True

def create_sample_files():
    """Create sample configuration files if they don't exist."""
    print("\nCreating sample files...")
    
    # Sample JSON file
    json_docs = Path('json_docs/sample_invoice.json')
    if not json_docs.exists():
        sample_data = {
            "supplier_name": "ACME Corporation",
            "po_number": "PO-123456",
            "invoice_number": "INV-2024-001",
            "amount": 1250.00,
            "invoice_date": "2024-01-15",
            "status": "pending",
            "line_items": [
                {
                    "description": "Office Supplies",
                    "quantity": 10,
                    "unit_price": 25.00
                },
                {
                    "description": "Software License",
                    "quantity": 1,
                    "unit_price": 1000.00
                }
            ]
        }
        
        import json
        with open(json_docs, 'w') as f:
            json.dump(sample_data, f, indent=2)
        print("✓ json_docs/sample_invoice.json")
    
    # Sample schema (if default doesn't exist)
    default_schema = Path('schemas/default_schema.yaml')
    if not default_schema.exists():
        schema_content = """title: "Default Schema"
description: "Generic schema for unknown document types"
fields:
  document_type:
    type: "string"
    label: "Document Type"
    required: true
    default: "unknown"
  
  content:
    type: "object"
    label: "Content"
    required: false
    description: "Document content as key-value pairs"
"""
        with open(default_schema, 'w') as f:
            f.write(schema_content)
        print("✓ schemas/default_schema.yaml")

def main():
    """Main setup function."""
    print("JSON QA Web Application Setup")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Install dependencies
    if not install_dependencies():
        print("\n❌ Setup failed during dependency installation")
        sys.exit(1)
    
    # Validate installation
    if not validate_installation():
        print("\n❌ Setup failed during validation")
        sys.exit(1)
    
    # Create sample files
    create_sample_files()
    
    print("\n" + "=" * 40)
    print("✅ Setup completed successfully!")
    print("\nTo start the application:")
    print("  python -m streamlit run streamlit_app.py")
    print("\nThe application will be available at:")
    print("  http://localhost:8501")
    print("\nFor more information, see README.md")

if __name__ == "__main__":
    main()