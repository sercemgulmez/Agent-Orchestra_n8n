# Yemeksepeti Mobile Appium Profile

This folder defines black-box Appium smoke profiles for Yemeksepeti Android and iOS app testing.

Safety rules:

- Do not use real personal accounts.
- Do not submit live orders or payments.
- App binaries, device IDs, test accounts, and Appium server URL come from environment variables.
- These profiles are intended for mock, staging, emulator, or simulator runs.
- Runtime orchestration rejects cart, checkout, order, payment, coupon, personal data, and login-submit tasks for mobile profiles unless a future explicit safe staging profile is added.

Required environment examples:

- `APPIUM_SERVER_URL`
- `YEMEKSEPETI_ANDROID_APP`
- `YEMEKSEPETI_IOS_APP`
- `YEMEKSEPETI_TEST_EMAIL`
- `YEMEKSEPETI_TEST_PASSWORD`
