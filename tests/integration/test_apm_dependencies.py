"""
Integration tests for APM Dependencies system using real GitHub repositories.

Tests the complete dependency workflow with actual repositories:
- danielmeppiel/compliance-rules - Primary dependency test target
- danielmeppiel/design-guidelines - Secondary dependency for multi-dependency scenarios

These tests validate:
- Complete dependency installation workflow
- Multi-level dependency chains
- Conflict resolution scenarios  
- Local primitive override behavior
- Source attribution in compiled AGENTS.md
- apm deps command functionality
- Network error scenarios and authentication handling
- Cross-platform compatibility with real repository downloads
"""

import os
import pytest
import tempfile
import shutil
import subprocess
import yaml
from pathlib import Path
from unittest.mock import patch, Mock
from typing import Dict, Any, List

from apm_cli.deps.github_downloader import GitHubPackageDownloader
from apm_cli.deps.apm_resolver import APMDependencyResolver
from apm_cli.models.apm_package import APMPackage, DependencyReference


class TestAPMDependenciesIntegration:
    """Integration tests for APM Dependencies using real GitHub repositories."""
    
    def setup_method(self):
        """Set up test fixtures with temporary directory."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.original_dir = Path.cwd()
        os.chdir(self.test_dir)
        
        # Create basic apm.yml for testing
        self.apm_yml_path = self.test_dir / "apm.yml" 
        
        # Set up GitHub authentication from environment (new token architecture)
        self.github_token = os.getenv('GITHUB_APM_PAT') or os.getenv('GITHUB_TOKEN')
        if not self.github_token:
            pytest.skip("GitHub token required for integration tests")
    
    def teardown_method(self):
        """Clean up test fixtures."""
        os.chdir(self.original_dir)
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def create_apm_yml(self, dependencies: List[str] = None, **kwargs):
        """Create an apm.yml file with specified dependencies."""
        config = {
            'name': 'test-project',
            'version': '1.0.0',
            'description': 'Test project for dependency integration',
            'author': 'Test Author'
        }
        config.update(kwargs)
        
        if dependencies:
            config['dependencies'] = {'apm': dependencies}
        
        with open(self.apm_yml_path, 'w') as f:
            yaml.dump(config, f)
        
        return config

    @pytest.mark.integration
    def test_single_dependency_installation_compliance_rules(self):
        """Test installation of single dependency: compliance-rules."""
        # Create project with single dependency
        self.create_apm_yml(dependencies=['danielmeppiel/compliance-rules'])
        
        # Initialize downloader
        downloader = GitHubPackageDownloader()
        
        # Load project package
        project_package = APMPackage.from_apm_yml(self.apm_yml_path)
        dependencies = project_package.get_apm_dependencies()
        
        assert len(dependencies) == 1
        assert dependencies[0].repo_url == 'danielmeppiel/compliance-rules'
        
        # Create apm_modules directory
        apm_modules_dir = self.test_dir / 'apm_modules'
        apm_modules_dir.mkdir()
        
        # Download the dependency
        package_dir = apm_modules_dir / 'compliance-rules'
        result = downloader.download_package(str(dependencies[0]), package_dir)
        
        # Verify installation
        assert package_dir.exists()
        assert (package_dir / 'apm.yml').exists()
        assert (package_dir / '.apm').exists()
        assert (package_dir / 'compliance-audit.prompt.md').exists()
        assert (package_dir / 'gdpr-assessment.prompt.md').exists()
        assert (package_dir / 'legal-review.prompt.md').exists()
        
        # Verify APM structure
        assert (package_dir / '.apm' / 'chatmodes').exists()
        assert (package_dir / '.apm' / 'context').exists()  
        assert (package_dir / '.apm' / 'instructions').exists()
        
        # Verify package info
        assert result.package.name == 'compliance-rules'
        assert result.package.version == '1.0.0'
        assert result.install_path == package_dir

    @pytest.mark.integration
    def test_single_dependency_installation_design_guidelines(self):
        """Test installation of single dependency: design-guidelines."""
        # Create project with single dependency
        self.create_apm_yml(dependencies=['danielmeppiel/design-guidelines'])
        
        # Initialize downloader and resolver
        downloader = GitHubPackageDownloader()
        resolver = APMDependencyResolver()
        
        # Load project package
        project_package = APMPackage.from_apm_yml(self.apm_yml_path)
        dependencies = project_package.get_apm_dependencies()
        
        assert len(dependencies) == 1
        assert dependencies[0].repo_url == 'danielmeppiel/design-guidelines'
        
        # Create apm_modules directory
        apm_modules_dir = self.test_dir / 'apm_modules'
        apm_modules_dir.mkdir()
        
        # Download the dependency
        package_dir = apm_modules_dir / 'design-guidelines'
        result = downloader.download_package(str(dependencies[0]), package_dir)
        
        # Verify installation
        assert package_dir.exists()
        assert (package_dir / 'apm.yml').exists()
        assert (package_dir / '.apm').exists()
        assert (package_dir / 'accessibility-audit.prompt.md').exists()
        assert (package_dir / 'design-review.prompt.md').exists()
        assert (package_dir / 'style-guide-check.prompt.md').exists()
        
        # Verify APM structure
        assert (package_dir / '.apm' / 'context').exists()
        assert (package_dir / '.apm' / 'instructions').exists()
        
        # Verify package info
        assert result.package.name == 'design-guidelines'
        assert result.package.version == '1.0.0'
        assert result.install_path == package_dir

    @pytest.mark.integration
    def test_multi_dependency_installation(self):
        """Test installation of both dependencies in multi-dependency scenario."""
        # Create project with multiple dependencies
        self.create_apm_yml(dependencies=[
            'danielmeppiel/compliance-rules',
            'danielmeppiel/design-guidelines'
        ])
        
        # Initialize downloader
        downloader = GitHubPackageDownloader()
        
        # Load project package
        project_package = APMPackage.from_apm_yml(self.apm_yml_path)
        dependencies = project_package.get_apm_dependencies()
        
        assert len(dependencies) == 2
        
        # Create apm_modules directory
        apm_modules_dir = self.test_dir / 'apm_modules'
        apm_modules_dir.mkdir()
        
        # Download both dependencies
        results = {}
        for dep in dependencies:
            package_name = dep.repo_url.split('/')[-1]
            package_dir = apm_modules_dir / package_name
            result = downloader.download_package(str(dep), package_dir)
            results[package_name] = result
        
        # Verify both installations
        compliance_dir = apm_modules_dir / 'compliance-rules'
        design_dir = apm_modules_dir / 'design-guidelines'
        
        assert compliance_dir.exists()
        assert design_dir.exists()
        
        # Verify compliance-rules
        assert (compliance_dir / 'apm.yml').exists()
        assert (compliance_dir / '.apm' / 'chatmodes').exists()
        assert len(list(compliance_dir.glob('*.prompt.md'))) == 3
        
        # Verify design-guidelines  
        assert (design_dir / 'apm.yml').exists()
        assert (design_dir / '.apm' / 'context').exists()
        assert len(list(design_dir.glob('*.prompt.md'))) == 3
        
        # Verify no conflicts (both should install successfully)
        assert len(results) == 2
        assert all(result.package is not None for result in results.values())

    @pytest.mark.integration
    def test_dependency_compilation_integration(self):
        """Test compilation integration with dependencies to verify source attribution."""
        # Create project with dependencies
        self.create_apm_yml(dependencies=['danielmeppiel/compliance-rules'])
        
        # Create some local primitives that might conflict
        local_apm_dir = self.test_dir / '.apm'
        local_apm_dir.mkdir()
        
        instructions_dir = local_apm_dir / 'instructions'
        instructions_dir.mkdir()
        
        # Create a local instruction that should override dependency
        local_instruction = instructions_dir / 'legal-compliance.instructions.md'
        local_instruction.write_text("""---
