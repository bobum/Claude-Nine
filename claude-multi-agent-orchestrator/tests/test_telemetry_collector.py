"""
Tests for telemetry collector with mocked dependencies.

This test suite validates telemetry collection without making real API calls
or requiring actual processes to monitor.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, UTC
import psutil

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from telemetry_collector import (
    TelemetryCollector,
    ProcessMetrics,
    GitActivity,
    TokenUsage,
    ActivityLog
)


@pytest.fixture
def mock_process():
    """Mock psutil.Process for testing without real processes."""
    with patch('telemetry_collector.psutil.Process') as mock:
        process = MagicMock()
        process.cpu_percent.return_value = 12.5
        process.memory_info.return_value = MagicMock(rss=268435456)  # 256 MB in bytes
        process.num_threads.return_value = 8
        process.status.return_value = 'running'
        mock.return_value = process
        yield process


@pytest.fixture
def collector(mock_process):
    """Create a telemetry collector instance for testing."""
    return TelemetryCollector(
        team_id="test-team-123",
        agent_names=["Agent1", "Agent2", "Monitor"],
        api_url="http://localhost:8000",
        check_interval=1  # Faster for testing
    )


class TestProcessMetrics:
    """Test process metrics collection."""

    def test_collect_process_metrics(self, collector, mock_process):
        """Test that process metrics are collected correctly."""
        metrics = collector._collect_process_metrics()

        assert isinstance(metrics, ProcessMetrics)
        assert metrics.cpu_percent == 12.5
        assert metrics.memory_mb == 256.0
        assert metrics.threads == 8
        assert metrics.status == "running"

    def test_process_metrics_handles_missing_process(self, collector):
        """Test graceful handling when process doesn't exist."""
        # Make cpu_percent raise NoSuchProcess
        with patch.object(collector.process, 'cpu_percent', side_effect=psutil.NoSuchProcess(999)):
            # Should not raise exception, should return zeros
            metrics = collector._collect_process_metrics()
            assert metrics.cpu_percent == 0.0
            assert metrics.memory_mb == 0.0
            assert metrics.status == "unknown"


class TestGitActivityParsing:
    """Test git activity parsing from log lines."""

    def test_parse_commit_with_message(self, collector):
        """Test parsing git commit with message."""
        line = 'git commit -m "Add new feature for users"'
        activity = collector._parse_git_activity(line)

        assert activity is not None
        assert activity.operation == "commit"
        assert activity.message == "Add new feature for users"

    def test_parse_branch_create(self, collector):
        """Test parsing branch creation."""
        line = "Creating branch: feature/telemetry-updates"
        activity = collector._parse_git_activity(line)

        assert activity is not None
        assert activity.operation == "branch_create"
        assert activity.branch == "feature/telemetry-updates"

    def test_parse_checkout(self, collector):
        """Test parsing git checkout."""
        line = "Switched to branch: main"
        activity = collector._parse_git_activity(line)

        assert activity is not None
        assert activity.operation == "checkout"
        assert activity.branch == "main"

    def test_parse_commit_with_file_count(self, collector):
        """Test parsing commit with file count."""
        line = "Committed 5 files successfully"
        activity = collector._parse_git_activity(line)

        assert activity is not None
        assert activity.operation == "commit"
        assert activity.files_changed == 5

    def test_parse_non_git_line(self, collector):
        """Test that non-git lines return None."""
        line = "This is just a regular log message"
        activity = collector._parse_git_activity(line)

        assert activity is None


class TestTokenUsageParsing:
    """Test token usage parsing from log lines."""

    def test_parse_token_usage_standard_format(self, collector):
        """Test parsing standard token usage format."""
        line = "Token usage: 1500 input, 500 output"
        usage = collector._parse_token_usage(line)

        assert usage is not None
        assert usage.input_tokens == 1500
        assert usage.output_tokens == 500
        assert usage.total_tokens == 2000
        assert usage.model == "claude-sonnet-4-5"
        # Cost calculation: (1500/1M * $3) + (500/1M * $15) = 0.0045 + 0.0075 = 0.012
        assert abs(usage.cost_usd - 0.012) < 0.0001

    def test_parse_token_usage_alternative_format(self, collector):
        """Test parsing alternative token format."""
        line = "Tokens: 2000 in, 1000 out"
        usage = collector._parse_token_usage(line)

        assert usage is not None
        assert usage.input_tokens == 2000
        assert usage.output_tokens == 1000
        assert usage.total_tokens == 3000

    def test_parse_token_usage_json_format(self, collector):
        """Test parsing JSON-style token format."""
        line = 'usage: input_tokens: 1234 output_tokens: 567'
        usage = collector._parse_token_usage(line)

        assert usage is not None
        assert usage.input_tokens == 1234
        assert usage.output_tokens == 567

    def test_parse_non_token_line(self, collector):
        """Test that non-token lines return None."""
        line = "This line has no token information"
        usage = collector._parse_token_usage(line)

        assert usage is None


