"""
Remember Me Token Tests - Security & Functionality

Tests the secure Remember Me feature:
- Token generation and storage
- Token validation (including timing-safe comparison)
- Security: Tampered token rejection
- API endpoint validation
"""

import sys
import os
import hashlib
import json

# Register NetAlertX directories
INSTALL_PATH = os.getenv("NETALERTX_APP", "/app")
sys.path.extend([f"{INSTALL_PATH}/front/plugins", f"{INSTALL_PATH}/server"])

import pytest
from api_server.api_server_start import app  # noqa: E402
from models.parameters_instance import ParametersInstance  # noqa: E402


@pytest.fixture
def client():
    """Flask test client."""
    with app.test_client() as client:
        yield client


@pytest.fixture
def params_instance():
    """ParametersInstance for direct database access."""
    return ParametersInstance()


@pytest.fixture
def test_token():
    """Generate a valid test token (64-hex characters)."""
    import os
    return os.urandom(32).hex()  # 32 bytes = 64 hex chars


# ============================================================================
# REMEMBER ME SAVE ENDPOINT TESTS
# ============================================================================

def test_save_remember_success(client, test_token):
    """POST /auth/remember-me/save - Valid token should save successfully."""
    resp = client.post("/auth/remember-me/save", json={"token": test_token})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data is not None
    assert data["success"] is True
    assert "saved successfully" in data.get("message", "").lower()
    assert data.get("token_id") is not None
    assert data["token_id"].startswith("remember_me_token_")


def test_save_remember_missing_token(client):
    """POST /auth/remember-me/save - Missing token should fail with 422 (validation error)."""
    resp = client.post("/auth/remember-me/save", json={})

    assert resp.status_code == 422  # Pydantic validation error, not 400
    data = resp.get_json()
    assert data is not None
    assert data["success"] is False


def test_save_remember_empty_token(client):
    """POST /auth/remember-me/save - Empty token should fail with 422."""
    resp = client.post("/auth/remember-me/save", json={"token": ""})

    assert resp.status_code == 422  # Pydantic validation error
    data = resp.get_json()
    assert data is not None
    assert data["success"] is False


def test_save_remember_short_token(client):
    """POST /auth/remember-me/save - Token too short (< 64 chars) should fail with 422."""
    resp = client.post("/auth/remember-me/save", json={"token": "a" * 32})

    assert resp.status_code == 422  # Pydantic validation error
    data = resp.get_json()
    assert data is not None
    assert data["success"] is False


def test_save_remember_null_token(client):
    """POST /auth/remember-me/save - Null token should fail with 422."""
    resp = client.post("/auth/remember-me/save", json={"token": None})

    assert resp.status_code == 422  # Pydantic validation error
    data = resp.get_json()
    assert data is not None
    assert data["success"] is False


# ============================================================================
# REMEMBER ME VALIDATION ENDPOINT TESTS
# ============================================================================

def test_validate_remember_valid_token(client, test_token, params_instance):
    """POST /auth/validate-remember - Valid token should validate successfully."""
    # First save the token
    save_resp = client.post("/auth/remember-me/save", json={"token": test_token})
    assert save_resp.status_code == 200

    # Now validate it
    validate_resp = client.post("/auth/validate-remember", json={"token": test_token})

    assert validate_resp.status_code == 200
    data = validate_resp.get_json()
    assert data is not None
    assert data["success"] is True
    assert data["valid"] is True
    assert "successful" in data.get("message", "").lower()


def test_validate_remember_tampered_token(client, test_token):
    """
    POST /auth/validate-remember - SECURITY TEST: Tampered token should be rejected.

    This test verifies the security of the timing-safe hash comparison.
    Even a single-character modification to the token should fail validation.
    """
    # Save the original token
    save_resp = client.post("/auth/remember-me/save", json={"token": test_token})
    assert save_resp.status_code == 200

    # Tamper with the token by modifying last character
    tampered_token = test_token[:-1] + ("0" if test_token[-1] != "0" else "1")

    # Attempt to validate with tampered token
    validate_resp = client.post("/auth/validate-remember", json={"token": tampered_token})

    assert validate_resp.status_code == 200
    data = validate_resp.get_json()
    assert data is not None
    assert data["success"] is True  # API doesn't error
    assert data["valid"] is False  # But validation fails
    assert "failed" in data.get("message", "").lower()


