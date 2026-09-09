"""Teste për Order Service: shëndeti, kontrolli i qasjes, krijimi i porosisë
dhe kontrata e event-it `order.created`.
"""

ORDER = {
    "customer_name": "Ardit Krasniqi",
    "customer_email": "ardit@example.com",
    "items": [{"product_id": 1, "quantity": 2, "unit_price": 500.0}],
}


def test_health_eshte_publik(client):
    """/health nuk kërkon API key sepse e thërret monitorimi."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "order-service"}


def test_krijimi_pa_api_key_kthen_401(client):
    response = client.post("/orders", json=ORDER)
    assert response.status_code in (401, 422)


def test_krijimi_me_api_key_te_gabuar_kthen_401(client):
    response = client.post("/orders", json=ORDER, headers={"X-API-Key": "gabim"})
    assert response.status_code == 401


def test_krijimi_i_porosise_kthen_201_dhe_artikujt(client, auth):
    response = client.post("/orders", json=ORDER, headers=auth)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert len(body["items"]) == 1
    assert body["items"][0]["quantity"] == 2


def test_publikohet_eventi_order_created(client, auth, published):
    client.post("/orders", json=ORDER, headers=auth)
    assert len(published) == 1
    routing_key, payload = published[0]
    assert routing_key == "order.created"
    assert payload["customer_email"] == ORDER["customer_email"]
    assert payload["items"] == [{"product_id": 1, "quantity": 2}]


def test_klienti_nuk_dublikohet_per_email_te_njejte(client, auth):
    first = client.post("/orders", json=ORDER, headers=auth).json()
    second = client.post("/orders", json=ORDER, headers=auth).json()
    assert first["id"] != second["id"]
    assert len(client.get("/orders", headers=auth).json()) == 2


def test_email_i_pavlefshem_kthen_422(client, auth):
    payload = dict(ORDER, customer_email="nuk-eshte-email")
    assert client.post("/orders", json=payload, headers=auth).status_code == 422


def test_porosia_e_paqene_kthen_404(client, auth):
    assert client.get("/orders/999", headers=auth).status_code == 404