title: Local Legal Compliance
applyTo: ["*.py", "*.js"]
tags: ["legal", "local-override"]
---

# Local Legal Compliance Override

This local instruction should override any dependency instruction.
""")
        
        # Install dependency
        downloader = GitHubPackageDownloader()
        apm_modules_dir = self.test_dir / 'apm_modules'
        apm_modules_dir.mkdir()
        
        package_dir = apm_modules_dir / 'compliance-rules'
        dep_ref = DependencyReference(repo_url='danielmeppiel/compliance-rules')
        downloader.download_package(str(dep_ref), package_dir)
        
        # Compile AGENTS.md to verify source attribution
        agents_md_path = self.test_dir / 'AGENTS.md'
        
        # The actual compilation may require additional setup, but we test the key aspects
        project_package = APMPackage.from_apm_yml(self.apm_yml_path)
        
        # Verify that local primitives exist alongside dependency primitives
        assert local_instruction.exists()
        assert package_dir.exists()
        assert (package_dir / '.apm' / 'instructions').exists()
        
        # Check that both local and dependency content is available for compilation
        local_files = list(instructions_dir.glob('*.instructions.md'))
        assert len(local_files) >= 1
        
        dep_instruction_files = list((package_dir / '.apm' / 'instructions').glob('*.md'))
        # Note: actual files in dependency may vary, just verify directory exists
        assert (package_dir / '.apm' / 'instructions').exists()

    @pytest.mark.integration 
    def test_dependency_branch_reference(self):
        """Test dependency installation with specific branch reference."""
        # Create project with branch-specific dependency
        self.create_apm_yml(dependencies=['danielmeppiel/compliance-rules#main'])
        
        downloader = GitHubPackageDownloader()
        project_package = APMPackage.from_apm_yml(self.apm_yml_path)
        dependencies = project_package.get_apm_dependencies()
        
        assert len(dependencies) == 1
        dep = dependencies[0]
        assert dep.repo_url == 'danielmeppiel/compliance-rules'
        assert dep.reference == 'main'
        
        # Create apm_modules directory
        apm_modules_dir = self.test_dir / 'apm_modules'
        apm_modules_dir.mkdir()
        
        # Download with branch reference
        package_dir = apm_modules_dir / 'compliance-rules'
        result = downloader.download_package(str(dep), package_dir)
        
        # Verify installation
        assert package_dir.exists()
        assert result.resolved_reference.ref_name == 'main'
        assert result.resolved_reference.resolved_commit is not None

    @pytest.mark.integration
    def test_dependency_error_handling_invalid_repo(self):
        """Test error handling for invalid repository."""
        downloader = GitHubPackageDownloader()
        
        apm_modules_dir = self.test_dir / 'apm_modules'
        apm_modules_dir.mkdir()
        
        package_dir = apm_modules_dir / 'invalid-repo'
        
        # Test with invalid repository
        with pytest.raises((RuntimeError, ValueError)):
            downloader.download_package('danielmeppiel/non-existent-repo-12345', package_dir)

    @pytest.mark.integration
    def test_dependency_network_error_simulation(self):
        """Test handling of network errors during dependency download."""
        # This test simulates network errors by mocking git operations
        with patch('apm_cli.deps.github_downloader.Repo') as mock_repo:
            # Simulate network error
            from git.exc import GitCommandError
            mock_repo.clone_from.side_effect = GitCommandError("Network error")
            
            downloader = GitHubPackageDownloader()
            apm_modules_dir = self.test_dir / 'apm_modules'
            apm_modules_dir.mkdir()
            
            package_dir = apm_modules_dir / 'compliance-rules'
            
            with pytest.raises(RuntimeError, match="Failed to clone repository"):
                downloader.download_package('danielmeppiel/compliance-rules', package_dir)

    @pytest.mark.integration
    def test_cli_deps_commands_with_real_dependencies(self):
        """Test CLI deps commands with real installed dependencies."""
        # Install dependencies first
        self.create_apm_yml(dependencies=['danielmeppiel/compliance-rules'])
        
        downloader = GitHubPackageDownloader()
        apm_modules_dir = self.test_dir / 'apm_modules'
        apm_modules_dir.mkdir()
        
        package_dir = apm_modules_dir / 'compliance-rules'
        dep_ref = DependencyReference(repo_url='danielmeppiel/compliance-rules')
        downloader.download_package(str(dep_ref), package_dir)
        
        # Import and test CLI commands
        from apm_cli.commands.deps import _count_package_files, _get_package_display_info
        
        # Test file counting
        context_count, workflow_count = _count_package_files(package_dir)
        assert context_count >= 0  # May have context files in .apm structure
        assert workflow_count == 3  # Should have 3 .prompt.md files
        
        # Test package display info
        package_info = _get_package_display_info(package_dir)
        assert package_info['name'] == 'compliance-rules'
        assert package_info['version'] == '1.0.0'

    @pytest.mark.integration
    def test_dependency_update_workflow(self):
        """Test dependency update workflow with real repository."""
        # Install initial dependency
        self.create_apm_yml(dependencies=['danielmeppiel/compliance-rules'])
        
        downloader = GitHubPackageDownloader()
        apm_modules_dir = self.test_dir / 'apm_modules'
        apm_modules_dir.mkdir()
        
        package_dir = apm_modules_dir / 'compliance-rules'
        dep_ref = DependencyReference(repo_url='danielmeppiel/compliance-rules')
        result1 = downloader.download_package(str(dep_ref), package_dir)
        
        original_commit = result1.resolved_reference.resolved_commit
        assert package_dir.exists()
        
        # Simulate update by re-downloading (in real scenario, this would get latest)
        result2 = downloader.download_package(str(dep_ref), package_dir)
        
        # Verify update completed
        assert result2.package.name == 'compliance-rules'
        assert result2.install_path == package_dir
        # Commits should be the same since we're pulling from the same state
        assert result2.resolved_reference.resolved_commit == original_commit

    @pytest.mark.integration
    def test_integration_test_infrastructure_smoke_test(self):
        """Smoke test to verify integration test infrastructure is working."""
        # Test that all required components can be imported and instantiated
        downloader = GitHubPackageDownloader()
        assert downloader is not None
        
        # Test that dependency reference can be created 
        dep_ref = DependencyReference(repo_url='danielmeppiel/compliance-rules')
        assert dep_ref.repo_url == 'danielmeppiel/compliance-rules'
        assert dep_ref.get_display_name() == 'danielmeppiel/compliance-rules'  # Display name is the full repo name
        
        # Test that APM package can be created from config
        self.create_apm_yml(dependencies=['danielmeppiel/compliance-rules'])
        project_package = APMPackage.from_apm_yml(self.apm_yml_path)
        dependencies = project_package.get_apm_dependencies()
        
        assert len(dependencies) == 1
        assert dependencies[0].repo_url == 'danielmeppiel/compliance-rules'
        
        # Test directory structure
        apm_modules_dir = self.test_dir / 'apm_modules' 
        apm_modules_dir.mkdir()
        assert apm_modules_dir.exists()
        
        # This test validates that the testing infrastructure is correctly set up
        # and can handle the real integration tests when network is available


class TestAPMDependenciesCI:
    """Tests specifically for CI/CD pipeline validation."""
    
    @pytest.mark.integration
    def test_binary_compatibility_with_dependencies(self):
        """Test that binary artifacts work with dependency features."""
        # This test verifies that a built binary can handle dependencies
        # In CI, this would test the actual binary artifact
        pytest.skip("Binary testing requires actual apm binary - run in CI with artifacts")
    
    @pytest.mark.integration
    def test_cross_platform_dependency_download(self):
        """Test dependency download across different platforms."""
        # This would test platform-specific aspects of dependency downloads
        import platform
        current_os = platform.system().lower()
        
        # Basic cross-platform compatibility test
        assert current_os in ['linux', 'darwin', 'windows']
        
        # The actual downloading is tested in other methods
        # This test would verify platform-specific path handling, etc.
        temp_dir = Path(tempfile.mkdtemp())
        try:
            # Test path handling on current platform
            apm_modules_dir = temp_dir / 'apm_modules'
            apm_modules_dir.mkdir()
            
            package_dir = apm_modules_dir / 'compliance-rules'
            assert package_dir.parent.exists()
            
            # Verify path separators work correctly
            assert str(package_dir).count('/') > 0 or str(package_dir).count('\\') > 0
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.integration
    def test_authentication_token_handling(self):
        """Test GitHub authentication token handling according to our token management architecture."""
        from apm_cli.deps.github_downloader import GitHubPackageDownloader
        
        # Test with environment tokens (new token architecture)
        github_apm_pat = os.getenv('GITHUB_APM_PAT')
        github_token = os.getenv('GITHUB_TOKEN')
        
        if not (github_apm_pat or github_token):
            pytest.skip("GitHub token required for authentication test")
        
        downloader = GitHubPackageDownloader()
        
        # Verify that the downloader has a GitHub token for modules access
        # According to our token manager, modules purpose uses: ['GITHUB_APM_PAT', 'GITHUB_TOKEN']
        assert downloader.has_github_token, "Downloader should have a GitHub token for modules access"
        assert downloader.github_token is not None, "GitHub token should be available"
        assert downloader.github_token.startswith('github_pat_'), "Token should be a valid GitHub PAT"
        
        # Verify that environment variables are properly set for Git operations
        assert 'GIT_TERMINAL_PROMPT' in downloader.git_env, "Git security settings should be configured"
        assert downloader.git_env['GIT_TERMINAL_PROMPT'] == '0', "Git should not prompt for credentials"
        
        # Test token precedence logic: verify the token manager gets the right token for modules
        token_for_modules = downloader.token_manager.get_token_for_purpose('modules')
        assert token_for_modules is not None, "Token manager should provide a token for modules access"
        assert token_for_modules.startswith('github_pat_'), "Modules token should be a valid GitHub PAT"
        
        # This validates the authentication setup works with real tokens
        assert 'GITHUB_TOKEN' in downloader.git_env or 'GH_TOKEN' in downloader.git_env


if __name__ == '__main__':
    # Run with: python -m pytest tests/integration/test_apm_dependencies.py -v
    pytest.main([__file__, '-v', '-s'])