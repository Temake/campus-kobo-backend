from datetime import date, timedelta
from decimal import Decimal

import pytest


async def _register_and_verify_user(
    client,
    *,
    email: str,
    password: str = "StrongPass123",
    full_name: str = "Finance User",
) -> dict:
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": full_name,
        },
    )
    assert register_response.status_code == 201
    register_body = register_response.json()

    verify_response = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": email, "code": register_body["verification_code"]},
    )
    assert verify_response.status_code == 204

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    return login_response.json()


async def _create_budget(client, headers: dict[str, str], **overrides) -> dict:
    payload = {
        "name": "April Budget",
        "amount": "1000.00",
        "currency": "NGN",
        "period_start": str(date(2026, 4, 1)),
        "period_end": str(date(2026, 4, 30)),
    }
    payload.update(overrides)
    response = await client.post("/api/v1/budgets", json=payload, headers=headers)
    assert response.status_code == 201
    return response.json()


async def _create_income(client, headers: dict[str, str], **overrides) -> dict:
    payload = {
        "amount": "60000.00",
        "category": "salary",
        "date": str(date(2026, 4, 4)),
        "note": "April salary",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/income", json=payload, headers=headers)
    assert response.status_code == 201
    return response.json()


async def _create_expense(client, headers: dict[str, str], **overrides) -> dict:
    payload = {
        "amount": "200.00",
        "category": "Food",
        "date": str(date(2026, 4, 4)),
        "note": "Lunch",
        "is_recurring": False,
    }
    payload.update(overrides)
    response = await client.post("/api/v1/expenses", json=payload, headers=headers)
    assert response.status_code == 201
    return response.json()


async def _create_savings_goal(client, headers: dict[str, str], **overrides) -> dict:
    payload = {
        "goal_name": "Emergency Fund",
        "target_amount": "100000.00",
        "target_date": str(date(2026, 12, 31)),
        "initial_deposit": "25000.00",
        "note": "Rainy day savings",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/savings", json=payload, headers=headers)
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_income_crud_and_dashboard_balance(client):
    auth = await _register_and_verify_user(client, email="income@example.com")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}

    created_income = await _create_income(client, headers)

    assert created_income["category"] == "salary"
    assert created_income["title"] == "salary"
    assert created_income["amount"] == "60000.00"
    assert created_income["note"] == "April salary"

    list_response = await client.get("/api/v1/income", headers=headers)
    assert list_response.status_code == 200
    incomes = list_response.json()
    assert len(incomes) == 1
    assert incomes[0]["id"] == created_income["id"]

    detail_response = await client.get(f"/api/v1/income/{created_income['id']}", headers=headers)
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == created_income["id"]

    update_response = await client.put(
        f"/api/v1/income/{created_income['id']}",
        json={
            "amount": "65000.00",
            "category": "freelance",
            "date": str(date(2026, 4, 5)),
            "note": "Website project",
        },
        headers=headers,
    )
    assert update_response.status_code == 200
    updated_income = update_response.json()
    assert updated_income["amount"] == "65000.00"
    assert updated_income["category"] == "freelance"
    assert updated_income["note"] == "Website project"

    dashboard_response = await client.get("/api/v1/dashboard", headers=headers)
    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.json()
    assert dashboard["current_balance"] == "65000.00"
    assert dashboard["summary"]["total_income"] == "65000.00"
    assert dashboard["summary"]["total_expenses"] == "0"
    assert dashboard["recent_transactions"][0]["type"] == "income"
    assert dashboard["recent_transactions"][0]["title"] == "freelance"

    delete_response = await client.delete(f"/api/v1/income/{created_income['id']}", headers=headers)
    assert delete_response.status_code == 204

    missing_response = await client.get(f"/api/v1/income/{created_income['id']}", headers=headers)
    assert missing_response.status_code == 404


@pytest.mark.asyncio
async def test_income_auth_validation_and_ownership(client):
    auth = await _register_and_verify_user(client, email="income-owner@example.com")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    other_auth = await _register_and_verify_user(client, email="other-income@example.com")
    other_headers = {"Authorization": f"Bearer {other_auth['access_token']}"}

    unauthorized_response = await client.get("/api/v1/income")
    assert unauthorized_response.status_code == 401

    invalid_response = await client.post(
        "/api/v1/income",
        json={
            "amount": "-10.00",
            "category": "salary",
            "date": str(date(2026, 4, 4)),
        },
        headers=headers,
    )
    assert invalid_response.status_code == 422

    created_income = await _create_income(client, headers)

    foreign_detail_response = await client.get(f"/api/v1/income/{created_income['id']}", headers=other_headers)
    assert foreign_detail_response.status_code == 404

    foreign_update_response = await client.put(
        f"/api/v1/income/{created_income['id']}",
        json={
            "amount": "10.00",
            "category": "gift",
            "date": str(date(2026, 4, 4)),
            "note": "Nope",
        },
        headers=other_headers,
    )
    assert foreign_update_response.status_code == 404

    foreign_delete_response = await client.delete(f"/api/v1/income/{created_income['id']}", headers=other_headers)
    assert foreign_delete_response.status_code == 404


@pytest.mark.asyncio
async def test_expense_crud_recurring_and_percentage_insights(client):
    auth = await _register_and_verify_user(client, email="expense@example.com")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}

    budget = await _create_budget(client, headers, amount="1000.00")
    assert budget["percentage_used"] == 0.0

    first_expense = await _create_expense(
        client,
        headers,
        amount="200.00",
        category="Food",
        date=str(date(2026, 4, 4)),
        note="Lunch",
    )
    second_expense = await _create_expense(
        client,
        headers,
        amount="300.00",
        category="Transport",
        date=str(date(2026, 4, 5)),
        note="Bus pass",
        is_recurring=True,
        repeats="monthly",
        next_due_date=str(date(2026, 5, 5)),
    )

    assert first_expense["percentage_of_total_expenses"] == 100.0
    assert first_expense["percentage_of_budget"] == 20.0
    assert second_expense["is_recurring"] is True
    assert second_expense["repeats"] == "monthly"
    assert second_expense["next_due_date"] == "2026-05-05"
    assert second_expense["percentage_of_total_expenses"] == 60.0
    assert second_expense["percentage_of_budget"] == 30.0

    list_response = await client.get("/api/v1/expenses", headers=headers)
    assert list_response.status_code == 200
    expenses = list_response.json()
    assert [expense["id"] for expense in expenses] == [second_expense["id"], first_expense["id"]]

    first_row = next(expense for expense in expenses if expense["id"] == first_expense["id"])
    second_row = next(expense for expense in expenses if expense["id"] == second_expense["id"])
    assert first_row["percentage_of_total_expenses"] == 40.0
    assert second_row["percentage_of_total_expenses"] == 60.0

    detail_response = await client.get(f"/api/v1/expenses/{second_expense['id']}", headers=headers)
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == second_expense["id"]

    update_response = await client.put(
        f"/api/v1/expenses/{second_expense['id']}",
        json={
            "amount": "250.00",
            "category": "Transport",
            "date": str(date(2026, 4, 6)),
            "note": "Updated bus pass",
            "is_recurring": True,
            "repeats": "weekly",
            "next_due_date": str(date(2026, 4, 13)),
        },
        headers=headers,
    )
    assert update_response.status_code == 200
    updated_expense = update_response.json()
    assert updated_expense["amount"] == "250.00"
    assert updated_expense["repeats"] == "weekly"
    assert updated_expense["next_due_date"] == "2026-04-13"
    assert updated_expense["percentage_of_budget"] == 25.0

    delete_response = await client.delete(f"/api/v1/expenses/{first_expense['id']}", headers=headers)
    assert delete_response.status_code == 204

    missing_response = await client.get(f"/api/v1/expenses/{first_expense['id']}", headers=headers)
    assert missing_response.status_code == 404