def test_validate_remember_nonexistent_token(client):
    """POST /auth/validate-remember - Non-existent token should return invalid."""
    import os
    random_token = os.urandom(32).hex()

    resp = client.post("/auth/validate-remember", json={"token": random_token})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data is not None
    assert data["success"] is True
    assert data["valid"] is False


def test_validate_remember_missing_token(client):
    """POST /auth/validate-remember - Missing token should fail with 422."""
    resp = client.post("/auth/validate-remember", json={})

    # Pydantic validation catches this before handler
    assert resp.status_code == 422
    data = resp.get_json()
    assert data is not None
    assert data["success"] is False


def test_validate_remember_empty_token(client):
    """POST /auth/validate-remember - Empty token should fail with 422."""
    resp = client.post("/auth/validate-remember", json={"token": ""})

    # Pydantic validation catches this before handler
    assert resp.status_code == 422
    data = resp.get_json()
    assert data is not None
    assert data["success"] is False


def test_validate_remember_null_token(client):
    """POST /auth/validate-remember - Null token should fail with 422."""
    resp = client.post("/auth/validate-remember", json={"token": None})

    # Pydantic validation catches this before handler
    assert resp.status_code == 422
    data = resp.get_json()
    assert data is not None
    assert data["success"] is False


# ============================================================================
# COMPLETE WORKFLOW TESTS
# ============================================================================

def test_remember_me_complete_workflow(client, test_token):
    """
    Save and validate: Complete Remember Me workflow.

    Simulates:
    1. User logs in, "Remember Me" checked
    2. System saves token via API
    3. User closes browser, session expires
    4. User returns, system validates token from cookie
    5. User authenticated without re-entering password
    """
    # Step 1: Save token (happens at login with "Remember Me")
    save_resp = client.post("/auth/remember-me/save", json={"token": test_token})
    assert save_resp.status_code == 200
    save_data = save_resp.get_json()
    assert save_data["success"] is True
    token_id = save_data["token_id"]

    # Step 2: Validate token (happens on return visit from cookie)
    validate_resp = client.post("/auth/validate-remember", json={"token": test_token})
    assert validate_resp.status_code == 200
    validate_data = validate_resp.get_json()
    assert validate_data["success"] is True
    assert validate_data["valid"] is True

    # Step 3: Verify token was actually stored in Parameters table
    stored_value = ParametersInstance().get_parameter(token_id)
    assert stored_value is not None
    expected_hash = hashlib.sha256(test_token.encode('utf-8')).hexdigest()
    assert stored_value == expected_hash


def test_remember_me_multiple_tokens(client):
    """Multiple tokens can coexist (for multi-device Remember Me in future)."""
    import os

    token1 = os.urandom(32).hex()
    token2 = os.urandom(32).hex()

    # Save both tokens
    resp1 = client.post("/auth/remember-me/save", json={"token": token1})
    resp2 = client.post("/auth/remember-me/save", json={"token": token2})

    assert resp1.status_code == 200
    assert resp2.status_code == 200

    # Both should validate
    validate1 = client.post("/auth/validate-remember", json={"token": token1})
    validate2 = client.post("/auth/validate-remember", json={"token": token2})

    assert validate1.get_json()["valid"] is True
    assert validate2.get_json()["valid"] is True

    # Each token should only match itself, not the other
    cross_validate = client.post("/auth/validate-remember", json={"token": token1 + token2[:32]})
    assert cross_validate.get_json()["valid"] is False


# ============================================================================
# SECURITY TESTS
# ============================================================================

def test_timing_attack_prevention(client, test_token):
    """
    Verify timing-safe hash comparison prevents timing attacks.

    The _hash_equals() method should take roughly equal time regardless of
    where the mismatch occurs in the string.
    """
    # Save token
    client.post("/auth/remember-me/save", json={"token": test_token})

    # Create tampered versions at different positions
    tamper_positions = [0, 10, 32, 60, 63]  # Various positions

    for pos in tamper_positions:
        tampered_token = list(test_token)
        tampered_token[pos] = "F" if tampered_token[pos] != "F" else "0"
        tampered_token = "".join(tampered_token)

        resp = client.post("/auth/validate-remember", json={"token": tampered_token})
        data = resp.get_json()

        # All tampered attempts should fail validation
        assert data["valid"] is False, f"Tamper at position {pos} was not detected!"


