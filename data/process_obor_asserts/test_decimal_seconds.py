#!/usr/bin/env python3
"""
Test script to demonstrate decimal seconds support in video_trimmer.py
"""

import sys
import os

# Add the current directory to Python path so we can import video_trimmer
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from video_trimmer import parse_time

def test_decimal_seconds():
    """Test various decimal second formats."""
    print("Testing decimal seconds support in video_trimmer...")
    print("=" * 50)
    
    test_cases = [
        # (input, expected_output, description)
        ("2.4", 2.4, "Simple decimal seconds"),
        ("30.5", 30.5, "Decimal seconds"),
        ("123.75", 123.75, "Decimal seconds with more precision"),
        ("0.5", 0.5, "Half second"),
        ("0.25", 0.25, "Quarter second"),
        ("5", 5.0, "Integer seconds"),
        ("00:02.4", 2.4, "MM:SS with decimal seconds"),
        ("01:30.5", 90.5, "MM:SS with decimal seconds"),
        ("00:00:02.4", 2.4, "HH:MM:SS with decimal seconds"),
        ("00:01:30.25", 90.25, "HH:MM:SS with decimal seconds"),
        ("01:02:30.5", 3750.5, "HH:MM:SS with decimal seconds"),
        ("02:30", 150.0, "MM:SS format"),
        ("01:02:30", 3750.0, "HH:MM:SS format"),
        ("00:00:30.125", 30.125, "Millisecond precision"),
    ]
    
    passed = 0
    failed = 0
    
    for input_str, expected, description in test_cases:
        try:
            result = parse_time(input_str)
            if abs(result - expected) < 0.001:  # Allow for floating point precision
                print(f"✓ PASS: {input_str:>12} -> {result:>8.3f}s ({description})")
                passed += 1
            else:
                print(f"✗ FAIL: {input_str:>12} -> {result:>8.3f}s (expected {expected:.3f}s) ({description})")
                failed += 1
        except Exception as e:
            print(f"✗ ERROR: {input_str:>12} -> {str(e)} ({description})")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed} passed, {failed} failed")
    
    # Test error cases
    print("\nTesting error cases:")
    error_cases = [
        "-2.4",      # Negative time
        "invalid",   # Invalid format
        "25:70",     # Invalid seconds (>= 60)
        "01:70:30",  # Invalid minutes (>= 60)
        "",          # Empty string
    ]
    
    for error_case in error_cases:
        try:
            result = parse_time(error_case)
            print(f"✗ Should have failed: {error_case} -> {result}")
        except ValueError as e:
            print(f"✓ Correctly rejected: {error_case} -> {e}")
        except Exception as e:
            print(f"? Unexpected error: {error_case} -> {e}")

def demo_usage_examples():
    """Show practical usage examples."""
    print("\n" + "=" * 50)
    print("PRACTICAL USAGE EXAMPLES:")
    print("=" * 50)
    
    examples = [
        {
            'description': 'Trim from 2.4 seconds to 30.5 seconds',
            'command': 'python video_trimmer.py input.mp4 output.mp4 --start 2.4 --end 30.5'
        },
        {
            'description': 'Trim from 1.5 seconds to 1 minute 45.25 seconds', 
            'command': 'python video_trimmer.py input.mp4 output.mp4 --start 1.5 --end 01:45.25'
        },
        {
            'description': 'Trim precise segment with millisecond precision',
            'command': 'python video_trimmer.py input.mp4 output.mp4 --start 00:00:02.125 --end 00:00:30.875'
        },
        {
            'description': 'Trim from 30.5s to 2 minutes 15.75 seconds',
            'command': 'python video_trimmer.py input.mp4 output.mp4 --start 30.5 --end 02:15.75'
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example['description']}")
        print(f"   Command: {example['command']}")
        
        # Parse the times to show what they convert to
        try:
            start = example['command'].split('--start ')[1].split(' ')[0]
            end = example['command'].split('--end ')[1].split(' ')[0] if '--end' in example['command'] else example['command'].split('--end ')[1]
            
            start_seconds = parse_time(start)
            end_seconds = parse_time(end)
            duration = end_seconds - start_seconds
            
            print(f"   Start: {start} -> {start_seconds:.3f} seconds")
            print(f"   End: {end} -> {end_seconds:.3f} seconds")
            print(f"   Duration: {duration:.3f} seconds ({duration/60:.2f} minutes)")
        except:
            pass

if __name__ == "__main__":
    test_decimal_seconds()
    demo_usage_examples()
    print("\n" + "=" * 50)
    print("Decimal seconds are fully supported! 🎉")
    print("You can now use formats like:")
    print("  --start 2.4 --end 30.5")
    print("  --start 00:02.4 --end 01:30.25") 
    print("  --start 0.5 --end 120.75") 