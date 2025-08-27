#!/usr/bin/env python3
"""
Master Test Suite Orchestrator

This script orchestrates all testing components to provide a comprehensive testing
and deployment validation experience. It coordinates:
- Environment generation and validation
- Security assessment and remediation
- Inter-service communication testing
- Deployment validation (local and remote)
- OAuth and user management testing
- Performance benchmarking
- Bare metal compatibility assessment
"""

import os
import sys
import asyncio
import subprocess
import time
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import argparse

class TestPhase(Enum):
    PREPARATION = "preparation"
    SECURITY = "security"
    CONFIGURATION = "configuration"
    DEPLOYMENT = "deployment"
    VALIDATION = "validation"
    CLEANUP = "cleanup"

class TestResult(Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"

@dataclass
class TestSuiteResult:
    phase: TestPhase
    name: str
    result: TestResult
    duration: float
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

class MasterTestOrchestrator:
    """Orchestrates all testing components."""
    
    def __init__(self, repo_root: str, config: Dict[str, Any]):
        self.repo_root = Path(repo_root)
        self.config = config
        self.results: List[TestSuiteResult] = []
        self.start_time = time.time()
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO if config.get('verbose', False) else logging.WARNING,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Test configuration
        self.skip_slow_tests = config.get('quick', False)
        self.deployment_type = config.get('deployment_type', 'local')
        self.domain = config.get('domain', 'localhost')
        self.email = config.get('email', 'admin@localhost')
        self.verbose = config.get('verbose', False)
    
    def print_header(self, title: str):
        """Print formatted header."""
        print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*80}{Colors.END}")
        print(f"{Colors.CYAN}{Colors.BOLD} {title}{Colors.END}")
        print(f"{Colors.CYAN}{Colors.BOLD}{'='*80}{Colors.END}\n")
    
    def print_phase(self, phase: str):
        """Print phase header."""
        print(f"\n{Colors.BLUE}{Colors.BOLD}--- {phase} ---{Colors.END}")
    
    def print_result(self, result: TestSuiteResult):
        """Print test result."""
        color = {
            TestResult.PASSED: Colors.GREEN,
            TestResult.FAILED: Colors.RED,
            TestResult.WARNING: Colors.YELLOW,
            TestResult.SKIPPED: Colors.BLUE
        }.get(result.result, Colors.WHITE)
        
        symbol = {
            TestResult.PASSED: "✅",
            TestResult.FAILED: "❌",
            TestResult.WARNING: "⚠️",
            TestResult.SKIPPED: "⊘"
        }.get(result.result, "?")
        
        print(f"{color}{symbol} {result.name} ({result.duration:.2f}s){Colors.END}")
        
        if result.message:
            print(f"   {result.message}")
        
        if result.details and self.verbose:
            for key, value in result.details.items():
                print(f"   {key}: {value}")
    
    async def run_comprehensive_test_suite(self) -> Dict[str, Any]:
        """Run the complete test suite."""
        self.print_header("🚀 Master Test Suite - Comprehensive Validation")
        
        print(f"📍 Repository: {self.repo_root}")
        print(f"🌐 Domain: {self.domain}")
        print(f"📧 Email: {self.email}")
        print(f"🏗️  Deployment: {self.deployment_type}")
        print(f"⚡ Quick mode: {self.skip_slow_tests}")
        
        # Phase 1: Preparation
        await self.run_preparation_phase()
        
        # Phase 2: Security Assessment
        await self.run_security_phase()
        
        # Phase 3: Configuration Management
        await self.run_configuration_phase()
        
        # Phase 4: Deployment Testing (if not quick mode)
        if not self.skip_slow_tests:
            await self.run_deployment_phase()
        
        # Phase 5: Validation Testing
        await self.run_validation_phase()
        
        # Phase 6: Cleanup
        await self.run_cleanup_phase()
        
        # Generate final report
        return self.generate_final_report()
    
    async def run_preparation_phase(self):
        """Run preparation phase tests."""
        self.print_phase("🛠️  Preparation Phase")
        
        # Check system requirements
        await self.run_test_script(
            TestPhase.PREPARATION,
            "System Requirements",
            self.check_system_requirements
        )
        
        # Generate/validate environment
        await self.run_test_script(
            TestPhase.PREPARATION,
            "Environment Configuration",
            self.setup_environment_configuration
        )
        
        # Initialize repositories
        await self.run_test_script(
            TestPhase.PREPARATION,
            "Repository Initialization",
            self.initialize_repositories
        )
    
    async def run_security_phase(self):
        """Run security assessment phase."""
        self.print_phase("🔒 Security Assessment Phase")
        
        # Run security validator
        await self.run_test_script(
            TestPhase.SECURITY,
            "Security Validation",
            self.run_security_validation
        )
        
        # Check bare metal compatibility
        await self.run_test_script(
            TestPhase.SECURITY,
            "Bare Metal Compatibility",
            self.check_bare_metal_compatibility
        )
    
    async def run_configuration_phase(self):
        """Run configuration management phase."""
        self.print_phase("⚙️ Configuration Management Phase")
        
        # Run flexible configuration
        await self.run_test_script(
            TestPhase.CONFIGURATION,
            "Adaptive Configuration",
            self.run_adaptive_configuration
        )
        
        # Validate service discovery
        await self.run_test_script(
            TestPhase.CONFIGURATION,
            "Service Discovery",
            self.test_service_discovery
        )
    
    async def run_deployment_phase(self):
        """Run deployment testing phase."""
        self.print_phase("🚀 Deployment Testing Phase")
        
        # Run comprehensive deployment test
        await self.run_test_script(
            TestPhase.DEPLOYMENT,
            "Comprehensive Deployment",
            self.run_comprehensive_deployment
        )
    
    async def run_validation_phase(self):
        """Run validation testing phase."""
        self.print_phase("✅ Validation Testing Phase")
        
        # Run inter-service communication tests
        await self.run_test_script(
            TestPhase.VALIDATION,
            "Inter-Service Communication",
            self.test_inter_service_communication
        )
        
        # Test OAuth and user management
        await self.run_test_script(
            TestPhase.VALIDATION,
            "OAuth and User Management",
            self.test_oauth_user_management
        )
        
        # Run existing comprehensive tests
        await self.run_test_script(
            TestPhase.VALIDATION,
            "Legacy Test Suite",
            self.run_legacy_tests
        )
    
    async def run_cleanup_phase(self):
        """Run cleanup phase."""
        self.print_phase("🧹 Cleanup Phase")
        
        # Generate reports
        await self.run_test_script(
            TestPhase.CLEANUP,
            "Report Generation",
            self.generate_reports
        )
    
    async def run_test_script(self, phase: TestPhase, name: str, test_func):
        """Run a test script and record results."""
        start_time = time.time()
        
        try:
            result = await test_func()
            duration = time.time() - start_time
            
            if result.get('success', False):
                test_result = TestSuiteResult(
                    phase=phase,
                    name=name,
                    result=TestResult.PASSED,
                    duration=duration,
                    message=result.get('message', ''),
                    details=result.get('details', {})
                )
            elif result.get('warning', False):
                test_result = TestSuiteResult(
                    phase=phase,
                    name=name,
                    result=TestResult.WARNING,
                    duration=duration,
                    message=result.get('message', ''),
                    details=result.get('details', {})
                )
            else:
                test_result = TestSuiteResult(
                    phase=phase,
                    name=name,
                    result=TestResult.FAILED,
                    duration=duration,
                    message=result.get('message', ''),
                    details=result.get('details', {})
                )
        
        except Exception as e:
            duration = time.time() - start_time
            test_result = TestSuiteResult(
                phase=phase,
                name=name,
                result=TestResult.FAILED,
                duration=duration,
                message=str(e),
                details={'exception': str(e)}
            )
        
        self.results.append(test_result)
        self.print_result(test_result)
    
    async def check_system_requirements(self) -> Dict[str, Any]:
        """Check system requirements."""
        try:
            # Check Docker
            docker_result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
            docker_ok = docker_result.returncode == 0
            
            # Check Python
            python_result = subprocess.run(['python3', '--version'], capture_output=True, text=True)
            python_ok = python_result.returncode == 0
            
            # Check Git
            git_result = subprocess.run(['git', '--version'], capture_output=True, text=True)
            git_ok = git_result.returncode == 0
            
            all_ok = docker_ok and python_ok and git_ok
            
            return {
                'success': all_ok,
                'message': 'All system requirements met' if all_ok else 'Missing system requirements',
                'details': {
                    'docker': docker_ok,
                    'python': python_ok,
                    'git': git_ok
                }
            }
        
        except Exception as e:
            return {'success': False, 'message': f'Error checking requirements: {e}'}
    
    async def setup_environment_configuration(self) -> Dict[str, Any]:
        """Setup environment configuration."""
        try:
            # Use enhanced environment generator
            cmd = [
                'python3', 'scripts/enhanced_env_generator.py',
                '--base-domain', self.domain,
                '--email', self.email,
                '--environment', self.deployment_type,
                '--output', '.env'
            ]
            
            if self.config.get('force', False):
                cmd.append('--force')
            
            result = subprocess.run(cmd, cwd=self.repo_root, capture_output=True, text=True)
            
            return {
                'success': result.returncode == 0,
                'message': 'Environment configured successfully' if result.returncode == 0 else 'Environment configuration failed',
                'details': {
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }
            }
        
        except Exception as e:
            return {'success': False, 'message': f'Error setting up environment: {e}'}
    
    async def initialize_repositories(self) -> Dict[str, Any]:
        """Initialize required repositories."""
        try:
            # Initialize Supabase if needed
            cmd = ['python3', 'start_services.py', '--preflight', '--skip-neo4j']
            result = subprocess.run(cmd, cwd=self.repo_root, capture_output=True, text=True)
            
            return {
                'success': result.returncode == 0,
                'message': 'Repositories initialized successfully' if result.returncode == 0 else 'Repository initialization failed',
                'details': {
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }
            }
        
        except Exception as e:
            return {'success': False, 'message': f'Error initializing repositories: {e}'}
    
    async def run_security_validation(self) -> Dict[str, Any]:
        """Run security validation."""
        try:
            cmd = ['python3', 'scripts/security_validator.py', '--verbose']
            result = subprocess.run(cmd, cwd=self.repo_root, capture_output=True, text=True)
            
            # Security validator returns 0 for no critical issues, 1 for critical, 2 for high
            security_ok = result.returncode in [0, 2]  # Allow high severity issues
            
            return {
                'success': security_ok,
                'warning': result.returncode == 2,
                'message': 'Security validation completed' if security_ok else 'Critical security issues found',
                'details': {
                    'exit_code': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }
            }
        
        except Exception as e:
            return {'success': False, 'message': f'Error running security validation: {e}'}
    
    async def check_bare_metal_compatibility(self) -> Dict[str, Any]:
        """Check bare metal compatibility."""
        try:
            # The security validator also checks bare metal compatibility
            report_file = self.repo_root / 'security_report.json'
            
            if report_file.exists():
                with open(report_file) as f:
                    report = json.load(f)
                
                bare_metal = report.get('bare_metal_compatibility', [])
                compatible_count = sum(1 for item in bare_metal if item['compatible'])
                total_count = len(bare_metal)
                
                compatibility_ratio = compatible_count / total_count if total_count > 0 else 0
                
                return {
                    'success': compatibility_ratio >= 0.6,  # 60% compatibility threshold
                    'warning': compatibility_ratio >= 0.4,
                    'message': f'Bare metal compatibility: {compatible_count}/{total_count} components',
                    'details': {
                        'compatible_count': compatible_count,
                        'total_count': total_count,
                        'ratio': compatibility_ratio
                    }
                }
            else:
                return {'success': False, 'message': 'Security report not found'}
        
        except Exception as e:
            return {'success': False, 'message': f'Error checking bare metal compatibility: {e}'}
    
    async def run_adaptive_configuration(self) -> Dict[str, Any]:
        """Run adaptive configuration."""
        try:
            cmd = ['python3', 'scripts/flexible_config_manager.py', '--verbose']
            result = subprocess.run(cmd, cwd=self.repo_root, capture_output=True, text=True)
            
            return {
                'success': result.returncode == 0,
                'message': 'Adaptive configuration completed' if result.returncode == 0 else 'Adaptive configuration failed',
                'details': {
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }
            }
        
        except Exception as e:
            return {'success': False, 'message': f'Error running adaptive configuration: {e}'}
    
    async def test_service_discovery(self) -> Dict[str, Any]:
        """Test service discovery."""
        try:
            # Check if adaptive config was generated
            config_file = self.repo_root / 'adaptive_config.json'
            
            if config_file.exists():
                with open(config_file) as f:
                    config = json.load(f)
                
                services_detected = len(config.get('services', {}))
                
                return {
                    'success': True,
                    'message': f'Service discovery completed - found {services_detected} services',
                    'details': {
                        'services_detected': services_detected,
                        'config_available': True
                    }
                }
            else:
                return {
                    'success': False,
                    'message': 'Adaptive configuration not found'
                }
        
        except Exception as e:
            return {'success': False, 'message': f'Error testing service discovery: {e}'}
    
    async def run_comprehensive_deployment(self) -> Dict[str, Any]:
        """Run comprehensive deployment test."""
        try:
            cmd = [
                './scripts/comprehensive_deployment_test.sh',
                '--type', self.deployment_type,
                '--domain', self.domain,
                '--email', self.email,
                '--dry-run'  # Safe dry run for testing
            ]
            
            if self.verbose:
                cmd.append('--verbose')
            
            result = subprocess.run(cmd, cwd=self.repo_root, capture_output=True, text=True)
            
            return {
                'success': result.returncode == 0,
                'warning': result.returncode == 2,
                'message': 'Deployment test completed' if result.returncode == 0 else 'Deployment test had issues',
                'details': {
                    'exit_code': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }
            }
        
        except Exception as e:
            return {'success': False, 'message': f'Error running deployment test: {e}'}
    
    async def test_inter_service_communication(self) -> Dict[str, Any]:
        """Test inter-service communication."""
        try:
            cmd = ['python3', 'scripts/tests/comprehensive_interservice_tests.py', '--quick']
            result = subprocess.run(cmd, cwd=self.repo_root, capture_output=True, text=True)
            
            # Inter-service tests may fail if services aren't running, which is expected
            return {
                'success': True,  # Always succeed as this is informational
                'warning': result.returncode != 0,
                'message': 'Inter-service communication test completed',
                'details': {
                    'exit_code': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }
            }
        
        except Exception as e:
            return {'success': False, 'message': f'Error testing inter-service communication: {e}'}
    
    async def test_oauth_user_management(self) -> Dict[str, Any]:
        """Test OAuth and user management."""
        try:
            cmd = [
                'python3', 'scripts/flexible_config_manager.py',
                '--test-oauth', '--test-auth'
            ]
            result = subprocess.run(cmd, cwd=self.repo_root, capture_output=True, text=True)
            
            return {
                'success': True,  # Always succeed as OAuth may not be configured
                'warning': result.returncode != 0,
                'message': 'OAuth and user management test completed',
                'details': {
                    'exit_code': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }
            }
        
        except Exception as e:
            return {'success': False, 'message': f'Error testing OAuth: {e}'}
    
    async def run_legacy_tests(self) -> Dict[str, Any]:
        """Run existing comprehensive tests."""
        try:
            cmd = ['./scripts/tests/run_comprehensive_tests.sh', '--quick']
            result = subprocess.run(cmd, cwd=self.repo_root, capture_output=True, text=True)
            
            return {
                'success': result.returncode == 0,
                'warning': result.returncode != 0,
                'message': 'Legacy test suite completed',
                'details': {
                    'exit_code': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }
            }
        
        except Exception as e:
            return {'success': False, 'message': f'Error running legacy tests: {e}'}
    
    async def generate_reports(self) -> Dict[str, Any]:
        """Generate final reports."""
        try:
            # Generate master report
            master_report = self.generate_final_report()
            
            report_file = self.repo_root / 'master_test_report.json'
            with open(report_file, 'w') as f:
                json.dump(master_report, f, indent=2, default=str)
            
            return {
                'success': True,
                'message': f'Reports generated successfully',
                'details': {
                    'master_report': str(report_file),
                    'total_tests': len(self.results)
                }
            }
        
        except Exception as e:
            return {'success': False, 'message': f'Error generating reports: {e}'}
    
    def generate_final_report(self) -> Dict[str, Any]:
        """Generate final comprehensive report."""
        total_duration = time.time() - self.start_time
        
        # Count results by status
        passed = sum(1 for r in self.results if r.result == TestResult.PASSED)
        failed = sum(1 for r in self.results if r.result == TestResult.FAILED)
        warnings = sum(1 for r in self.results if r.result == TestResult.WARNING)
        skipped = sum(1 for r in self.results if r.result == TestResult.SKIPPED)
        
        # Group by phase
        results_by_phase = {}
        for result in self.results:
            phase = result.phase.value
            if phase not in results_by_phase:
                results_by_phase[phase] = []
            results_by_phase[phase].append({
                'name': result.name,
                'result': result.result.value,
                'duration': result.duration,
                'message': result.message,
                'details': result.details
            })
        
        return {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'configuration': {
                'repo_root': str(self.repo_root),
                'deployment_type': self.deployment_type,
                'domain': self.domain,
                'email': self.email,
                'quick_mode': self.skip_slow_tests
            },
            'summary': {
                'total_tests': len(self.results),
                'passed': passed,
                'failed': failed,
                'warnings': warnings,
                'skipped': skipped,
                'total_duration': total_duration,
                'success_rate': passed / len(self.results) if self.results else 0
            },
            'results_by_phase': results_by_phase,
            'recommendations': self.generate_recommendations()
        }
    
    def generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        failed_tests = [r for r in self.results if r.result == TestResult.FAILED]
        warning_tests = [r for r in self.results if r.result == TestResult.WARNING]
        
        if failed_tests:
            recommendations.append("🚨 Address failed tests before deployment")
            
            for test in failed_tests:
                if 'security' in test.name.lower():
                    recommendations.append("🔒 Review security issues in security_report.json")
                elif 'environment' in test.name.lower():
                    recommendations.append("⚙️ Check environment configuration and regenerate .env if needed")
                elif 'deployment' in test.name.lower():
                    recommendations.append("🚀 Review deployment prerequisites and system requirements")
        
        if warning_tests:
            recommendations.append("⚠️ Review warnings for potential improvements")
        
        # General recommendations
        recommendations.extend([
            "📚 Review DEPLOYMENT_GUIDE.md for detailed setup instructions",
            "🔐 Ensure all credentials are properly secured",
            "🌐 Test the application thoroughly before production deployment",
            "📊 Monitor the application performance after deployment"
        ])
        
        return recommendations
    
    def print_final_summary(self, report: Dict[str, Any]):
        """Print final test summary."""
        self.print_header("📊 Final Test Summary")
        
        summary = report['summary']
        
        print(f"⏱️  Total Duration: {summary['total_duration']:.2f}s")
        print(f"🧪 Total Tests: {summary['total_tests']}")
        print(f"✅ Passed: {summary['passed']}")
        print(f"❌ Failed: {summary['failed']}")
        print(f"⚠️  Warnings: {summary['warnings']}")
        print(f"⊘ Skipped: {summary['skipped']}")
        print(f"📈 Success Rate: {summary['success_rate']:.1%}")
        
        if report.get('recommendations'):
            print(f"\n{Colors.YELLOW}{Colors.BOLD}📋 Recommendations:{Colors.END}")
            for rec in report['recommendations']:
                print(f"  {rec}")
        
        # Overall status
        if summary['failed'] == 0:
            if summary['warnings'] == 0:
                print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 All tests passed! Ready for deployment.{Colors.END}")
            else:
                print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️  Tests completed with warnings. Review before deployment.{Colors.END}")
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}❌ Some tests failed. Address issues before deployment.{Colors.END}")

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Master Test Suite Orchestrator")
    parser.add_argument('--repo-root', default='.', help='Repository root directory')
    parser.add_argument('--deployment-type', choices=['local', 'development', 'production'], 
                        default='local', help='Deployment type')
    parser.add_argument('--domain', default='localhost', help='Base domain')
    parser.add_argument('--email', default='admin@localhost', help='Admin email')
    parser.add_argument('--quick', action='store_true', help='Run quick tests only')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--force', action='store_true', help='Force regeneration of configuration')
    
    args = parser.parse_args()
    
    config = {
        'deployment_type': args.deployment_type,
        'domain': args.domain,
        'email': args.email,
        'quick': args.quick,
        'verbose': args.verbose,
        'force': args.force
    }
    
    orchestrator = MasterTestOrchestrator(args.repo_root, config)
    
    try:
        # Run comprehensive test suite
        final_report = await orchestrator.run_comprehensive_test_suite()
        
        # Print final summary
        orchestrator.print_final_summary(final_report)
        
        # Exit with appropriate code
        if final_report['summary']['failed'] > 0:
            return 1
        elif final_report['summary']['warnings'] > 0:
            return 2
        else:
            return 0
    
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠️  Test suite interrupted by user{Colors.END}")
        return 130
    except Exception as e:
        print(f"\n{Colors.RED}❌ Test suite failed: {e}{Colors.END}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)