"""Password hashing regression tests, including bcrypt legacy compatibility."""
import unittest
import bcrypt

from app.core.security import hash_password, needs_password_rehash, verify_password

class PasswordHashingTests(unittest.TestCase):
    def test_new_hash_rejects_passwords_over_bcrypt_limit(self):
        with self.assertRaises(ValueError):
            hash_password("A" * 73)
        hashed = hash_password("A" * 72)
        self.assertTrue(verify_password("A" * 72, hashed))
        self.assertFalse(needs_password_rehash(hashed))

    def test_legacy_bcrypt_hash_remains_valid_and_is_marked_for_upgrade(self):
        password = "LegacyPassword123"
        legacy = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        self.assertTrue(verify_password(password, legacy))
        self.assertTrue(needs_password_rehash(legacy))

    def test_malformed_hash_fails_closed(self):
        self.assertFalse(verify_password("anything", "not-a-bcrypt-hash"))

if __name__ == "__main__":
    unittest.main()
