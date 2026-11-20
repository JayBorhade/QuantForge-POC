"""Regression tests for encrypted TOTP seed storage."""

import unittest

from app.core.encryption import decrypt_mfa_secret, encrypt_mfa_secret


class TestMfaSecretEncryption(unittest.TestCase):
    def test_seed_is_encrypted_and_round_trips(self):
        seed = "JBSWY3DPEHPK3PXP"
        encrypted = encrypt_mfa_secret(seed)

        self.assertNotEqual(encrypted, seed)
        self.assertNotIn(seed, encrypted)
        self.assertTrue(encrypted.startswith("enc:v1:"))
        self.assertEqual(decrypt_mfa_secret(encrypted), seed)

    def test_legacy_plaintext_is_read_during_migration_compatibility(self):
        seed = "JBSWY3DPEHPK3PXP"
        self.assertEqual(decrypt_mfa_secret(seed), seed)


if __name__ == "__main__":
    unittest.main()