@pytest.mark.asyncio
async def test_expense_auth_validation_and_ownership(client):
    auth = await _register_and_verify_user(client, email="expense-owner@example.com")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    other_auth = await _register_and_verify_user(client, email="other-expense@example.com")
    other_headers = {"Authorization": f"Bearer {other_auth['access_token']}"}

    unauthorized_response = await client.get("/api/v1/expenses")
    assert unauthorized_response.status_code == 401

    invalid_amount_response = await client.post(
        "/api/v1/expenses",
        json={
            "amount": "0.00",
            "category": "Food",
            "date": str(date(2026, 4, 4)),
        },
        headers=headers,
    )
    assert invalid_amount_response.status_code == 422

    invalid_recurring_response = await client.post(
        "/api/v1/expenses",
        json={
            "amount": "100.00",
            "category": "Food",
            "date": str(date(2026, 4, 4)),
            "is_recurring": True,
        },
        headers=headers,
    )
    assert invalid_recurring_response.status_code == 422

    created_expense = await _create_expense(client, headers)

    foreign_detail_response = await client.get(f"/api/v1/expenses/{created_expense['id']}", headers=other_headers)
    assert foreign_detail_response.status_code == 404

    foreign_update_response = await client.put(
        f"/api/v1/expenses/{created_expense['id']}",
        json={
            "amount": "500.00",
            "category": "Travel",
            "date": str(date(2026, 4, 4)),
            "note": "Nope",
            "is_recurring": False,
        },
        headers=other_headers,
    )
    assert foreign_update_response.status_code == 404

    foreign_delete_response = await client.delete(f"/api/v1/expenses/{created_expense['id']}", headers=other_headers)
    assert foreign_delete_response.status_code == 404


