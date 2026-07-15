from app.payments import YooKassaPayment, make_payload, parse_payload


def test_payload_roundtrip_for_known_product() -> None:
    payload = make_payload("details", 42)

    assert parse_payload(payload) == ("details", 42)


def test_yookassa_payment_exposes_metadata_contract() -> None:
    payment = YooKassaPayment(
        payment_id="pay_1",
        status="succeeded",
        paid=True,
        metadata={"product_key": "message", "report_id": "17", "telegram_user_id": "123"},
    )

    assert payment.product_key == "message"
    assert payment.report_id == 17
    assert payment.telegram_user_id == 123


def test_yookassa_payment_ignores_broken_numeric_metadata() -> None:
    payment = YooKassaPayment(
        payment_id="pay_2",
        status="pending",
        metadata={"report_id": "bad", "telegram_user_id": "bad"},
    )

    assert payment.report_id == 0
    assert payment.telegram_user_id == 0


def test_yookassa_user_error_explains_bad_return_url() -> None:
    from app.payments import _format_yookassa_user_error

    message = _format_yookassa_user_error(400, '{"description":"Invalid return_url","parameter":"confirmation.return_url"}')

    assert "WEBAPP_URL" in message
    assert "https" in message


def test_yookassa_payment_rejects_missing_confirmation_url(monkeypatch) -> None:
    import app.payments as payments
    from app.payments import YooKassaPaymentError, get_product

    product = get_product("planet_venus")
    assert product is not None

    def fake_request(*args, **kwargs):
        return {"id": "pay_1", "status": "pending", "confirmation": {}, "metadata": {}}

    monkeypatch.setattr(payments, "_yookassa_request", fake_request)

    try:
        payments.create_yookassa_payment(
            shop_id="shop",
            secret_key="secret",
            product=product,
            product_key="planet_venus",
            report_id=1,
            user_id=2,
            return_url="https://example.com/webapp",
        )
    except YooKassaPaymentError as exc:
        assert "не вернула рабочую ссылку" in exc.user_message
    else:
        raise AssertionError("missing confirmation_url should fail before showing a broken payment button")
