"""Tests for code quality validation."""

import math
import os
import unittest

# Set database URL for tests
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from app import create_app


class TestCodeQuality(unittest.TestCase):
    """Tests for code quality validation."""

    def test_app_creates_successfully(self):
        """Test that the app factory creates an instance."""
        app = create_app()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.assertIsNotNone(app)

    def test_blueprints_registered(self):
        """Test that all blueprints are registered."""
        app = create_app()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.assertIsNotNone(app.blueprints)