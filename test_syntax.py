#!/usr/bin/env python3
# -*- coding: utf-8 -*-

print("Testing Python syntax...")

def test_function():
    try:
        print("Function works")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    test_function()
    print("Syntax test completed successfully!")
