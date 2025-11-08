#!/usr/bin/env python3
"""
ChatApp Test Runner
Runs all unit tests for the ChatApp backend with comprehensive reporting.
"""

import subprocess
import sys
import os
import argparse
from pathlib import Path

def run_command(command, description=""):
    """Run a command and return success status."""
    if description:
        print(f"🔄 {description}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Success: {description}")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"❌ Failed: {description}")
            if result.stderr:
                print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ Error running command: {e}")
        return False

def install_test_dependencies():
    """Install test dependencies if needed."""
    print("📦 Installing test dependencies...")
    
    # Install from requirements if it exists
    test_req_path = Path(__file__).parent / "test_requirements.txt"
    if test_req_path.exists():
        return run_command(f"pip install -r {test_req_path}", "Installing from test_requirements.txt")
    else:
        # Install individual packages
        packages = [
            "pytest==7.4.3",
            "pytest-asyncio==0.21.1", 
            "pytest-mock==3.12.0",
            "httpx==0.25.2",
            "python-socketio[client]==5.10.0",
            "coverage==7.3.2"
        ]
        
        success = True
        for package in packages:
            if not run_command(f"pip install {package}", f"Installing {package}"):
                success = False
        return success

def run_tests(test_type="all", verbose=False, coverage=False):
    """Run the specified tests."""
    # Change to the correct directory
    os.chdir(Path(__file__).parent)
    
    # Base pytest command
    cmd = ["pytest"]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=backend", "--cov-report=html", "--cov-report=term"])
    
    # Add test selection based on type
    if test_type == "unit":
        cmd.extend(["-m", "not integration"])
        cmd.extend(["tests/test_auth.py", "tests/test_database.py", "tests/conftest.py"])
    elif test_type == "integration": 
        cmd.extend(["-m", "integration"])
        cmd.append("tests/test_integration.py")
    elif test_type == "api":
        cmd.append("tests/test_api_routes.py")
    elif test_type == "socketio":
        cmd.append("tests/test_socketio.py")
    elif test_type == "auth":
        cmd.extend(["-m", "auth"])
        cmd.append("tests/test_auth.py")
    elif test_type == "database":
        cmd.extend(["-m", "database"])
        cmd.append("tests/test_database.py")
    else:  # all tests
        cmd.append("tests/")
    
    # Add output formatting
    cmd.extend(["--tb=short", "-ra"])
    
    command_str = " ".join(cmd)
    print(f"🧪 Running tests: {command_str}")
    
    return run_command(command_str, f"Running {test_type} tests")

def check_code_quality():
    """Run code quality checks."""
    print("🔍 Running code quality checks...")
    
    # Check if flake8 is available
    try:
        subprocess.run(["flake8", "--version"], capture_output=True, check=True)
        flake8_available = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        flake8_available = False
    
    if flake8_available:
        return run_command("flake8 backend/ --max-line-length=100 --ignore=E501,W503", "Code style check")
    else:
        print("⚠️ flake8 not available, skipping code quality check")
        return True

def generate_test_report():
    """Generate a comprehensive test report."""
    print("📊 Generating test report...")
    
    report_lines = [
        "# ChatApp Test Report",
        "",
        f"Generated on: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Test Structure",
        "",
        "- **conftest.py**: Test configuration and fixtures",
        "- **test_auth.py**: Authentication and JWT token tests",
        "- **test_database.py**: Database operations and CRUD tests",  
        "- **test_api_routes.py**: REST API endpoint tests",
        "- **test_socketio.py**: Real-time messaging and Socket.IO tests",
        "- **test_integration.py**: End-to-end workflow tests",
        "",
        "## Test Categories",
        "",
        "### Unit Tests",
        "- Authentication (login, registration, JWT)",
        "- Database operations (CRUD, connections)",
        "- Socket.IO (real-time messaging, rooms)",
        "",
        "### API Tests", 
        "- REST endpoints (/auth, /users, /chat)",
        "- Request/response validation",
        "- Authentication middleware",
        "",
        "### Integration Tests",
        "- Complete user workflows", 
        "- End-to-end messaging",
        "- Error recovery scenarios",
        "",
        "## Running Tests",
        "",
        "```bash",
        "# Install dependencies",
        "pip install -r test_requirements.txt",
        "",
        "# Run all tests",
        "python run_tests.py",
        "",
        "# Run specific test types",
        "python run_tests.py --type unit",
        "python run_tests.py --type integration", 
        "python run_tests.py --type auth",
        "",
        "# Run with coverage",
        "python run_tests.py --coverage",
        "```",
        "",
        "## Coverage Targets",
        "",
        "- Authentication: 95%+",
        "- Database operations: 90%+", 
        "- API routes: 85%+",
        "- Socket.IO: 80%+",
        "- Overall: 85%+",
    ]
    
    report_path = Path(__file__).parent / "TEST_REPORT.md"
    with open(report_path, 'w') as f:
        f.write('\n'.join(report_lines))
    
    print(f"📋 Test report generated: {report_path}")
    return True

def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="ChatApp Test Runner")
    parser.add_argument("--type", choices=["all", "unit", "integration", "api", "socketio", "auth", "database"],
                      default="all", help="Type of tests to run")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--coverage", "-c", action="store_true", help="Run with coverage")
    parser.add_argument("--install-deps", action="store_true", help="Install test dependencies")
    parser.add_argument("--quality-check", action="store_true", help="Run code quality checks")
    parser.add_argument("--report", action="store_true", help="Generate test report")
    
    args = parser.parse_args()
    
    print("🚀 ChatApp Test Runner")
    print("=" * 50)
    
    success = True
    
    # Install dependencies if requested
    if args.install_deps:
        if not install_test_dependencies():
            print("❌ Failed to install dependencies")
            return 1
    
    # Run code quality checks if requested
    if args.quality_check:
        if not check_code_quality():
            success = False
    
    # Run tests
    if not run_tests(args.type, args.verbose, args.coverage):
        success = False
    
    # Generate report if requested
    if args.report:
        if not generate_test_report():
            success = False
    
    print("=" * 50)
    if success:
        print("✅ All operations completed successfully!")
        return 0
    else:
        print("❌ Some operations failed. Please check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())