"""
Test script for Basic Response Handler
"""
import sys
import os
sys.path.append(os.getcwd())

from src.services.chat.basic_response_handler import BasicResponseHandler

def test_basic_responses():
    handler = BasicResponseHandler()
    
    test_cases = [
        # English
        ("hello", True),
        ("hi", True),
        ("hello torres", True),
        ("what is your name", True),
        ("who are you", True),
        ("random text", False),
        
        # Malayalam
        ("sugam aano", True),
        ("sugamano", True),
        ("endha per", True),
        ("entha peru", True),
        ("food kayicho", True),
        ("food kazhicho", True),
        ("random malayalam", False),
    ]
    
    print("🧪 Testing Basic Responses...")
    print("="*40)
    
    passed = 0
    failed = 0
    
    for text, should_match in test_cases:
        response = handler.get_response(text)
        has_match = response is not None
        
        status = "✅ PASS" if has_match == should_match else "❌ FAIL"
        if has_match != should_match:
            failed += 1
        else:
            passed += 1
            
        print(f"{status} | Input: '{text}'")
        if response:
            print(f"   -> Response: {response}")
            
    print("="*40)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed")
        sys.exit(1)

if __name__ == "__main__":
    test_basic_responses()
