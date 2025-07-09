#!/usr/bin/env python3
"""
Test runner script for turtle-app.
Provides convenient ways to run tests with different options.
"""
import sys
import subprocess
import argparse


def run_tests(args):
    """Run pytest with the given arguments."""
    cmd = ["python", "-m", "pytest"] + args
    print(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=".")


def main():
    parser = argparse.ArgumentParser(description="Run turtle-app tests")
    parser.add_argument(
        "--unit", 
        action="store_true", 
        help="Run only unit tests"
    )
    parser.add_argument(
        "--integration", 
        action="store_true", 
        help="Run only integration tests"
    )
    parser.add_argument(
        "--slow", 
        action="store_true", 
        help="Include slow tests"
    )
    parser.add_argument(
        "--coverage", 
        action="store_true", 
        help="Run with coverage report"
    )
    parser.add_argument(
        "--verbose", "-v", 
        action="store_true", 
        help="Verbose output"
    )
    parser.add_argument(
        "test_paths", 
        nargs="*", 
        help="Specific test files or directories to run"
    )
    
    args = parser.parse_args()
    
    pytest_args = []
    
    # Add markers based on arguments
    if args.unit:
        pytest_args.extend(["-m", "unit"])
    elif args.integration:
        pytest_args.extend(["-m", "integration"])
    
    if not args.slow:
        pytest_args.extend(["-m", "not slow"])
    
    # Add coverage if requested
    if args.coverage:
        pytest_args.extend(["--cov=turtleapp", "--cov-report=html", "--cov-report=term"])
    
    # Add verbose flag
    if args.verbose:
        pytest_args.append("-v")
    
    # Add specific test paths if provided
    if args.test_paths:
        pytest_args.extend(args.test_paths)
    
    # Run the tests
    result = run_tests(pytest_args)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main() 