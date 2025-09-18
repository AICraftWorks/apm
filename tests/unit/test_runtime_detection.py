"""Unit tests for MCP runtime detection functionality."""

import unittest
from unittest.mock import patch, MagicMock

from apm_cli.cli import _detect_runtimes_from_scripts, _filter_available_runtimes


class TestRuntimeDetection(unittest.TestCase):
    """Test cases for runtime detection from apm.yml scripts."""
    
    def test_detect_single_runtime(self):
        """Test detecting single runtime from scripts."""
        scripts = {"start": "copilot --log-level all -p hello.md"}
        detected = _detect_runtimes_from_scripts(scripts)
        self.assertEqual(detected, ["copilot"])
    
    def test_detect_multiple_runtimes(self):
        """Test detecting multiple runtimes from scripts."""
        scripts = {
            "start": "copilot --log-level all -p hello.md",
            "debug": "codex --verbose hello.md", 
            "llm": "llm hello.md -m gpt-4"
        }
        detected = _detect_runtimes_from_scripts(scripts)
        # Order may vary due to set() usage, so check contents
        self.assertEqual(set(detected), {"copilot", "codex", "llm"})
        self.assertEqual(len(detected), 3)
    
    def test_detect_no_runtimes(self):
        """Test detecting no recognized runtimes."""
        scripts = {"start": "python hello.py", "test": "pytest"}
        detected = _detect_runtimes_from_scripts(scripts)
        self.assertEqual(detected, [])
    
    def test_detect_runtime_in_complex_command(self):
        """Test detecting runtime in complex command lines."""
        scripts = {
            "start": "RUST_LOG=debug codex --skip-git-repo-check hello.md",
            "dev": "npm run build && copilot -p prompt.md",
            "ai": "export MODEL=gpt-4 && llm prompt.md"
        }
        detected = _detect_runtimes_from_scripts(scripts)
        self.assertEqual(set(detected), {"codex", "copilot", "llm"})
    
    def test_detect_same_runtime_multiple_times(self):
        """Test that same runtime is only detected once."""
        scripts = {
            "start": "copilot -p hello.md",
            "dev": "copilot -p dev.md",
            "test": "copilot -p test.md"
        }
        detected = _detect_runtimes_from_scripts(scripts)
        self.assertEqual(detected, ["copilot"])
    
    def test_detect_empty_scripts(self):
        """Test handling empty scripts dictionary."""
        scripts = {}
        detected = _detect_runtimes_from_scripts(scripts)
        self.assertEqual(detected, [])
    
    def test_detect_runtime_case_sensitivity(self):
        """Test that runtime detection is case sensitive."""
        scripts = {
            "start": "COPILOT -p hello.md",  # Should not match
            "dev": "copilot -p hello.md"     # Should match
        }
        detected = _detect_runtimes_from_scripts(scripts)
        self.assertEqual(detected, ["copilot"])
    
    def test_detect_runtime_word_boundaries(self):
        """Test that runtime detection respects word boundaries."""
        scripts = {
            "start": "mycopilot -p hello.md",     # Should not match
            "dev": "copilot-cli -p hello.md",    # Should not match  
            "test": "copilot -p hello.md"        # Should match
        }
        detected = _detect_runtimes_from_scripts(scripts)
        self.assertEqual(detected, ["copilot"])


