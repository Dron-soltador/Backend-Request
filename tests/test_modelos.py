"""Tests for models module."""

import math
import unittest

from app.models import db, Pedido, Usuario


class TestModels(unittest.TestCase):
    def test_usuario_model(self):
        """Test that Usuario model has required fields."""
        self.assertTrue(hasattr(Usuario, 'email'))

    def test_pedido_relationship(self):
        """Test that Pedido model has proper relationships."""
        self.assertIsNotNone(Pedido.__table__)
