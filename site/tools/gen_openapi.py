"""Regenerate site/src/openapi.json from the FastAPI app itself.

Run from the repo root with the service dependencies installed:
    python site/tools/gen_openapi.py

The script builds the app with throwaway local settings, dumps the
OpenAPI schema the app serves, and cross-checks the route auth wiring
by inspecting each route's dependency tree (get_current_user and
require_admin). It writes only site/src/openapi.json. The site build
(gen-data.mjs) then derives its endpoint table from that committed
schema and checks it against the README API table, so the published
explorer can never drift from the service.
"""
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./openapi-gen.db")
os.environ.setdefault("JWT_SECRET", "openapi-generation-placeholder")

from app.deps import get_current_user, require_admin  # noqa: E402
from app.main import create_app  # noqa: E402


def calls_in(dependant):
    found = set()
    stack = [dependant]
    while stack:
        dep = stack.pop()
        if dep.call in (get_current_user, require_admin):
            found.add(dep.call.__name__)
        stack.extend(dep.dependencies)
    return found


def main():
    app = create_app()
    schema = app.openapi()
    problems = []
    for route in app.routes:
        methods = getattr(route, "methods", None)
        if not methods or not hasattr(route, "dependant"):
            continue
        calls = calls_in(route.dependant)
        ops = schema["paths"].get(route.path, {})
        for method in methods:
            if method == "HEAD":
                continue
            op = ops.get(method.lower(), {})
            secured = bool(op.get("security"))
            if "require_admin" in calls and not secured:
                problems.append(f"{method} {route.path}: admin route without bearer security")
            if "get_current_user" in calls and not secured:
                problems.append(f"{method} {route.path}: user route without bearer security")
            if not calls and secured:
                problems.append(f"{method} {route.path}: secured in schema but no auth dependency")
    if problems:
        raise SystemExit("auth cross-check failed:\n" + "\n".join(problems))
    out = REPO / "site" / "src" / "openapi.json"
    out.write_text(json.dumps(schema, indent=2) + "\n")
    ops = sum(len(v) for v in schema["paths"].values())
    print(f"openapi.json written: {len(schema['paths'])} paths, {ops} operations, auth cross-check passed")


if __name__ == "__main__":
    main()
