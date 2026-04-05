from backend.permissions.model import PermissionLevel, UserPermissions


def test_permissions_default_to_full_manual():
    permissions = UserPermissions()
    assert permissions.level is PermissionLevel.FULL_MANUAL
    assert permissions.live_trading_acknowledged_risks is False


def test_permissions_from_dict_ignores_legacy_unlock_fields():
    permissions = UserPermissions.from_dict(
        {
            "level": "semi_auto",
            "live_trading_acknowledged_risks": True,
            "live_trading_unlocked": False,
            "live_trading_unlock_timestamp": "2026-01-01T00:00:00Z",
            "paper_trading_minimum_days": 14,
        }
    )
    assert permissions.level is PermissionLevel.SEMI_AUTO
    assert permissions.live_trading_acknowledged_risks is True
