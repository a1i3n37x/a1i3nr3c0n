"""Tests for the __main__ module."""

from unittest.mock import patch


class TestMain:
    """Test __main__ module."""

    def test_main_entry_point(self):
        """Test that __main__ module structure is correct."""
        # Just verify the module exists and has the expected structure
        import alienrecon.__main__ as main_module

        # Check the module has the expected content
        assert hasattr(main_module, "__name__")

        # Since __main__ executes app() at module level,
        # we can't easily test it without running the app

    def test_main_as_module(self):
        """Test running alienrecon as python -m alienrecon."""
        # Mock sys.argv
        test_args = ["alienrecon", "doctor"]

        with patch("sys.argv", test_args):
            with patch("alienrecon.cli.app") as mock_app:
                # Run the module
                import runpy

                try:
                    runpy.run_module("alienrecon", run_name="__main__")
                except SystemExit:
                    # Typer may exit, that's ok
                    pass

        # Verify app was invoked
        assert mock_app.called
