from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_contact_accepts_valid_payload_and_stores_message():
    payload = {
        "name": "Ivan",
        "email": "ivan@example.com",
        "message": "Hello there!" * 1,
    }
    resp = client.post("/api/contact", json=payload)
    assert resp.status_code == 201
    assert resp.json() == {"status": "received"}

    # storage must contain exactly this message as last element
    # import inside test to avoid circulars
    from app.main import contact_messages

    assert contact_messages, "storage should not be empty"
    last = contact_messages[-1]
    assert last["name"] == payload["name"]
    assert last["email"] == payload["email"]
    assert last["message"] == payload["message"].strip()


def test_contact_honeypot_spam_returns_400_and_not_stored():
    payload = {
        "name": "Ivan",
        "email": "ivan@example.com",
        "message": "Hello there!",
        "website": "http://spam.example",
    }
    from app.main import contact_messages
    before = len(contact_messages)

    resp = client.post("/api/contact", json=payload)
    assert resp.status_code == 400
    assert resp.json() == {"detail": "spam"}
    assert len(contact_messages) == before


def test_contact_invalid_fields_return_422_and_not_stored():
    # name too short after strip and message too short
    payload = {
        "name": " ",
        "email": "invalid",
        "message": "short",
    }
    from app.main import contact_messages
    before = len(contact_messages)

    resp = client.post("/api/contact", json=payload)
    assert resp.status_code == 422
    assert len(contact_messages) == before


def test_contact_boundaries_valid_name_and_message_lengths():
    name_min = "a"
    name_max = "a" * 100
    msg_min = "m" * 10
    msg_max = "m" * 2000

    for name in (name_min, name_max):
        for message in (msg_min, msg_max):
            payload = {
                "name": name,
                "email": "x@y.z",
                "message": message,
            }
            resp = client.post("/api/contact", json=payload)
            assert resp.status_code == 201


def test_email_rules():
    # valid emails
    for email in [
        "a@b.c",
        "user.name+tag@domain.co.uk",
    ]:
        resp = client.post(
            "/api/contact",
            json={"name": "n", "email": email, "message": "m" * 10},
        )
        assert resp.status_code == 201

    # invalid: multiple '@', empty local or domain, no dot in domain
    invalids = [
        "a@@b.c",
        "@b.c",
        "a@",
        "a@bc",  # no dot in domain
    ]
    from app.main import contact_messages
    before = len(contact_messages)
    for email in invalids:
        resp = client.post(
            "/api/contact",
            json={"name": "n", "email": email, "message": "m" * 10},
        )
        assert resp.status_code == 422
    assert len(contact_messages) == before


def test_out_of_bounds_lengths_not_stored():
    from app.main import contact_messages
    before = len(contact_messages)

    # name length 101
    resp = client.post(
        "/api/contact",
        json={
            "name": "a" * 101,
            "email": "x@y.z",
            "message": "m" * 10,
        },
    )
    assert resp.status_code == 422

    # message length 9
    resp = client.post(
        "/api/contact",
        json={
            "name": "ok",
            "email": "x@y.z",
            "message": "m" * 9,
        },
    )
    assert resp.status_code == 422

    # message length 2001
    resp = client.post(
        "/api/contact",
        json={
            "name": "ok",
            "email": "x@y.z",
            "message": "m" * 2001,
        },
    )
    assert resp.status_code == 422

    # message of only spaces
    resp = client.post(
        "/api/contact",
        json={
            "name": "ok",
            "email": "x@y.z",
            "message": " " * 20,
        },
    )
    assert resp.status_code == 422

    # no invalid request stored
    assert len(contact_messages) == before
