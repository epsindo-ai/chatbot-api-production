#!/usr/bin/env python3

"""
Test script to verify the enhanced title cleaning functionality.
"""

import sys
import os
sys.path.append('/app')

from app.utils.title_utils import clean_title

def test_title_cleaning():
    """Test various problematic titles that should be cleaned."""
    
    test_cases = [
        # Original problematic case
        ('Persiapan Beli DGX H100" → "Kebutuhan UPS DGX H100', 'Persiapan Beli DGX H100'),
        
        # Markdown symbols
        ('**GPU Requirements**', 'GPU Requirements'),
        ('__Important Question__', 'Important Question'),
        ('`code setup`', 'code setup'),
        ('~strikethrough text~', 'strikethrough text'),
        
        # Arrows and special symbols
        ('Question → Answer', 'Question Answer'),
        ('Input ← Output', 'Input Output'),
        ('Step 1 ↑ Step 2', 'Step 1 Step 2'),
        ('Process ↓ Result', 'Process Result'),
        
        # Brackets and parentheses
        ('[Important] Setup Guide', 'Important Setup Guide'),
        ('(Optional) Configuration', 'Optional Configuration'),
        ('{Advanced} Settings', 'Advanced Settings'),
        ('<Required> Installation', 'Required Installation'),
        
        # Multiple punctuation
        ('Question???', 'Question'),
        ('Setup!!!', 'Setup'),
        ('Config...', 'Config'),
        ('Help,,,', 'Help'),
        
        # Quotes and formatting
        ('"Python Programming"', 'Python Programming'),
        ("'Machine Learning'", 'Machine Learning'),
        ('"DGX Setup" → "GPU Config"', 'DGX Setup GPU Config'),
        
        # Length testing (should limit to 5 words)
        ('This is a very long title with many words', 'This is a very long'),
        
        # Edge cases
        ('', 'New Conversation'),
        ('   ', 'New Conversation'),
        ('***', 'New Conversation'),
        ('→→→', 'New Conversation'),
    ]
    
    print("Testing title cleaning functionality...\n")
    
    all_passed = True
    for input_title, expected in test_cases:
        result = clean_title(input_title)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        
        if result != expected:
            all_passed = False
        
        print(f"{status}")
        print(f"  Input:    '{input_title}'")
        print(f"  Expected: '{expected}'")
        print(f"  Got:      '{result}'")
        print()
    
    print(f"Overall result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    return all_passed

if __name__ == "__main__":
    test_title_cleaning()
