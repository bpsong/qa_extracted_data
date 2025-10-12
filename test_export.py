#!/usr/bin/env python3
"""
Test script to verify audit export functionality.
"""

import sys
import os
from datetime import datetime
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.audit_view import AuditView
from utils.file_utils import read_audit_logs

def test_export():
    """Test the export functionality."""
    print("Testing audit export functionality...")
    
    # Read audit logs
    entries = read_audit_logs()
    print(f"Found {len(entries)} audit entries")
    
    if not entries:
        print("No audit entries found. Cannot test export.")
        return
    
    # Test CSV export
    print("\nTesting CSV export...")
    csv_data = AuditView.export_audit_data(entries, 'csv')
    if csv_data:
        print(f"✅ CSV export successful! Size: {len(csv_data)} characters")
        
        # Save to file
        csv_filename = f"audit_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(csv_filename, 'w', encoding='utf-8') as f:
            f.write(csv_data)
        print(f"💾 CSV saved to: {csv_filename}")
    else:
        print("❌ CSV export failed")
    
    # Test JSON export
    print("\nTesting JSON export...")
    json_data = AuditView.export_audit_data(entries, 'json')
    if json_data:
        print(f"✅ JSON export successful! Size: {len(json_data)} characters")
        
        # Save to file
        json_filename = f"audit_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            f.write(json_data)
        print(f"💾 JSON saved to: {json_filename}")
    else:
        print("❌ JSON export failed")

if __name__ == "__main__":
    test_export()