class TestRuntimeFiltering(unittest.TestCase):
    """Test cases for filtering available runtimes."""
    
    @patch('apm_cli.runtime.manager.RuntimeManager')
    @patch('apm_cli.factory.ClientFactory')
    def test_filter_available_runtimes_all_available(self, mock_factory_class, mock_manager_class):
        """Test filtering when all detected runtimes are available."""
        # Mock ClientFactory to accept all runtimes
        mock_factory_class.create_client.return_value = MagicMock()
        
        # Mock RuntimeManager to report all as available
        mock_manager = MagicMock()
        mock_manager.is_runtime_available.return_value = True
        mock_manager_class.return_value = mock_manager
        
        detected = ["copilot", "codex", "llm"]
        available = _filter_available_runtimes(detected)
        
        self.assertEqual(set(available), set(detected))
    
    @patch('apm_cli.runtime.manager.RuntimeManager')
    @patch('apm_cli.factory.ClientFactory')
    def test_filter_available_runtimes_partial_available(self, mock_factory_class, mock_manager_class):
        """Test filtering when only some runtimes are available."""
        # Mock ClientFactory to accept all runtimes
        mock_factory_class.create_client.return_value = MagicMock()
        
        # Mock RuntimeManager to report only copilot as available
        mock_manager = MagicMock()
        mock_manager.is_runtime_available.side_effect = lambda rt: rt == "copilot"
        mock_manager_class.return_value = mock_manager
        
        detected = ["copilot", "codex", "llm"]
        available = _filter_available_runtimes(detected)
        
        self.assertEqual(available, ["copilot"])
    
    @patch('apm_cli.runtime.manager.RuntimeManager')
    @patch('apm_cli.factory.ClientFactory')
    def test_filter_available_runtimes_none_available(self, mock_factory_class, mock_manager_class):
        """Test filtering when no runtimes are available."""
        # Mock ClientFactory to accept all runtimes
        mock_factory_class.create_client.return_value = MagicMock()
        
        # Mock RuntimeManager to report none as available
        mock_manager = MagicMock()
        mock_manager.is_runtime_available.return_value = False
        mock_manager_class.return_value = mock_manager
        
        detected = ["copilot", "codex", "llm"]
        available = _filter_available_runtimes(detected)
        
        self.assertEqual(available, [])
    
    @patch('apm_cli.factory.ClientFactory')
    def test_filter_unsupported_runtime_types(self, mock_factory_class):
        """Test filtering out unsupported runtime types."""
        # Mock ClientFactory to reject unsupported runtime
        def mock_create_client(runtime):
            if runtime == "unsupported":
                raise ValueError("Unsupported client type")
            return MagicMock()
        
        mock_factory_class.create_client.side_effect = mock_create_client
        
        # Mock missing RuntimeManager to trigger fallback
        with patch('apm_cli.runtime.manager.RuntimeManager', side_effect=ImportError):
            with patch('shutil.which') as mock_which:
                mock_which.side_effect = lambda cmd: cmd in ["copilot", "codex"]
                
                detected = ["copilot", "codex", "unsupported"]
                available = _filter_available_runtimes(detected)
                
                # Should filter out unsupported runtime
                self.assertEqual(set(available), {"copilot", "codex"})
    
    def test_filter_empty_list(self):
        """Test filtering empty list of detected runtimes."""
        detected = []
        available = _filter_available_runtimes(detected)
        self.assertEqual(available, [])


class TestRuntimeDetectionIntegration(unittest.TestCase):
    """Integration tests for runtime detection workflow."""
    
    def test_full_detection_workflow(self):
        """Test complete workflow from scripts to available runtimes."""
        scripts = {
            "start": "copilot --log-level all -p hello.md",
            "debug": "codex --verbose hello.md", 
            "build": "npm run build"  # Non-runtime command
        }
        
        # Detect runtimes from scripts
        detected = _detect_runtimes_from_scripts(scripts)
        expected_detected = {"copilot", "codex"}
        self.assertEqual(set(detected), expected_detected)
        
        # Filter available runtimes (this will use real system state)
        available = _filter_available_runtimes(detected)
        
        # Available should be subset of detected
        self.assertTrue(set(available).issubset(set(detected)))
        
        # Each available runtime should be creatable via factory
        from apm_cli.factory import ClientFactory
        for runtime in available:
            with self.subTest(runtime=runtime):
                try:
                    client = ClientFactory.create_client(runtime)
                    self.assertIsNotNone(client)
                except ValueError:
                    self.fail(f"Runtime {runtime} reported as available but not creatable")


if __name__ == "__main__":
    unittest.main()