@pytest.mark.asyncio
async def test_budget_crud_usage_days_left_highest_spent_and_transactions(client):
    auth = await _register_and_verify_user(client, email="budget@example.com")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}

    created_budget = await _create_budget(
        client,
        headers,
        name="Main Budget",
        amount="1000.00",
        period_start=str(date.today().replace(day=1)),
        period_end=str(date.today() + timedelta(days=10)),
    )
    assert created_budget["total_budget"] == "1000.00"
    assert created_budget["total_spent"] == "0"
    assert created_budget["remaining_amount"] == "1000.00"
    assert created_budget["percentage_used"] == 0.0
    assert created_budget["highest_spent"] is None

    await _create_expense(client, headers, amount="200.00", category="Food", date=str(date.today()), note="Lunch")
    await _create_expense(client, headers, amount="350.00", category="Transport", date=str(date.today()), note="Trip")

    detail_response = await client.get(f"/api/v1/budgets/{created_budget['id']}", headers=headers)
    assert detail_response.status_code == 200
    budget_detail = detail_response.json()
    assert budget_detail["total_spent"] == "550.00"
    assert budget_detail["remaining_amount"] == "450.00"
    assert budget_detail["percentage_used"] == 55.0
    assert budget_detail["highest_spent"] == "Transport"
    assert budget_detail["days_left"] >= 0
    assert len(budget_detail["recent_transactions"]) == 2

    list_response = await client.get("/api/v1/budgets", headers=headers)
    assert list_response.status_code == 200
    budgets = list_response.json()
    assert budgets[0]["id"] == created_budget["id"]
    assert budgets[0]["percentage_used"] == 55.0

    update_response = await client.put(
        f"/api/v1/budgets/{created_budget['id']}",
        json={
            "name": "Updated Budget",
            "amount": "1200.00",
            "currency": "NGN",
            "period_start": str(date.today().replace(day=1)),
            "period_end": str(date.today() + timedelta(days=15)),
        },
        headers=headers,
    )
    assert update_response.status_code == 200
    updated_budget = update_response.json()
    assert updated_budget["name"] == "Updated Budget"
    assert updated_budget["total_budget"] == "1200.00"
    assert updated_budget["percentage_used"] == float(round((Decimal("550.00") / Decimal("1200.00")) * 100, 2))

    delete_response = await client.delete(f"/api/v1/budgets/{created_budget['id']}", headers=headers)
    assert delete_response.status_code == 204

    missing_response = await client.get(f"/api/v1/budgets/{created_budget['id']}", headers=headers)
    assert missing_response.status_code == 404


