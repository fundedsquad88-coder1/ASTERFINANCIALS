# Aster Financials — Android App (GitHub-ready)

This is a complete Android Studio/Gradle project for the Aster Financials mobile app prototype.

## Project structure

- `app/` — Android application module
- `app/src/main/assets/` — Aster UI and logo
- `app/src/main/java/.../MainActivity.java` — WebView launcher
- `app/src/main/res/values/styles.xml` — app theme
- `.github/workflows/build-apk.yml` — automatic GitHub Actions APK build
- `build.gradle` / `settings.gradle` — root Gradle configuration

## Build the APK on GitHub

1. Create/open your GitHub repository.
2. Upload the **contents of this folder while preserving the folders exactly as shown above**. Do not upload all files into the repository root individually.
3. Confirm that the repository root contains `app`, `.github`, `build.gradle`, and `settings.gradle`.
4. Open **Actions** → **Build Aster APK** → **Run workflow**.
5. When the run is green, open it and download the artifact `aster-financials-debug-apk`.
6. The downloaded artifact contains `app-debug.apk`.

## Important

The current app is a UI prototype. Dashboard balances, prices, returns, transactions, and trading controls are demo interface values. No live funds, wallet custody, authentication, market execution, or real-money trading backend is connected.
