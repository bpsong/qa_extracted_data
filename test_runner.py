"""
Test runner for JSON QA webapp.
Runs all tests and generates coverage reports.
"""

import pytest
import sys
import os
from pathlib import Path
import subprocess
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)


class QATestRunner:
    """Test runner for the JSON QA webapp."""
    
    def __init__(self):
        self.test_files = [
            "test_file_utils.py",
            "test_schema_loader.py", 
            "test_model_builder.py",
            "test_diff_utils.py",
            "test_submission_handler.py",
            "test_error_handler.py",
            "test_ui_feedback.py",
            "test_integration.py"
        ]
        
        self.coverage_threshold = 80  # Minimum coverage percentage
    
    def run_unit_tests(self):
        """Run all unit tests."""
        logger.info("Running unit tests...")
        
        unit_test_files = [f for f in self.test_files if not f.startswith("test_integration")]
        
        # Run pytest with coverage
        cmd = [
            "python", "-m", "pytest",
            "--verbose",
            "--tb=short",
            "--cov=utils",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-fail-under={}".format(self.coverage_threshold)
        ] + unit_test_files
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✅ Unit tests passed!")
                print(result.stdout)
                return True
            else:
                logger.error("❌ Unit tests failed!")
                print(result.stdout)
                print(result.stderr)
                return False
                
        except Exception as e:
            logger.error(f"Error running unit tests: {e}")
            return False
    
    def run_integration_tests(self):
        """Run integration tests."""
        logger.info("Running integration tests...")
        
        cmd = [
            "python", "-m", "pytest",
            "--verbose",
            "--tb=short",
            "test_integration.py"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✅ Integration tests passed!")
                print(result.stdout)
                return True
            else:
                logger.error("❌ Integration tests failed!")
                print(result.stdout)
                print(result.stderr)
                return False
                
        except Exception as e:
            logger.error(f"Error running integration tests: {e}")
            return False
    
    def run_all_tests(self):
        """Run all tests."""
        logger.info("Running complete test suite...")
        
        cmd = [
            "python", "-m", "pytest",
            "--verbose",
            "--tb=short",
            "--cov=utils",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-fail-under={}".format(self.coverage_threshold)
        ] + self.test_files
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✅ All tests passed!")
                print(result.stdout)
                return True
            else:
                logger.error("❌ Some tests failed!")
                print(result.stdout)
                print(result.stderr)
                return False
                
        except Exception as e:
            logger.error(f"Error running tests: {e}")
            return False
    
    def run_specific_test(self, test_file: str):
        """Run a specific test file."""
        if test_file not in self.test_files:
            logger.error(f"Test file {test_file} not found in test suite")
            return False
        
        logger.info(f"Running {test_file}...")
        
        cmd = [
            "python", "-m", "pytest",
            "--verbose",
            "--tb=short",
            test_file
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"✅ {test_file} passed!")
                print(result.stdout)
                return True
            else:
                logger.error(f"❌ {test_file} failed!")
                print(result.stdout)
                print(result.stderr)
                return False
                
        except Exception as e:
            logger.error(f"Error running {test_file}: {e}")
            return False
    
    def check_test_files_exist(self):
        """Check that all test files exist."""
        missing_files = []
        
        for test_file in self.test_files:
            if not Path(test_file).exists():
                missing_files.append(test_file)
        
        if missing_files:
            logger.error(f"Missing test files: {missing_files}")
            return False
        
        logger.info("All test files found")
        return True
    
    def generate_test_report(self):
        """Generate a comprehensive test report."""
        logger.info("Generating test report...")
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "test_files": self.test_files,
            "results": {}
        }
        
        # Run each test file individually to get detailed results
        for test_file in self.test_files:
            logger.info(f"Testing {test_file}...")
            
            cmd = [
                "python", "-m", "pytest",
                "--verbose",
                "--tb=no",
                "--quiet",
                test_file
            ]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                report["results"][test_file] = {
                    "passed": result.returncode == 0,
                    "output": result.stdout,
                    "errors": result.stderr if result.stderr else None
                }
                
            except Exception as e:
                report["results"][test_file] = {
                    "passed": False,
                    "output": "",
                    "errors": str(e)
                }
        
        # Save report
        import json
        with open("test_report.json", 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        total_tests = len(self.test_files)
        passed_tests = sum(1 for r in report["results"].values() if r["passed"])
        
        logger.info(f"Test Report Summary:")
        logger.info(f"  Total test files: {total_tests}")
        logger.info(f"  Passed: {passed_tests}")
        logger.info(f"  Failed: {total_tests - passed_tests}")
        logger.info(f"  Success rate: {(passed_tests / total_tests) * 100:.1f}%")
        
        return report
    
    def install_test_dependencies(self):
        """Install required test dependencies."""
        logger.info("Installing test dependencies...")
        
        dependencies = [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-mock>=3.10.0",
            "coverage>=7.0.0"
        ]
        
        for dep in dependencies:
            try:
                subprocess.run([
                    "python", "-m", "pip", "install", dep
                ], check=True, capture_output=True)
                logger.info(f"✅ Installed {dep}")
            except subprocess.CalledProcessError as e:
                logger.error(f"❌ Failed to install {dep}: {e}")
                return False
        
        return True


def main():
    """Main test runner function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="JSON QA Webapp Test Runner")
    parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration", action="store_true", help="Run only integration tests")
    parser.add_argument("--file", type=str, help="Run specific test file")
    parser.add_argument("--report", action="store_true", help="Generate detailed test report")
    parser.add_argument("--install-deps", action="store_true", help="Install test dependencies")
    parser.add_argument("--check", action="store_true", help="Check test files exist")
    
    args = parser.parse_args()
    
    runner = QATestRunner()
    
    # Install dependencies if requested
    if args.install_deps:
        if not runner.install_test_dependencies():
            sys.exit(1)
        return
    
    # Check test files exist
    if args.check:
        if not runner.check_test_files_exist():
            sys.exit(1)
        return
    
    # Generate report
    if args.report:
        runner.generate_test_report()
        return
    
    # Run specific test file
    if args.file:
        success = runner.run_specific_test(args.file)
        sys.exit(0 if success else 1)
    
    # Run unit tests only
    if args.unit:
        success = runner.run_unit_tests()
        sys.exit(0 if success else 1)
    
    # Run integration tests only
    if args.integration:
        success = runner.run_integration_tests()
        sys.exit(0 if success else 1)
    
    # Run all tests (default)
    success = runner.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

# Import datetime for report generation
from datetime import datetime