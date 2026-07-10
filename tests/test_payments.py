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
