# Workspace verification

## Automated domain and boundary checks

Run `python -m unittest discover -s tests -v` from the repository root. The suite contains 20 tests, including the shared HTTP boundary/storage checks. Domain checks cover the application's meaningful invariants, persistence across new workspace instances and invalid inputs. The volunteer suite includes competing assignment requests to verify capacity is enforced transactionally. The ML suite verifies group-disjoint and strictly ordered temporal splits, local artifact prediction and protocol comparison fingerprints.

The implementation was exercised locally on 2026-11-04. Final hosted results are available in [Workspace verification](https://github.com/HM-023/NetworkThreatDetection/actions/workflows/workspace.yml); inspect the commit associated with each run. The workflow additionally runs the browser journey and uploads desktop/mobile captures. A green unit-test job alone is not evidence that a browser job passed.

## Boundaries

Unit tests and browser journeys verify the documented local workflows. They do not establish production readiness, real-traffic ML accuracy, actual firewall enforcement, simulator import compatibility, independent penetration-test findings or hosted multi-user behavior. The C# prototype, where present, has its separate Windows build check.

## Browser journey

`tests/browser.cjs` starts an isolated server using a temporary data directory, uses real browser controls to exercise the main workflow, checks for JavaScript errors, captures 1440-pixel desktop and 390-pixel mobile views, tests viewport overflow and reloads saved state. The temporary test data is deleted afterward. To run it locally with Node 22+:

```bash
npm install --no-save --package-lock=false playwright@1.56.1
npx playwright install chromium
node tests/browser.cjs
```

The application itself needs neither Node nor Playwright. These are verification dependencies only.
