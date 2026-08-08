/**
 * API Smoke Tests
 * Fast checks that all critical endpoints exist and return the right status codes.
 * No browser needed — uses page.request (Playwright's fetch under the hood).
 */
import { test, expect } from '@playwright/test';

const BASE = 'https://bijou-staging.fly.dev';

test.describe('API smoke tests', () => {
  test('GET /health returns healthy', async ({ request }) => {
    const res = await request.get(`${BASE}/health`);
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.status).toBe('healthy');
  });

  test('GET /api/payment/health returns healthy', async ({ request }) => {
    const res = await request.get(`${BASE}/api/payment/health`);
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.status).toBe('healthy');
  });

  test('GET /api/payment/plans returns at least one plan', async ({ request }) => {
    const res = await request.get(`${BASE}/api/payment/plans`);
    expect(res.status()).toBe(200);
    const body = await res.json();
    // Accepts either { plans: [...] } or a plain array
    const plans = Array.isArray(body) ? body : body.plans ?? body.data ?? [];
    expect(plans.length).toBeGreaterThan(0);
  });

  test('GET /api/onboarding/health returns healthy', async ({ request }) => {
    const res = await request.get(`${BASE}/api/onboarding/health`);
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.status).toBe('healthy');
  });

  test('POST /api/onboarding/v2/signup with missing fields returns 422', async ({ request }) => {
    const res = await request.post(`${BASE}/api/onboarding/v2/signup`, {
      data: {},
    });
    // FastAPI returns 422 for missing required fields
    expect([400, 422]).toContain(res.status());
  });

  test('POST /api/payment/subscribe with unknown tenant_id returns 404', async ({ request }) => {
    const res = await request.post(`${BASE}/api/payment/subscribe`, {
      data: {
        tenant_id: '00000000-0000-0000-0000-000000000000',
        plan_code: 'starter',
        billing_period: 'monthly',
      },
    });
    expect(res.status()).toBe(404);
  });

  test('POST /api/dashboard/send-message with no body returns 400 or 422', async ({ request }) => {
    const res = await request.post(`${BASE}/api/dashboard/send-message`, { data: {} });
    expect([400, 422]).toContain(res.status());
  });

  test('Static files are served — onboarding.html', async ({ request }) => {
    const res = await request.get(`${BASE}/static/onboarding.html`);
    expect(res.status()).toBe(200);
    const text = await res.text();
    // Match case-insensitively — some servers emit lowercase <!doctype html>
    expect(text.toLowerCase()).toContain('<!doctype html');
  });

  test('Static files are served — dashboard.html', async ({ request }) => {
    const res = await request.get(`${BASE}/static/dashboard.html`);
    expect(res.status()).toBe(200);
    const text = await res.text();
    expect(text.toLowerCase()).toContain('<!doctype html');
  });
});
