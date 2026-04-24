# CampusKobo Backend Architecture

## 1. System shape

FastAPI is organized by product domains that mirror the UI, with async SQLAlchemy sessions shared across the app and Alembic managing schema migrations:

- `auth`: sign up, login, token refresh, logout, verification
- `onboarding`: goal selection, starter budget, starter categories
- `dashboard`: summary cards and recent activity
- `expenses`: create and list expenses
- `budgets`: monthly budget setup and management
- `savings`: goals and contributions
- `learning`: content feed and bookmarks
- `notifications`: alert preferences and quiet hours
- `support`: FAQ search and contact messages
- `users`: current profile and account metadata

## 2. Database schema

### Core identity

- `users`
  - `id`
  - `email`
  - `phone_number`
  - `full_name`
  - `password_hash`
  - `provider`
  - `status`
  - `is_email_verified`
  - `is_phone_verified`
  - `has_pin`
  - `pin_hash`
  - `biometric_enabled`
  - `last_login_at`
  - timestamps

- `user_sessions`
  - active device sessions for security settings and session tracking

- `refresh_tokens`
  - token rotation and revocation support

### Onboarding

- `user_goals`
  - chosen primary objective from onboarding

- `onboarding_progress`
  - current step and completion state

### Money tracking

- `expense_categories`
  - default and custom categories

- `expenses`
  - amount, title, merchant, date, category, status

- `budgets`
  - monthly limit and active period

### Savings

- `savings_goals`
  - target amount, progress, due date

- `savings_contributions`
  - contribution ledger

### Learning

- `learning_categories`
- `learning_content`
- `content_bookmarks`

### Notifications and support

- `notification_preferences`
  - per-user alert type settings and quiet hours

- `faq_categories`
- `faq_items`
- `support_messages`

## 3. Auth flow

### Sign up

1. `POST /api/v1/auth/register`
2. Validate email uniqueness.
3. Hash password with bcrypt.
4. Create user with `pending_verification`.
5. Create onboarding progress record.
6. Issue verification code via email or SMS.
7. Return access and refresh tokens or optionally gate access until verification.

### Verify email

1. `POST /api/v1/auth/verify-email`
2. Match verification code.
3. Mark account active and verified.

### Login

1. `POST /api/v1/auth/login`
2. Validate credentials.
3. Reject suspended/deleted accounts.
4. Optionally enforce PIN or biometric challenge for sensitive flows.
5. Issue fresh access and refresh tokens.
6. Persist session metadata.

### Refresh

1. `POST /api/v1/auth/refresh`
2. Validate refresh token and revocation state.
3. Rotate refresh token.
4. Return new access token and refresh token.

### Logout

1. `POST /api/v1/auth/logout`
2. Revoke refresh token.
3. Optionally close current device session.

## 4. API surface

### Auth

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/refresh`
- `POST /auth/verify-email`
- `POST /auth/resend-verification`
- `POST /auth/change-password`
- `POST /auth/change-email`
- `POST /auth/create-pin`
- `POST /auth/logout`

### User / settings

- `GET /users/me`

### Onboarding

- `GET /onboarding/progress`
- `POST /onboarding/goal`
- `POST /onboarding/budget`
- `POST /onboarding/categories`

### Dashboard

- `GET /dashboard/summary`

### Expenses

- `GET /expenses`
- `POST /expenses`

### Budgets

- `GET /budgets`
- `POST /budgets`

### Savings

- `GET /savings/goals`
- `POST /savings/goals`
- `POST /savings/goals/{goal_id}/contributions`

### Learning

- `GET /learning/content`
- `POST /learning/content/{content_id}/bookmark`

### Notifications

- `GET /notifications/preferences`
- `PUT /notifications/preferences`

### Support

- `GET /support/faqs?search=&category=`
- `POST /support/messages`

## 5. Business logic rules

### Expenses

- Expense amount must be positive.
- Category must belong to the user or be a default category.
- Expense creation should trigger budget recalculation.
- If spending crosses configured thresholds, create notification events.

### Budgets

- One active budget per user per date window.
- Periods should not overlap unless explicitly versioned.
- Dashboard remaining amount is `budget.amount - sum(expenses within period)`.

### Savings

- Contribution updates the parent goal balance.
- Goal status changes to `completed` when current amount reaches target.

### Notifications

- Quiet hours suppress push/email delivery but not critical security messages.
- Preferences are stored by notification type.

### Support

- FAQ search should use title/body keyword search.
- Support message creation should open a ticket and optionally notify admins.

## 6. Recommended next implementation pieces

1. Add repositories or CRUD modules instead of placeholder service methods.
2. Add seed scripts for categories, FAQ content, and learning content.
3. Add Redis-backed OTP and token revocation.
4. Add background jobs for reminders, alerts, and email delivery.
5. Add tests for auth, onboarding, expense creation, and budget calculations.
