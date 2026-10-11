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
                cookie_domain="quantforge.example",
                cors_origins=["https://quantforge.example"],
                encryption_key="x" * 32,
            )

    def test_production_requires_encryption_key(self):
        with self.assertRaises(ValidationError):
            Settings(
                _env_file=None,
                app_env="production",
                debug=False,
                secret_key="Kf9!Rz2@Lm7#Qp4$Tx8%Va5&Ns3^Hj6P7",
                jwt_secret_key="Yx4^Bp8!Nv2@Cq7#Hd5$Rm9%Ks3&Lt6B8",
                database_url="postgresql+asyncpg://user:DbPass-84!Strong@db:5432/quantforge",
                cookie_secure=True,
                cookie_domain="quantforge.example",
                cookie_samesite="lax",
                cors_origins=["https://quantforge.example"],
                encryption_key="",
            )

    def test_production_accepts_explicit_secure_configuration(self):
        settings = Settings(
            _env_file=None,
            app_env="production",
            debug=False,
            secret_key="Kf9!Rz2@Lm7#Qp4$Tx8%Va5&Ns3^Hj6P7",
            jwt_secret_key="Yx4^Bp8!Nv2@Cq7#Hd5$Rm9%Ks3&Lt6B8",
            database_url="postgresql+asyncpg://user:DbPass-84!Strong@db:5432/quantforge",
            cookie_secure=True,
            cookie_domain="quantforge.example",
            cookie_samesite="lax",
            cors_origins=["https://quantforge.example"],
            encryption_key="e" * 48,
            csrf_enabled=True,
            smtp_user="smtp-user",
            smtp_password="smtp-password",
        )
        self.assertTrue(settings.is_production)
        self.assertTrue(settings.cookie_secure)

    def test_production_rejects_localhost_cookie_domain(self):
        with self.assertRaisesRegex(ValidationError, "COOKIE_DOMAIN"):
            Settings(
                _env_file=None,
                app_env="production",
                debug=False,
                secret_key="Kf9!Rz2@Lm7#Qp4$Tx8%Va5&Ns3^Hj6P7",
                jwt_secret_key="Yx4^Bp8!Nv2@Cq7#Hd5$Rm9%Ks3&Lt6B8",
                database_url="postgresql+asyncpg://user:DbPass-84!Strong@db:5432/quantforge",
                cookie_secure=True,
                cookie_domain="localhost",
                cors_origins=["https://quantforge.example"],
                encryption_key="e" * 48,
            )

    def test_non_local_environment_rejects_debug(self):
        with self.assertRaises(ValidationError):
            Settings(
                _env_file=None,
                app_env="staging",
                debug=True,
                secret_key="Kf9!Rz2@Lm7#Qp4$Tx8%Va5&Ns3^Hj6P7",
                jwt_secret_key="Yx4^Bp8!Nv2@Cq7#Hd5$Rm9%Ks3&Lt6B8",
                database_url="postgresql+asyncpg://user:DbPass-84!Strong@db:5432/quantforge",
                cookie_secure=True,
                cookie_domain="staging.quantforge.example",
                cors_origins=["https://staging.quantforge.example"],
                encryption_key="e" * 48,
            )

    def test_production_rejects_same_jwt_and_application_secret(self):
        with self.assertRaisesRegex(ValidationError, "must be different"):
            Settings(
                _env_file=None,
                app_env="production",
                debug=False,
                secret_key="Kf9!Rz2@Lm7#Qp4$Tx8%Va5&Ns3^Hj6P7",
                jwt_secret_key="Kf9!Rz2@Lm7#Qp4$Tx8%Va5&Ns3^Hj6P7",
                database_url="postgresql+asyncpg://user:DbPass-84!Strong@db:5432/quantforge",
                cookie_secure=True,
                cookie_domain="quantforge.example",
                cors_origins=["https://quantforge.example"],
                encryption_key="e" * 48,
            )

    def test_production_rejects_wildcard_cors(self):
        with self.assertRaisesRegex(ValidationError, "exact HTTPS origins"):
            Settings(
                _env_file=None,
                app_env="production",
                debug=False,
                secret_key="Kf9!Rz2@Lm7#Qp4$Tx8%Va5&Ns3^Hj6P7",
                jwt_secret_key="Yx4^Bp8!Nv2@Cq7#Hd5$Rm9%Ks3&Lt6B8",
                database_url="postgresql+asyncpg://user:DbPass-84!Strong@db:5432/quantforge",
                cookie_secure=True,
                cookie_domain="quantforge.example",
                cors_origins=["https://*.quantforge.example"],
                encryption_key="e" * 48,
            )

    def test_production_rejects_default_database_password(self):
        with self.assertRaisesRegex(ValidationError, "default or placeholder database password"):
            Settings(
                _env_file=None,
                app_env="production",
                debug=False,
                secret_key="Kf9!Rz2@Lm7#Qp4$Tx8%Va5&Ns3^Hj6P7",
                jwt_secret_key="Yx4^Bp8!Nv2@Cq7#Hd5$Rm9%Ks3&Lt6B8",
                database_url="postgresql+asyncpg://user:quantforge_secret@db:5432/quantforge",
                cookie_secure=True,
                cookie_domain="quantforge.example",
                cors_origins=["https://quantforge.example"],
                encryption_key="e" * 48,
            )

if __name__ == "__main__":
    unittest.main()
