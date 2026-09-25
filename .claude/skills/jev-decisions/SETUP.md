# jev-decisions setup

Paste this into the repo README if you want it there.

## Jev decisions for wayfinder

The `jev-decisions` Claude Code skill sends wayfinder's recurring judgment calls to Jev (TypeSafe) as typed questions and gates the answers in code.

Files:

- `.claude/skills/jev-decisions/SKILL.md` - when and how the agent calls Jev
- `.claude/skills/jev-decisions/questions.json` - fixed questions and gate thresholds
- `scripts/jev_decide.py` - CLI that calls the API and applies the gates (standard library only, Python 3.8+)

Setup:

1. Commit the `.claude/skills/jev-decisions/` folder and `scripts/jev_decide.py`. Claude Code picks up project skills from `.claude/skills/` on its own, so there's nothing to install. (`npx skills add` is only needed for skills published in another repo.)
2. Get an API key from the TypeSafe dashboard and export it. Don't commit it.

   ```bash
   export TYPESAFE_API_KEY=...
   ```

3. Check the request without spending a call:

   ```bash
   python3 scripts/jev_decide.py classify --destination "Answer questions with cited suttas" --ticket "Try hybrid BM25 + embeddings" --dry-run
   ```

4. Optional: pin the model. `jev-latest` is an alias. After a few real runs, copy the `model` value the script prints (e.g. `jev-1.13.0`) into `questions.json` or `export JEV_MODEL=...`.

Tune thresholds in the `gate` blocks of `questions.json`. They are starting guesses.
