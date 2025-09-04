#!/usr/bin/env python3
"""
Test runner for scraper manager tests.

This script provides an easy way to run scraper manager tests
without the strict coverage requirements that might interfere
during development.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_scraper_manager_tests(verbose=True, coverage=False, specific_test=None):
    """Run scraper manager tests with appropriate configuration."""
    
    # Ensure we're in the right directory
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    # Activate virtual environment if needed
    venv_python = project_root / "venv" / "bin" / "python"
    if venv_python.exists():
        python_cmd = str(venv_python)
    else:
        python_cmd = sys.executable
    
    # Build pytest command
    cmd = [python_cmd, "-m", "pytest"]
    
    # Add test files
    if specific_test:
        cmd.append(specific_test)
    else:
        cmd.extend([
            "tests/test_scraper_manager.py",
            "tests/test_scraper_manager_edge_cases.py"
        ])
    
    # Add options
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=src.scripts.scraper_manager", "--cov-report=html", "--cov-report=term"])
    else:
        # Disable coverage for quick testing
        cmd.append("--no-cov")
    
    # Add other useful options
    cmd.extend([
        "--tb=short",           # Shorter traceback format
        "-x",                   # Stop on first failure
        "--disable-warnings"    # Hide most warnings during development
    ])
    
    print(f"Running command: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode == 0
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        return False
    except Exception as e:
        print(f"Error running tests: {e}")
        return False


def run_quick_tests():
    """Run a subset of quick tests for rapid development feedback."""
    quick_tests = [
        "tests/test_scraper_manager.py::TestScraperManager::test_scraper_manager_initialization",
        "tests/test_scraper_manager.py::TestScraperManager::test_start_scraping_session_success",
        "tests/test_scraper_manager.py::TestScraperManager::test_generate_urls_for_season_regular",
        "tests/test_scraper_manager.py::TestScraperManagerCLI::test_main_scrape_season"
    ]
    
    print("Running quick tests...")
    for test in quick_tests:
        success = run_scraper_manager_tests(verbose=False, coverage=False, specific_test=test)
        if not success:
            print(f"❌ Failed: {test}")
            return False
        else:
            print(f"✅ Passed: {test.split('::')[-1]}")
    
    print("\n🎉 All quick tests passed!")
    return True


def run_edge_case_tests():
    """Run edge case and error handling tests."""
    return run_scraper_manager_tests(
        verbose=True,
        coverage=False, 
        specific_test="tests/test_scraper_manager_edge_cases.py"
    )


def run_full_test_suite():
    """Run the complete test suite with coverage."""
    return run_scraper_manager_tests(verbose=True, coverage=True)


def main():
    """Main test runner interface."""
    if len(sys.argv) < 2:
        print("Usage: python test_runner.py [quick|edge|full|custom]")
        print("  quick: Run essential tests for rapid feedback")
        print("  edge: Run edge case and error handling tests")
        print("  full: Run complete test suite with coverage")
        print("  custom: Run specific test (provide test path as additional argument)")
        return
    
    test_type = sys.argv[1].lower()
    
    if test_type == "quick":
        success = run_quick_tests()
    elif test_type == "edge":
        success = run_edge_case_tests()
    elif test_type == "full":
        success = run_full_test_suite()
    elif test_type == "custom":
        if len(sys.argv) < 3:
            print("Please provide test path for custom run")
            return
        success = run_scraper_manager_tests(verbose=True, coverage=False, specific_test=sys.argv[2])
    else:
        print(f"Unknown test type: {test_type}")
        return
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()