@pytest.mark.asyncio
async def test_budget_auth_validation_and_ownership(client):
    auth = await _register_and_verify_user(client, email="budget-owner@example.com")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    other_auth = await _register_and_verify_user(client, email="other-budget@example.com")
    other_headers = {"Authorization": f"Bearer {other_auth['access_token']}"}

    unauthorized_response = await client.get("/api/v1/budgets")
    assert unauthorized_response.status_code == 401

    invalid_response = await client.post(
        "/api/v1/budgets",
        json={
            "name": "Broken Budget",
            "amount": "1000.00",
            "currency": "NGN",
            "period_start": "2026-04-30",
            "period_end": "2026-04-01",
        },
        headers=headers,
    )
    assert invalid_response.status_code == 422

    created_budget = await _create_budget(client, headers)

    foreign_detail_response = await client.get(f"/api/v1/budgets/{created_budget['id']}", headers=other_headers)
    assert foreign_detail_response.status_code == 404

    foreign_update_response = await client.put(
        f"/api/v1/budgets/{created_budget['id']}",
        json={
            "name": "Nope",
            "amount": "500.00",
            "currency": "NGN",
            "period_start": "2026-04-01",
            "period_end": "2026-04-30",
        },
        headers=other_headers,
    )
    assert foreign_update_response.status_code == 404

    foreign_delete_response = await client.delete(f"/api/v1/budgets/{created_budget['id']}", headers=other_headers)
    assert foreign_delete_response.status_code == 404


@pytest.mark.asyncio
async def test_savings_crud_progress_and_dashboard_section(client):
    auth = await _register_and_verify_user(client, email="savings@example.com")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}

    created_goal = await _create_savings_goal(client, headers)
    assert created_goal["goal_name"] == "Emergency Fund"
    assert created_goal["target_amount"] == "100000.00"
    assert created_goal["current_amount"] == "25000.00"
    assert created_goal["percentage_progress"] == 25.0

    list_response = await client.get("/api/v1/savings", headers=headers)
    assert list_response.status_code == 200
    goals = list_response.json()
    assert len(goals) == 1
    assert goals[0]["id"] == created_goal["id"]

    detail_response = await client.get(f"/api/v1/savings/{created_goal['id']}", headers=headers)
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == created_goal["id"]

    update_response = await client.put(
        f"/api/v1/savings/{created_goal['id']}",
        json={
            "goal_name": "Emergency Fund+",
            "target_amount": "120000.00",
            "target_date": "2027-01-31",
            "initial_deposit": "60000.00",
            "note": "Boosted",
        },
        headers=headers,
    )
    assert update_response.status_code == 200
    updated_goal = update_response.json()
    assert updated_goal["goal_name"] == "Emergency Fund+"
    assert updated_goal["current_amount"] == "60000.00"
    assert updated_goal["percentage_progress"] == 50.0

    dashboard_response = await client.get("/api/v1/dashboard", headers=headers)
    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.json()
    assert dashboard["savings"]["goal_name"] == "Emergency Fund+"
    assert dashboard["savings"]["saved_amount"] == "60000.00"
    assert dashboard["savings"]["target_amount"] == "120000.00"
    assert dashboard["savings"]["percentage_progress"] == 50.0

    delete_response = await client.delete(f"/api/v1/savings/{created_goal['id']}", headers=headers)
    assert delete_response.status_code == 204

    missing_response = await client.get(f"/api/v1/savings/{created_goal['id']}", headers=headers)
    assert missing_response.status_code == 404


