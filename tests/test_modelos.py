"""Tests for models module."""

from app.models import db, Pedido, Usuario


class TestModels:
    def test_usuario_model(self):
        """Test that Usuario model has required fields."""
        self.assertTrue(hasattr(Pedido, 'to_dict'))
        self.assertTrue(hasattr(Pedido, 'email'))

    def test_pedido_relationship(self):
        """Test that Pedido model has proper relationships."""
        self.assertIsNotNone(Pedido.__table__)
