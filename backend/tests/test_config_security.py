"""Configuration security regression tests."""
import unittest

from pydantic import ValidationError

from app.core.config import Settings


class SettingsSecurityTests(unittest.TestCase):
    def test_local_defaults_are_allowed_for_development(self):
        settings = Settings(_env_file=None)
        self.assertEqual(settings.app_env, "development")
        self.assertFalse(settings.cookie_secure)

    def test_production_rejects_default_secrets_and_database(self):
        with self.assertRaises(ValidationError):
            Settings(
                _env_file=None,
                app_env="production",
                debug=False,
                cookie_secure=True,
                cors_origins=["https://quantforge.example"],
                encryption_key="x" * 32,
            )

    def test_production_requires_encryption_key(self):
        with self.assertRaises(ValidationError):
            Settings(
                _env_file=None,
                app_env="production",
                debug=False,
                secret_key="s" * 48,
                jwt_secret_key="j" * 48,
                database_url="postgresql+asyncpg://user:password@db:5432/quantforge",
                cookie_secure=True,
                cookie_samesite="lax",
                cors_origins=["https://quantforge.example"],
                encryption_key="",
            )

    def test_production_accepts_explicit_secure_configuration(self):
        settings = Settings(
            _env_file=None,
            app_env="production",
            debug=False,
            secret_key="s" * 48,
            jwt_secret_key="j" * 48,
            database_url="postgresql+asyncpg://user:password@db:5432/quantforge",
            cookie_secure=True,
            cookie_samesite="lax",
            cors_origins=["https://quantforge.example"],
            encryption_key="e" * 48,
            csrf_enabled=True,
        )
        self.assertTrue(settings.is_production)
        self.assertTrue(settings.cookie_secure)

    def test_non_local_environment_rejects_debug(self):
        with self.assertRaises(ValidationError):
            Settings(
                _env_file=None,
                app_env="staging",
                debug=True,
                secret_key="s" * 48,
                jwt_secret_key="j" * 48,
                database_url="postgresql+asyncpg://user:password@db:5432/quantforge",
                cookie_secure=True,
                cors_origins=["https://staging.quantforge.example"],
                encryption_key="e" * 48,
            )


if __name__ == "__main__":
    unittest.main()