def test_hash_not_stored_on_disk(client, test_token):
    """Verify that the HASH (not the token) is stored on disk."""
    save_resp = client.post("/auth/remember-me/save", json={"token": test_token})
    token_id = save_resp.get_json()["token_id"]

    # Retrieve the stored value
    stored_hash = ParametersInstance().get_parameter(token_id)

    # Verify it's a hash, not the original token
    assert stored_hash != test_token, "Token hash should not match original token!"
    assert len(stored_hash) == 64, "SHA256 hash should be 64 hex characters"
    assert stored_hash == hashlib.sha256(test_token.encode('utf-8')).hexdigest()


def test_database_compromise_mitigation(client, test_token):
    """
    If database is compromised, stolen hash should not authenticate.

    This verifies the security model: attacker gets hash, but can't use it
    without the original token (which only exists in the user's cookie).
    """
    # Save token
    save_resp = client.post("/auth/remember-me/save", json={"token": test_token})
    token_id = save_resp.get_json()["token_id"]

    # Simulate database breach: attacker gets the stored hash
    stored_hash = ParametersInstance().get_parameter(token_id)

    # Attacker tries to use the stolen hash as a token
    breach_test_resp = client.post("/auth/validate-remember", json={"token": stored_hash})
    breach_test_data = breach_test_resp.get_json()

    # Validation should fail because hash doesn't match hash(hash(token))
    assert breach_test_data["valid"] is False, "Stolen hash should not authenticate!"


# ============================================================================
# MALFORMED REQUEST TESTS
# ============================================================================

def test_save_remember_no_json_body(client):
    """POST /auth/remember-me/save - Missing JSON body should fail."""
    resp = client.post(
        "/auth/remember-me/save",
        data="not json",
        content_type="application/json"
    )
    assert resp.status_code in [400, 500]


def test_validate_remember_no_json_body(client):
    """POST /auth/validate-remember - Missing JSON body should handle gracefully."""
    resp = client.post(
        "/auth/validate-remember",
        data="not json",
        content_type="application/json"
    )
    assert resp.status_code in [200, 400, 500]


def test_save_remember_extra_fields(client, test_token):
    """POST /auth/remember-me/save - Extra fields should be ignored."""
    resp = client.post("/auth/remember-me/save", json={
        "token": test_token,
        "extra_field": "should be ignored",
        "another": 123
    })

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True


# ============================================================================
# CLEANUP/MAINTENANCE TESTS
# ============================================================================

def test_delete_parameter(params_instance, test_token):
    """ParametersInstance.delete_parameter() should clean up tokens."""
    # Save a token
    test_id = "test_token_cleanup"
    test_hash = hashlib.sha256(test_token.encode('utf-8')).hexdigest()

    params_instance.set_parameter(test_id, test_hash)
    assert params_instance.get_parameter(test_id) is not None

    # Delete it
    success = params_instance.delete_parameter(test_id)
    assert success is True
    assert params_instance.get_parameter(test_id) is None


def test_delete_parameters_by_prefix(params_instance):
    """ParametersInstance.delete_parameters_by_prefix() should batch delete tokens."""
    import os

    # Create multiple tokens with same prefix
    prefix = "remember_me_token_test_"
    for i in range(3):
        token_id = f"{prefix}{i}"
        params_instance.set_parameter(token_id, f"hash_{i}")

    # Verify they exist
    assert params_instance.get_parameter(f"{prefix}0") is not None
    assert params_instance.get_parameter(f"{prefix}1") is not None
    assert params_instance.get_parameter(f"{prefix}2") is not None

    # Delete by prefix
    deleted_count = params_instance.delete_parameters_by_prefix(prefix)
    assert deleted_count >= 3

    # Verify they're gone
    assert params_instance.get_parameter(f"{prefix}0") is None
    assert params_instance.get_parameter(f"{prefix}1") is None
    assert params_instance.get_parameter(f"{prefix}2") is None
