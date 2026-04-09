## What this PR does

Brief description of the change and why it was made.

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Refactor / cleanup
- [ ] Docs / config
- [ ] Test

## How to test

Steps to verify this works correctly.

## Checklist

- [ ] Backend tests pass: `uv run pytest backend/tests -q`
- [ ] Frontend builds: `pnpm --dir frontend build`
- [ ] No API keys or secrets are sent to the browser
- [ ] If touching backtester: temporal integrity is preserved in strict mode
- [ ] If touching live trading: server-side guardrails still apply
- [ ] If changing API shapes: both `frontend/src/api/types.ts` and the backend route are updated
- [ ] If changing settings behavior: frontend editor, store wiring, and backend PATCH route are all consistent
