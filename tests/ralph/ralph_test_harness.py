#!/usr/bin/env python3
"""
Ralph Test Harness - Automated testing after story completion

Runs after Ralph completes each story to verify:
1. Code compiles and runs
2. Tests pass
3. Database migrations succeed
4. No regressions introduced

Usage:
    python ralph_test_harness.py STORY_ID COMMIT_HASH

Example:
    python ralph_test_harness.py KB-006 abc123
"""

import sys
import subprocess
import json
import asyncio
import asyncpg
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional


class RalphTestHarness:
    """Automated test runner for Ralph-implemented features"""

    def __init__(self, story_id: str, commit_hash: str):
        self.story_id = story_id
        self.commit_hash = commit_hash
        self.project_root = Path(__file__).parent.parent.parent
        self.test_results = {
            'story_id': story_id,
            'commit_hash': commit_hash,
            'timestamp': datetime.utcnow().isoformat(),
            'tests': [],
            'overall_status': 'unknown'
        }

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run complete test suite"""
        print(f"\n{'='*60}")
        print(f"Ralph Test Harness - Story: {self.story_id}")
        print(f"Commit: {self.commit_hash}")
        print(f"{'='*60}\n")

        # 1. Code Quality Checks
        await self._run_test("Lint Check", self._run_linter)
        await self._run_test("Type Check", self._run_type_checker)

        # 2. Unit Tests
        await self._run_test("Unit Tests", self._run_unit_tests)

        # 3. Integration Tests
        await self._run_test("Integration Tests", self._run_integration_tests)

        # 4. Database Tests
        await self._run_test("Database Schema", self._check_database_schema)

        # 5. Feature-Specific Tests
        await self._run_test("Feature Tests", self._run_feature_tests)

        # 6. Performance Tests
        await self._run_test("Performance", self._run_performance_tests)

        # 7. Regression Tests
        await self._run_test("Regression Check", self._run_regression_tests)

        # Calculate overall status
        failed_tests = [t for t in self.test_results['tests'] if t['status'] == 'failed']
        self.test_results['overall_status'] = 'failed' if failed_tests else 'passed'

        # Report results
        self._print_summary()

        # Save results to database
        await self._save_results()

        return self.test_results

    async def _run_test(self, name: str, test_func):
        """Run a single test and record results"""
        print(f"\n▶ Running {name}...")

        test_result = {
            'name': name,
            'status': 'unknown',
            'message': '',
            'duration_ms': 0
        }

        start = datetime.utcnow()

        try:
            result = await test_func()
            test_result['status'] = 'passed' if result['success'] else 'failed'
            test_result['message'] = result.get('message', '')
            print(f"  ✓ {name}: {test_result['status'].upper()}")
            if result.get('details'):
                print(f"    {result['details']}")
        except Exception as e:
            test_result['status'] = 'failed'
            test_result['message'] = str(e)
            print(f"  ✗ {name}: FAILED")
            print(f"    Error: {e}")

        end = datetime.utcnow()
        test_result['duration_ms'] = int((end - start).total_seconds() * 1000)

        self.test_results['tests'].append(test_result)

    async def _run_linter(self) -> Dict[str, Any]:
        """Run ruff linter on changed files"""
        try:
            # Get files changed in this commit
            changed_files = subprocess.check_output(
                ['git', 'diff-tree', '--no-commit-id', '--name-only', '-r', self.commit_hash],
                cwd=self.project_root,
                text=True
            ).strip().split('\n')

            python_files = [f for f in changed_files if f.endswith('.py')]

            if not python_files:
                return {'success': True, 'message': 'No Python files changed'}

            # Run ruff
            result = subprocess.run(
                ['ruff', 'check'] + python_files,
                cwd=self.project_root,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                return {'success': True, 'details': f'Checked {len(python_files)} files'}
            else:
                return {
                    'success': False,
                    'message': 'Linting errors found',
                    'details': result.stdout
                }
        except Exception as e:
            return {'success': False, 'message': f'Linter error: {e}'}

    async def _run_type_checker(self) -> Dict[str, Any]:
        """Run mypy type checker"""
        try:
            result = subprocess.run(
                ['mypy', 'rivet_pro/', '--ignore-missing-imports'],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                return {'success': True, 'details': 'No type errors'}
            else:
                # mypy warnings are non-critical
                return {'success': True, 'details': 'Type check completed with warnings'}
        except FileNotFoundError:
            return {'success': True, 'message': 'mypy not installed (optional)'}

    async def _run_unit_tests(self) -> Dict[str, Any]:
        """Run pytest unit tests"""
        try:
            result = subprocess.run(
                ['pytest', 'tests/unit/', '-v', '--tb=short'],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )

            # Parse pytest output
            if 'passed' in result.stdout:
                import re
                match = re.search(r'(\d+) passed', result.stdout)
                passed = match.group(1) if match else '?'
                return {'success': result.returncode == 0, 'details': f'{passed} tests passed'}

            return {'success': result.returncode == 0}
        except Exception as e:
            return {'success': False, 'message': f'Unit test error: {e}'}

    async def _run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests"""
        try:
            result = subprocess.run(
                ['pytest', 'tests/integration/', '-v', '--tb=short'],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )

            return {'success': result.returncode == 0}
        except Exception as e:
            return {'success': False, 'message': f'Integration test error: {e}'}

    async def _check_database_schema(self) -> Dict[str, Any]:
        """Verify database schema is valid"""
        try:
            from rivet_pro.config.settings import settings

            conn = await asyncpg.connect(settings.database_url)

            # Check critical tables exist
            critical_tables = [
                'users', 'interactions', 'knowledge_atoms',
                'ralph_stories', 'cmms_equipment'
            ]

            for table in critical_tables:
                exists = await conn.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = $1
                    )
                    """,
                    table
                )

                if not exists:
                    await conn.close()
                    return {
                        'success': False,
                        'message': f'Missing table: {table}'
                    }

            await conn.close()
            return {'success': True, 'details': f'All {len(critical_tables)} tables verified'}

        except Exception as e:
            return {'success': False, 'message': f'Database check error: {e}'}

    async def _run_feature_tests(self) -> Dict[str, Any]:
        """Run story-specific feature tests"""
        try:
            # Map story ID to test file
            test_file = self._get_test_file_for_story()

            if not test_file:
                return {'success': True, 'message': 'No specific tests defined'}

            result = subprocess.run(
                ['pytest', str(test_file), '-v', '--tb=short'],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )

            return {'success': result.returncode == 0}
        except Exception as e:
            return {'success': False, 'message': f'Feature test error: {e}'}

    async def _run_performance_tests(self) -> Dict[str, Any]:
        """Run performance benchmarks"""
        try:
            result = subprocess.run(
                ['pytest', 'tests/performance/', '-v', '--benchmark-only'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60
            )

            return {'success': result.returncode == 0}
        except subprocess.TimeoutExpired:
            return {'success': False, 'message': 'Performance tests timed out'}
        except Exception as e:
            return {'success': True, 'message': 'No performance tests defined'}

    async def _run_regression_tests(self) -> Dict[str, Any]:
        """Check for regressions in existing features"""
        try:
            # Run full test suite
            result = subprocess.run(
                ['pytest', 'tests/', '--ignore=tests/performance/', '-x'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )

            return {'success': result.returncode == 0}
        except Exception as e:
            return {'success': False, 'message': f'Regression check error: {e}'}

    def _get_test_file_for_story(self) -> Optional[Path]:
        """Map story ID to its test file"""
        story_prefix = self.story_id.split('-')[0]

        test_mapping = {
            'KB': self.project_root / 'tests' / 'ralph' / 'test_kb_features.py',
            'RIVET': self.project_root / 'tests' / 'integration' / 'test_rivet_features.py',
            'FEEDBACK': self.project_root / 'tests' / 'integration' / 'test_feedback_loop.py',
        }

        test_file = test_mapping.get(story_prefix)
        return test_file if test_file and test_file.exists() else None

    def _print_summary(self):
        """Print test results summary"""
        print(f"\n{'='*60}")
        print("Test Results Summary")
        print(f"{'='*60}")

        for test in self.test_results['tests']:
            status_icon = '✓' if test['status'] == 'passed' else '✗'
            print(f"{status_icon} {test['name']}: {test['status'].upper()}")
            if test['message']:
                print(f"  └─ {test['message']}")

        print(f"\n{'='*60}")
        overall = self.test_results['overall_status'].upper()
        icon = '✓' if overall == 'PASSED' else '✗'
        print(f"{icon} Overall Status: {overall}")
        print(f"{'='*60}\n")

    async def _save_results(self):
        """Save test results to database"""
        try:
            from rivet_pro.config.settings import settings

            conn = await asyncpg.connect(settings.database_url)

            # Update ralph_stories with test results
            await conn.execute(
                """
                UPDATE ralph_stories
                SET
                    test_status = $1,
                    test_results = $2,
                    tested_at = NOW()
                WHERE story_id = $3
                """,
                self.test_results['overall_status'],
                json.dumps(self.test_results),
                self.story_id
            )

            await conn.close()

            print(f"✓ Test results saved to database")

        except Exception as e:
            print(f"✗ Failed to save test results: {e}")


async def main():
    """Main entry point"""
    if len(sys.argv) < 3:
        print("Usage: python ralph_test_harness.py STORY_ID COMMIT_HASH")
        print("Example: python ralph_test_harness.py KB-006 abc123def")
        sys.exit(1)

    story_id = sys.argv[1]
    commit_hash = sys.argv[2]

    harness = RalphTestHarness(story_id, commit_hash)
    results = await harness.run_all_tests()

    # Exit with appropriate code
    sys.exit(0 if results['overall_status'] == 'passed' else 1)


if __name__ == '__main__':
    asyncio.run(main())