class TestLogProcessing:
    """Test log line processing and agent context tracking."""

    def test_process_log_line_detects_agent_context(self, collector):
        """Test that agent context is detected from log lines."""
        line = "Agent: Agent1 working on task"
        collector.process_log_line(line)

        assert collector.current_agent == "Agent1"

    def test_process_log_line_tracks_git_activity(self, collector):
        """Test that git activities are tracked per agent."""
        collector.current_agent = "Agent1"
        line = 'git commit -m "Update feature"'

        collector.process_log_line(line)

        assert len(collector.agent_git_activities["Agent1"]) == 1
        activity = collector.agent_git_activities["Agent1"][0]
        assert activity.operation == "commit"
        assert activity.agent_name == "Agent1"

    def test_process_log_line_tracks_token_usage(self, collector):
        """Test that token usage is tracked per agent."""
        collector.current_agent = "Agent2"
        line = "Token usage: 1000 input, 500 output"

        collector.process_log_line(line)

        usage = collector.agent_token_usage["Agent2"]
        assert usage.input_tokens == 1000
        assert usage.output_tokens == 500

    def test_process_log_line_accumulates_tokens(self, collector):
        """Test that token usage accumulates across multiple calls."""
        collector.current_agent = "Agent1"

        collector.process_log_line("Token usage: 100 input, 50 output")
        collector.process_log_line("Token usage: 200 input, 100 output")

        usage = collector.agent_token_usage["Agent1"]
        assert usage.input_tokens == 300
        assert usage.output_tokens == 150
        assert usage.total_tokens == 450

    def test_activity_log_buffer_limits(self, collector):
        """Test that activity log buffer respects size limits."""
        collector.current_agent = "Agent1"

        # Add 150 log entries (more than the limit of 100)
        for i in range(150):
            collector.process_log_line(f"Log message {i}")

        # Should only keep the last 100
        assert len(collector.agent_activity_logs["Agent1"]) == 100


class TestTelemetryReporting:
    """Test telemetry reporting to API."""

    @patch('telemetry_collector.httpx.Client')
    def test_report_agent_telemetry_success(self, mock_client_class, collector, mock_process):
        """Test successful telemetry reporting."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client

        metrics = collector._collect_process_metrics()
        collector._report_agent_telemetry("Agent1", metrics)

        # Verify POST was called
        assert mock_client.post.called
        call_args = mock_client.post.call_args
        assert "Agent1" in call_args[0][0]
        assert call_args[1]['json']['team_id'] == "test-team-123"

    @patch('telemetry_collector.httpx.Client')
    def test_report_agent_telemetry_handles_error(self, mock_client_class, collector, mock_process):
        """Test that reporting errors are handled gracefully."""
        mock_client = MagicMock()
        mock_client.post.side_effect = Exception("Network error")
        mock_client_class.return_value.__enter__.return_value = mock_client

        metrics = collector._collect_process_metrics()

        # Should not raise exception
        collector._report_agent_telemetry("Agent1", metrics)


class TestTelemetryCollectorLifecycle:
    """Test telemetry collector start/stop lifecycle."""

    def test_start_creates_thread(self, collector):
        """Test that start() creates a background thread."""
        collector.start()

        assert collector.running is True
        assert collector.thread is not None
        assert collector.thread.daemon is True

        # Clean up
        collector.stop()

    def test_stop_terminates_thread(self, collector):
        """Test that stop() terminates the thread."""
        collector.start()
        time.sleep(0.1)  # Let thread start

        collector.stop()

        assert collector.running is False

    def test_get_summary(self, collector):
        """Test get_summary() returns correct data."""
        collector.current_agent = "Agent1"
        collector.process_log_line("Token usage: 1000 input, 500 output")
        collector.process_log_line('git commit -m "test"')

        summary = collector.get_summary()

        assert summary['team_id'] == "test-team-123"
        assert summary['tracked_agents'] == ["Agent1", "Agent2", "Monitor"]
        assert summary['total_tokens'] >= 1500
        assert summary['total_git_activities'] >= 1


class TestLogLevelDetection:
    """Test log level detection."""

    def test_determine_log_level_error(self, collector):
        """Test error detection."""
        assert collector._determine_log_level("ERROR: Something failed") == "error"
        assert collector._determine_log_level("Exception occurred") == "error"
        assert collector._determine_log_level("Task failed with error") == "error"

    def test_determine_log_level_warning(self, collector):
        """Test warning detection."""
        assert collector._determine_log_level("WARNING: Low memory") == "warning"
        assert collector._determine_log_level("warn: rate limit approaching") == "warning"

    def test_determine_log_level_info(self, collector):
        """Test info level default."""
        assert collector._determine_log_level("Task completed successfully") == "info"
        assert collector._determine_log_level("Processing request") == "info"


if __name__ == "__main__":
    # Run with: python -m pytest test_telemetry_collector.py -v
    pytest.main([__file__, "-v"])
