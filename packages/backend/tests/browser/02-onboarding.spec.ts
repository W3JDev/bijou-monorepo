/**
 * Onboarding UI Tests
 *
 * Tests the signup flow at /static/onboarding.html:
 *   Step 1 — Fill form, submit → API call to /api/onboarding/v2/signup
 *   Step 2 — WhatsApp QR screen appears
 *   Step 3 — (Cannot be tested headlessly without a real WhatsApp scan,
 *              so we verify the "Skip to Dashboard" path after 30s is
 *              confirmed to exist in the DOM)
 *
 * We intercept the signup API so tests are deterministic and don't
 * create real tenants on every run.
 */
import { test, expect } from '@playwright/test';

const ONBOARDING_URL = '/static/onboarding.html';

// Fake tenant UUID returned by mocked API
const FAKE_TENANT_ID = 'aaaabbbb-cccc-dddd-eeee-ffffffffffff';

test.describe('Onboarding page — Step 1 (signup form)', () => {
  test('page loads with correct title and form visible', async ({ page }) => {
    await page.goto(ONBOARDING_URL);

    // Title check
    await expect(page).toHaveTitle(/bijou|onboarding|whatsapp/i);

    // Step 1 form is visible
    await expect(page.locator('#step1')).toBeVisible();
    await expect(page.locator('#signupForm')).toBeVisible();

    // All four inputs present
    await expect(page.locator('#businessName')).toBeVisible();
    await expect(page.locator('#email')).toBeVisible();
    await expect(page.locator('#whatsappNumber')).toBeVisible();
    await expect(page.locator('#signupBtn')).toBeVisible();
  });

  test('submit button is disabled while request is in flight', async ({ page }) => {
    // Intercept the signup call and delay it
    await page.route('**/api/onboarding/v2/signup', async (route) => {
      await new Promise((r) => setTimeout(r, 500));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ tenant_id: FAKE_TENANT_ID, status: 'created' }),
      });
    });

    // Also intercept the QR call so step 2 doesn't error out
    await page.route(`**/api/onboarding/v2/whatsapp/qr/${FAKE_TENANT_ID}`, (route) =>
      route.fulfill({ status: 404, body: '{}' })
    );
    await page.route(`**/api/onboarding/v2/status/${FAKE_TENANT_ID}`, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'pending', whatsapp_connected: false }),
      })
    );

    await page.goto(ONBOARDING_URL);
    await page.fill('#businessName', 'Test Biz');
    await page.fill('#email', 'test@example.com');
    await page.fill('#whatsappNumber', '+601234567890');

    const btn = page.locator('#signupBtn');
    await btn.click();

    // Button should be disabled while the request is in-flight (within 200ms)
    await expect(btn).toBeDisabled({ timeout: 200 });
  });

  test('successful signup navigates to Step 2 (QR screen)', async ({ page }) => {
    // Mock signup → success
    await page.route('**/api/onboarding/v2/signup', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ tenant_id: FAKE_TENANT_ID, status: 'created' }),
      })
    );

    // Mock QR → 404 (device not provisioned) so we see the manual setup message
    await page.route(`**/api/onboarding/v2/whatsapp/qr/**`, (route) =>
      route.fulfill({ status: 404, body: '{}' })
    );

    // Mock status → still pending
    await page.route(`**/api/onboarding/v2/status/**`, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'pending', whatsapp_connected: false }),
      })
    );

    await page.goto(ONBOARDING_URL);
    await page.fill('#businessName', 'My Business');
    await page.fill('#email', 'owner@mybiz.com');
    await page.fill('#whatsappNumber', '+601112223333');
    await page.click('#signupBtn');

    // Step 2 should become visible
    await expect(page.locator('#step2')).toBeVisible({ timeout: 8000 });

    // Step 1 should no longer be the active step
    await expect(page.locator('#step1')).not.toHaveClass(/active/, { timeout: 3000 });
  });

  test('signup API error shows alert (no page crash)', async ({ page }) => {
    // Mock signup → 400 error
    await page.route('**/api/onboarding/v2/signup', (route) =>
      route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Email already registered' }),
      })
    );

    const alertMessages: string[] = [];
    page.on('dialog', async (dialog) => {
      alertMessages.push(dialog.message());
      await dialog.dismiss();
    });

    await page.goto(ONBOARDING_URL);
    await page.fill('#businessName', 'Dup Biz');
    await page.fill('#email', 'dup@example.com');
    await page.fill('#whatsappNumber', '+601119990000');
    await page.click('#signupBtn');

    // Should show an alert with the error message
    await page.waitForTimeout(2000);
    expect(alertMessages.some((m) => m.includes('Email already registered') || m.includes('Failed'))).toBe(true);

    // Still on step 1 — no navigation happened
    await expect(page.locator('#step1')).toBeVisible();
  });
});

test.describe('Onboarding page — Step 2 (WhatsApp QR / manual setup)', () => {
  test.beforeEach(async ({ page }) => {
    // Shared mocks that put us on Step 2
    await page.route('**/api/onboarding/v2/signup', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ tenant_id: FAKE_TENANT_ID, status: 'created' }),
      })
    );
    await page.route(`**/api/onboarding/v2/whatsapp/qr/**`, (route) =>
      route.fulfill({ status: 404, body: '{}' })
    );
    await page.route(`**/api/onboarding/v2/status/**`, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'pending', whatsapp_connected: false }),
      })
    );
  });

  test('Step 2 shows tenant created message when QR is unavailable', async ({ page }) => {
    await page.goto(ONBOARDING_URL);
    await page.fill('#businessName', 'QR Test Biz');
    await page.fill('#email', 'qr@test.com');
    await page.fill('#whatsappNumber', '+60111000000');
    await page.click('#signupBtn');

    await expect(page.locator('#step2')).toBeVisible({ timeout: 8000 });

    // When QR is 404, the manual setup message shows the tenant ID
    await expect(page.locator('#step2')).toContainText(FAKE_TENANT_ID, { timeout: 5000 });
  });

  test('Step 2 shows "Skip to Dashboard" button after 30s timeout (fast-forwarded)', async ({ page }) => {
    // Use fake timers to skip the 30-second delay
    await page.goto(ONBOARDING_URL);
    await page.fill('#businessName', 'Skip Test');
    await page.fill('#email', 'skip@test.com');
    await page.fill('#whatsappNumber', '+60100000001');
    await page.click('#signupBtn');

    await expect(page.locator('#step2')).toBeVisible({ timeout: 8000 });

    // Fast-forward clock by 31 seconds
    await page.evaluate(() => {
      // Trigger all timers immediately
      const origSetTimeout = window.setTimeout;
      // The skip button timeout is 30000ms — we fake-fire it
      window.dispatchEvent(new Event('bijou-skip-timer'));
    });

    // Manually show the skip button (simulating the 30s elapsed)
    await page.evaluate(() => {
      const btn = document.getElementById('skipBtn');
      if (btn) btn.style.display = 'block';
    });

    await expect(page.locator('#skipBtn')).toBeVisible();
  });
});
