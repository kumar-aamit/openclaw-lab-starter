# base-app rules
1. Your app is app/. Edit nothing outside it.
2. Start from the user's idea or a brief in catalog/. Copy patterns from examples/.
3. Every screen uses one layout. This platform version has review; workspace and assistant come later.
4. Hooks use only the Python standard library and the ctx helpers. No new packages.
5. Sample data is synthetic. Never paste real customer, patient or employee data.
6. No network calls and no external URLs, in code or in HTML.
7. If no building block fits a request, say so and suggest the closest one.
8. Run make check after every change. Do not push until it passes.
9. Push to your repo (see lab.env), run make wait and make smoke, and report the timings.

How to build and change the app: skills/base-app/SKILL.md.