@pytest.mark.asyncio
async def test_savings_auth_validation_and_ownership(client):
    auth = await _register_and_verify_user(client, email="savings-owner@example.com")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    other_auth = await _register_and_verify_user(client, email="other-savings@example.com")
    other_headers = {"Authorization": f"Bearer {other_auth['access_token']}"}

    unauthorized_response = await client.get("/api/v1/savings")
    assert unauthorized_response.status_code == 401

    invalid_response = await client.post(
        "/api/v1/savings",
        json={
            "goal_name": "Broken Goal",
            "target_amount": "0.00",
            "target_date": "2026-12-31",
            "initial_deposit": "0.00",
        },
        headers=headers,
    )
    assert invalid_response.status_code == 422

    created_goal = await _create_savings_goal(client, headers)

    foreign_detail_response = await client.get(f"/api/v1/savings/{created_goal['id']}", headers=other_headers)
    assert foreign_detail_response.status_code == 404

    foreign_update_response = await client.put(
        f"/api/v1/savings/{created_goal['id']}",
        json={
            "goal_name": "Nope",
            "target_amount": "5000.00",
            "target_date": "2026-12-31",
            "initial_deposit": "1000.00",
            "note": "Nope",
        },
        headers=other_headers,
    )
    assert foreign_update_response.status_code == 404

    foreign_delete_response = await client.delete(f"/api/v1/savings/{created_goal['id']}", headers=other_headers)
    assert foreign_delete_response.status_code == 404


@pytest.mark.asyncio
async def test_dashboard_aggregates_balance_budget_savings_recent_transactions_and_expense_insights(client):
    auth = await _register_and_verify_user(client, email="dashboard@example.com")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}

    await _create_income(client, headers, amount="60000.00", category="salary", date="2026-04-01", note="Salary")
    await _create_income(client, headers, amount="10000.00", category="freelance", date="2026-04-03", note="Freelance")
    budget = await _create_budget(
        client,
        headers,
        amount="50000.00",
        period_start="2026-04-01",
        period_end="2026-04-30",
    )
    await _create_expense(client, headers, amount="12000.00", category="Food", date="2026-04-02", note="Food spend")
    await _create_expense(client, headers, amount="8000.00", category="Transport", date="2026-04-04", note="Transport spend")
    await _create_savings_goal(
        client,
        headers,
        goal_name="New Laptop",
        target_amount="150000.00",
        initial_deposit="45000.00",
        target_date="2026-09-30",
        note="Laptop savings",
    )

    response = await client.get("/api/v1/dashboard", headers=headers)
    assert response.status_code == 200
    body = response.json()

    assert body["current_balance"] == "50000.00"
    assert body["summary"] == {
        "total_income": "70000.00",
        "total_expenses": "20000.00",
    }
    assert body["budget"]["budget_id"] == budget["id"]
    assert body["budget"]["total_budget"] == "50000.00"
    assert body["budget"]["spent"] == "20000.00"
    assert body["budget"]["remaining"] == "30000.00"
    assert body["budget"]["percentage_used"] == 40.0
    assert body["savings"]["goal_name"] == "New Laptop"
    assert body["savings"]["saved_amount"] == "45000.00"
    assert body["savings"]["target_amount"] == "150000.00"
    assert body["savings"]["percentage_progress"] == 30.0

    assert len(body["recent_transactions"]) == 4
    assert body["recent_transactions"][0]["type"] in {"income", "expense"}
    assert body["recent_transactions"][0]["date"] >= body["recent_transactions"][-1]["date"]

    insights = {item["category"]: item for item in body["expense_insights"]}
    assert insights["Food"]["amount"] == "12000.00"
    assert insights["Food"]["percentage_of_total"] == 60.0
    assert insights["Transport"]["amount"] == "8000.00"
    assert insights["Transport"]["percentage_of_total"] == 40.0
