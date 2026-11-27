# base-app rules
1. Before any change to app/, read skills/base-app/SKILL.md and the closest example in examples/. Never invent fields or file layouts: make check is the authority.
2. Your app is app/. Edit nothing outside it.
3. Start from the user's idea or a brief in catalog/. Copy patterns from examples/ (alert-triage, netconf-guard).
4. Every screen uses one layout. This platform version has review; workspace and assistant come later.
5. Hooks use only the Python standard library and the ctx helpers. No new packages.
6. Sample data is synthetic. Never paste real customer, patient or employee data.
7. No network calls and no external URLs, in code or in HTML.
8. If no building block fits a request, say so and suggest the closest one.
9. Run make check after every change. Do not push until it passes.
10. Push to your repo (see lab.env), run make wait and make smoke, and report the new version number and the timings.
11. Work only in your own team's repo, team-<N>. If it is not cloned yet, ask for the team number and clone only that repo (skills/base-app/SKILL.md, Clone the team repo). If the number is wrong or the clone fails, say so and ask again. Never try other numbers or other teams' repos.

How to build and change the app: skills/base-app/SKILL.md.
