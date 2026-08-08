"""
Unit tests for dashboard authentication modes.

Tests the verify_session function in both pilot and strict modes.
"""

import os
import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException

from src.core.dashboard_api_simple import verify_session, get_current_user


@pytest.mark.asyncio
async def test_pilot_mode_allows_no_auth():
    """
    In pilot mode (DASHBOARD_MODE=pilot), requests without auth should succeed
    with a default tenant_id fallback.
    """
    # Pilot mode falls back to DEFAULT_TENANT_ID (env-driven, fail-secure if unset)
    with patch.dict(os.environ, {"DASHBOARD_MODE": "pilot", "REQUIRE_DASHBOARD_TOKEN": "false",
                                 "DEFAULT_TENANT_ID": "00000000-0000-0000-0000-000000000001"}):
        # No user, no tenant_id provided
        result = await verify_session(
            tenant_id=None,
            x_tenant_id=None,
            token=None,
            user=None
        )

        # Should return the configured default tenant (no exception raised)
        assert result == "00000000-0000-0000-0000-000000000001"


@pytest.mark.asyncio
async def test_strict_mode_requires_auth():
    """
    In strict mode (DASHBOARD_MODE=strict), requests without auth should fail.
    """
    with patch.dict(os.environ, {"DASHBOARD_MODE": "strict", "REQUIRE_DASHBOARD_TOKEN": "true"}):
        # No user, no tenant_id provided
        with pytest.raises(HTTPException) as exc_info:
            await verify_session(
                tenant_id=None,
                x_tenant_id=None,
                token=None,
                user=None
            )
        
        # Should raise 400 or 401 error
        assert exc_info.value.status_code in [400, 401]


@pytest.mark.asyncio
async def test_strict_mode_with_valid_session():
    """
    In strict mode, requests WITH valid Supabase session should succeed.
    """
    with patch.dict(os.environ, {"DASHBOARD_MODE": "strict", "REQUIRE_DASHBOARD_TOKEN": "true"}):
        # Mock user from Supabase auth. Tenant is resolved via the tenant_users
        # table (not user_metadata), so mock get_supabase's lookup chain.
        mock_user = Mock()
        mock_user.id = "user-123"
        mock_user.email = "test@example.com"

        with patch("src.core.dashboard_api_simple.get_supabase") as mock_get_supabase:
            mock_sb = Mock()
            mock_sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = Mock(
                data=[{"tenant_id": "test-tenant-123"}]
            )
            mock_get_supabase.return_value = mock_sb

            result = await verify_session(
                tenant_id=None,
                x_tenant_id=None,
                token=None,
                user=mock_user
            )

        assert result == "test-tenant-123"


@pytest.mark.asyncio
async def test_strict_mode_blocks_cross_tenant_access():
    """
    Security test: User from tenant A cannot access tenant B's data.
    """
    with patch.dict(os.environ, {"DASHBOARD_MODE": "strict"}):
        # Mock user authorized for tenant A (resolved via tenant_users lookup)
        mock_user = Mock()
        mock_user.id = "user-a"
        mock_user.email = "tenant-a@example.com"

        with patch("src.core.dashboard_api_simple.get_supabase") as mock_get_supabase:
            mock_sb = Mock()
            mock_sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = Mock(
                data=[{"tenant_id": "tenant-a-id"}]
            )
            mock_get_supabase.return_value = mock_sb

            # Try to access tenant B's data
            with pytest.raises(HTTPException) as exc_info:
                await verify_session(
                    tenant_id="tenant-b-id",  # Different tenant!
                    x_tenant_id=None,
                    token=None,
                    user=mock_user
                )

        # Should raise 403 Forbidden
        assert exc_info.value.status_code == 403
        assert "Unauthorized tenant access" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_x_tenant_id_header_preferred_over_query():
    """
    X-Tenant-ID header should take precedence over query parameter.
    """
    with patch.dict(os.environ, {"DASHBOARD_MODE": "pilot", "REQUIRE_DASHBOARD_TOKEN": "false"}):
        result = await verify_session(
            tenant_id="query-tenant-id",
            x_tenant_id="header-tenant-id",
            token=None,
            user=None
        )
        
        # Should use header value
        assert result == "header-tenant-id"


@pytest.mark.asyncio
async def test_require_dashboard_token_enabled():
    """
    When REQUIRE_DASHBOARD_TOKEN=true, requests without user should fail.
    """
    with patch.dict(os.environ, {"REQUIRE_DASHBOARD_TOKEN": "true"}):
        with pytest.raises(HTTPException) as exc_info:
            await verify_session(
                tenant_id="some-tenant",
                x_tenant_id=None,
                token=None,
                user=None  # No authenticated user
            )
        
        assert exc_info.value.status_code == 401
        assert "Authentication required" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_get_current_user_with_valid_token():
    """
    Test get_current_user extracts user from valid JWT token.
    """
    # Mock Supabase client
    mock_user = Mock()
    mock_user.email = "test@example.com"
    
    mock_response = Mock()
    mock_response.user = mock_user
    
    with patch('src.core.dashboard_api_simple.get_supabase') as mock_get_supabase:
        mock_supabase = Mock()
        mock_supabase.auth.get_user.return_value = mock_response
        mock_get_supabase.return_value = mock_supabase
        
        # Call with Bearer token
        result = await get_current_user(authorization="Bearer test-token-123")
        
        assert result == mock_user
        mock_supabase.auth.get_user.assert_called_once_with("test-token-123")


@pytest.mark.asyncio
async def test_get_current_user_with_no_token():
    """
    Test get_current_user returns None when no Authorization header provided.
    """
    result = await get_current_user(authorization=None)
    assert result is None


@pytest.mark.asyncio
async def test_get_current_user_with_invalid_token():
    """
    Test get_current_user returns None for invalid/expired tokens.
    """
    with patch('src.core.dashboard_api_simple.get_supabase') as mock_get_supabase:
        mock_supabase = Mock()
        mock_supabase.auth.get_user.side_effect = Exception("Invalid JWT")
        mock_get_supabase.return_value = mock_supabase
        
        result = await get_current_user(authorization="Bearer invalid-token")
        
        assert result is None
