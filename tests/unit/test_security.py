from app.core.security import verify_password, get_password_hash

def test_verify_password():
    password = "testpassword"
    hashed_password = get_password_hash(password)
    assert verify_password(password, hashed_password)
    assert not verify_password("wrongpassword", hashed_password)

def test_password_hashing_consistency():
    password = "secure_password!123"
    hash1 = get_password_hash(password)
    hash2 = get_password_hash(password)
    # Bcrypt produces different hashes for the same password, but verify should work
    assert hash1 != hash2 # This is expected for bcrypt
    assert verify_password(password, hash1)
    assert verify_password(password, hash2)
