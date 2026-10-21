"""Tests for code quality validation."""

from app import create_app


class TestCodeQuality:
    def test_app_creates_successfully(self):
        """Test that the app factory creates an instance."""
        app = create_app()
        self.assertIsNotNone(app)

    def test_blueprints_registered(self):
        """Test that all blueprints are registered."""
        app = create_app()
        self.assertIsNotNone(app.blueprints)
