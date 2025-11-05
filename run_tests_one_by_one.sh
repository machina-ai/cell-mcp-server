#!/bin/bash
# This script runs pytest for each test file individually to avoid API rate limiting.

# Find all python files in the tests directory that start with test_
TEST_FILES=$(find tests -name "test_*.py")

# Loop through each test file and run pytest
for file in $TEST_FILES
do
  echo "======================================================================="
  echo "RUNNING TEST: $file"
  echo "======================================================================="
  /Users/rodolfo/Development/AI/cell_project/zen-mcp-server/.zen_venv/bin/python -m pytest "$file"
  # Optional: add a small delay if rate limiting is still an issue
  # sleep 1
done

echo "All tests have been run."
