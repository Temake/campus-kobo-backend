from datetime import date


async def test_onboarding_goal_budget_categories_and_first_expense_completion(
    client,
    registered_user,
    seeded_default_categories,
):
    access_token = registered_user["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    goal_response = await client.post(
        "/api/v1/onboarding/goal",
        json={"goal_type": "stay_on_budget"},
        headers=headers,
    )
    assert goal_response.status_code == 204

    budget_response = await client.post(
        "/api/v1/onboarding/budget",
        json={"amount": "50000.00", "currency": "NGN"},
        headers=headers,
    )
    assert budget_response.status_code == 204

    categories_response = await client.post(
        "/api/v1/onboarding/categories",
        json={"category_ids": seeded_default_categories[:2]},
        headers=headers,
    )
    assert categories_response.status_code == 204

    progress_before_expense = await client.get("/api/v1/onboarding/progress", headers=headers)
    assert progress_before_expense.status_code == 200
    progress_before_body = progress_before_expense.json()
    assert progress_before_body["current_step"] == "first_expense"
    assert progress_before_body["completed_step_count"] >= 3
    assert progress_before_body["is_completed"] is False

    expense_response = await client.post(
        "/api/v1/expenses",
        json={
            "title": "Lunch",
            "description": "First onboarding expense",
            "amount": "2500.00",
            "currency": "NGN",
            "spent_on": str(date.today()),
            "category_id": None,
            "merchant_name": "Campus Cafe",
        },
        headers=headers,
    )
    assert expense_response.status_code == 201

    progress_after_expense = await client.get("/api/v1/onboarding/progress", headers=headers)
    assert progress_after_expense.status_code == 200
    progress_after_body = progress_after_expense.json()
    assert progress_after_body["current_step"] == "completed"
    assert progress_after_body["completed_step_count"] >= 4
    assert progress_after_body["is_completed"] is True
