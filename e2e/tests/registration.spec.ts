import { test, expect } from '@playwright/test';

test.describe('Registration Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('landing page loads correctly', async ({ page }) => {
    // Check page title and header
    await expect(page.locator('text=FoodLogr')).toBeVisible();
    await expect(page.locator('text=Track your food and macros')).toBeVisible();

    // Check feature cards are visible
    await expect(page.locator('text=Log Food Naturally')).toBeVisible();
    await expect(page.locator('text=Track Progress')).toBeVisible();
    await expect(page.locator('text=Persistent Memory')).toBeVisible();

    // Check registration form is present
    await expect(page.locator('text=Get Started')).toBeVisible();
    await expect(page.getByPlaceholder('you@example.com')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Get API Key' })).toBeVisible();
  });

  test('shows error for empty email submission', async ({ page }) => {
    // Click submit without entering email
    await page.getByRole('button', { name: 'Get API Key' }).click();

    // HTML5 validation should prevent submission
    const emailInput = page.getByPlaceholder('you@example.com');
    await expect(emailInput).toBeFocused();
  });

  test('shows error for invalid email format', async ({ page }) => {
    // Enter invalid email
    await page.getByPlaceholder('you@example.com').fill('not-an-email');
    await page.getByRole('button', { name: 'Get API Key' }).click();

    // HTML5 validation should show error
    const emailInput = page.getByPlaceholder('you@example.com');
    await expect(emailInput).toBeFocused();
  });

  test('successful registration shows API key', async ({ page }) => {
    // Generate unique email for test
    const testEmail = `e2e-test-${Date.now()}@test.foodlogr.app`;

    // Fill in email and submit
    await page.getByPlaceholder('you@example.com').fill(testEmail);
    await page.getByRole('button', { name: 'Get API Key' }).click();

    // Wait for success state
    await expect(page.locator('text=You\'re all set!')).toBeVisible({ timeout: 15000 });

    // Check API key is displayed
    await expect(page.locator('text=Your API Key')).toBeVisible();
    const apiKeyField = page.locator('input[readonly]').first();
    await expect(apiKeyField).toBeVisible();

    // Verify API key format (starts with flr_)
    const apiKeyValue = await apiKeyField.inputValue();
    expect(apiKeyValue).toMatch(/^flr_/);

    // Check Claude command is shown
    await expect(page.locator('text=Run this in your terminal')).toBeVisible();
    await expect(page.locator('text=claude mcp add')).toBeVisible();

    // Check copy buttons are present
    const copyButtons = page.getByRole('button', { name: 'Copy' });
    await expect(copyButtons.first()).toBeVisible();
  });

  test('copy button works for API key', async ({ page, context }) => {
    // Grant clipboard permissions
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);

    const testEmail = `e2e-copy-test-${Date.now()}@test.foodlogr.app`;

    // Register
    await page.getByPlaceholder('you@example.com').fill(testEmail);
    await page.getByRole('button', { name: 'Get API Key' }).click();

    // Wait for success
    await expect(page.locator('text=You\'re all set!')).toBeVisible({ timeout: 15000 });

    // Get the API key value
    const apiKeyField = page.locator('input[readonly]').first();
    const apiKeyValue = await apiKeyField.inputValue();

    // Click copy button
    const copyButtons = page.getByRole('button', { name: 'Copy' });
    await copyButtons.first().click();

    // Verify clipboard content
    const clipboardText = await page.evaluate(() => navigator.clipboard.readText());
    expect(clipboardText).toBe(apiKeyValue);
  });
});

test.describe('API Health Check', () => {
  test('backend health endpoint responds', async ({ request }) => {
    const apiUrl = process.env.API_URL || 'https://mcp.foodlogr.app';
    const response = await request.get(`${apiUrl}/health`);

    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);

    const data = await response.json();
    expect(data.status).toBe('healthy');
    expect(data.service).toBe('foodlogr-mcp');
  });

  test('CORS headers are present for allowed origin', async ({ request }) => {
    const apiUrl = process.env.API_URL || 'https://mcp.foodlogr.app';

    const response = await request.fetch(`${apiUrl}/auth/register`, {
      method: 'OPTIONS',
      headers: {
        'Origin': 'https://foodlogr.app',
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'Content-Type',
      },
    });

    expect(response.ok()).toBeTruthy();
    expect(response.headers()['access-control-allow-origin']).toBe('https://foodlogr.app');
    expect(response.headers()['access-control-allow-methods']).toContain('POST');
  });
});

test.describe('Registration API', () => {
  test('register endpoint accepts valid email', async ({ request }) => {
    const apiUrl = process.env.API_URL || 'https://mcp.foodlogr.app';
    const testEmail = `api-test-${Date.now()}@test.foodlogr.app`;

    const response = await request.post(`${apiUrl}/auth/register`, {
      data: { email: testEmail },
    });

    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);

    const data = await response.json();
    expect(data.api_key).toMatch(/^flr_/);
    expect(data.message).toContain('Registration successful');
    expect(data.claude_command).toContain('claude mcp add');
  });

  test('register endpoint rejects invalid email', async ({ request }) => {
    const apiUrl = process.env.API_URL || 'https://mcp.foodlogr.app';

    const response = await request.post(`${apiUrl}/auth/register`, {
      data: { email: 'not-valid' },
    });

    expect(response.status()).toBe(400);

    const data = await response.json();
    expect(data.error).toBeDefined();
  });

  test('register endpoint rejects empty body', async ({ request }) => {
    const apiUrl = process.env.API_URL || 'https://mcp.foodlogr.app';

    const response = await request.post(`${apiUrl}/auth/register`, {
      data: {},
    });

    expect(response.status()).toBe(400);
  });
});
