"""tests for refresh token rotation logic in app/utils/auth.py."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.user import RefreshToken
from app.utils.auth import (
    save_refresh_token,
    revoke_refresh_token,
    is_refresh_token_valid,
    revoke_all_user_tokens,
    create_refresh_token,
    verify_token,
)


class TestRefreshTokenRotationLogic:
    """tests that the token management functions support rotation correctly."""

    def test_revoke_refresh_token_marks_as_revoked(self):
        """revoking a token should set is_revoked to True."""
        mock_db = MagicMock(spec=Session)
        token_record = MagicMock(spec=RefreshToken)
        token_record.is_revoked = False
        mock_db.query.return_value.filter.return_value.first.return_value = token_record

        result = revoke_refresh_token(mock_db, "some-token")

        assert result is True
        assert token_record.is_revoked is True

    def test_revoke_refresh_token_returns_false_if_not_found(self):
        """revoking a nonexistent token should return False."""
        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = revoke_refresh_token(mock_db, "nonexistent-token")

        assert result is False

    def test_is_refresh_token_valid_rejects_revoked(self):
        """a revoked token should not be considered valid."""
        mock_db = MagicMock(spec=Session)
        # filter excludes revoked tokens, so no result
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = is_refresh_token_valid(mock_db, "revoked-token", "user-id")

        assert result is False

    def test_is_refresh_token_valid_accepts_active(self):
        """an active, non-expired token should be valid."""
        mock_db = MagicMock(spec=Session)
        active_record = MagicMock(spec=RefreshToken)
        mock_db.query.return_value.filter.return_value.first.return_value = active_record

        result = is_refresh_token_valid(mock_db, "active-token", "user-id")

        assert result is True

    def test_revoke_all_user_tokens_updates_all(self):
        """revoke_all_user_tokens should mark all active tokens as revoked."""
        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.update.return_value = 3

        result = revoke_all_user_tokens(mock_db, "user-id")

        assert result is True
        mock_db.query.return_value.filter.return_value.update.assert_called_once_with(
            {"is_revoked": True}
        )

    def test_save_refresh_token_adds_to_session(self):
        """save_refresh_token should add a new record to the db session."""
        mock_db = MagicMock(spec=Session)
        expires = datetime.utcnow() + timedelta(days=7)

        result = save_refresh_token(mock_db, "user-id", "new-token", expires)

        mock_db.add.assert_called_once()
        assert result.token == "new-token"
        assert result.user_id == "user-id"
        assert result.expires_at == expires

    def test_create_refresh_token_returns_valid_jwt(self):
        """create_refresh_token should return a jwt that can be verified."""
        token, expires = create_refresh_token({"sub": "user-123"})

        assert token is not None
        assert isinstance(token, str)
        assert expires > datetime.utcnow()

        # the token should be verifiable as a refresh token
        payload = verify_token(token, "refresh")
        assert payload is not None
        assert payload["sub"] == "user-123"
        assert payload["type"] == "refresh"

    def test_create_refresh_token_not_valid_as_access(self):
        """a refresh token should not pass verification as an access token."""
        token, _ = create_refresh_token({"sub": "user-123"})

        payload = verify_token(token, "access")
        assert payload is None


class TestTokenRotationFlow:
    """tests that simulate the full rotation flow."""

    def test_old_token_invalid_after_revocation(self):
        """after revoking a token, is_refresh_token_valid should reject it."""
        mock_db = MagicMock(spec=Session)

        # step 1: token is valid
        active_record = MagicMock(spec=RefreshToken)
        active_record.is_revoked = False
        mock_db.query.return_value.filter.return_value.first.return_value = active_record

        assert is_refresh_token_valid(mock_db, "token-a", "user-1") is True

        # step 2: revoke it
        revoke_refresh_token(mock_db, "token-a")
        assert active_record.is_revoked is True

        # step 3: after revocation, filter returns None (revoked tokens excluded)
        mock_db.query.return_value.filter.return_value.first.return_value = None
        assert is_refresh_token_valid(mock_db, "token-a", "user-1") is False

    def test_new_token_valid_after_save(self):
        """a newly saved token should be considered valid."""
        mock_db = MagicMock(spec=Session)
        expires = datetime.utcnow() + timedelta(days=7)

        # save new token
        new_record = save_refresh_token(mock_db, "user-1", "token-b", expires)
        mock_db.add.assert_called_once()

        # simulate it being found as valid
        mock_db.query.return_value.filter.return_value.first.return_value = new_record
        assert is_refresh_token_valid(mock_db, "token-b", "user-1") is True
