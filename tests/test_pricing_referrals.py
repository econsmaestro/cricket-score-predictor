from types import SimpleNamespace

import pytest
from flask import render_template

from app import app


@pytest.mark.parametrize("authenticated,has_pro", [
    (False, False), (True, False), (True, True),
])
@pytest.mark.parametrize("stripe_configured", [False, True])
def test_pricing_offers_referral_pro_for_every_account_state(
    authenticated, has_pro, stripe_configured,
):
    with app.test_request_context("/pricing"):
        html = render_template(
            "pricing.html",
            current_user=SimpleNamespace(
                is_authenticated=authenticated, has_pro=has_pro,
            ),
            stripe_configured=stripe_configured,
        )

    assert 'href="/referrals"' in html
    assert "Earn Pro for free" in html
    assert "first successful prediction" in html
    assert "Singapore calendar month" in html
    assert "SGD 3.99" in html
    if has_pro:
        assert "Manage subscription" in html
    elif stripe_configured:
        assert "Start 7-day free trial" in html
    else:
        assert "Payments launching soon" in html
