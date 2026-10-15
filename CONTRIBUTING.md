# Contributing a skill

Alfred skills are public executable policy. Treat a pull request like a code change, not a prompt
collection.

## Before opening a pull request

- Remove names, email addresses, phone numbers, message text, destinations, account identifiers,
  tokens, and every other observed user value.
- Replace reusable values with typed placeholders such as `${destination}` or `${query}`.
- Never include the original voice transcript, screenshots, accessibility dumps, or model traces.
- Keep the action plan deterministic and as short as possible.
- Use `safety: "confirm"` for any `click` or `set_text` action. Alfred also upgrades interactive
  skills to confirmation-required on the device.
- Do not target Send, Delete, Purchase, Pay, Transfer, Install, Uninstall, or factory-reset controls.

## Folder placement

Use `skills/<publisher-or-platform>/<application>/<intent>.json`. Examples:

```text
skills/android/settings/open.json
skills/google/maps/navigate.json
skills/google/youtube/search.json
```

Skill IDs and canonical intents are stable dotted identifiers. Increase `version` when behavior
changes. Do not reuse a version for different content.

## Pull-request workflow

1. Fork this repository and create a branch.
2. Add or update one or more skill JSON files.
3. Rebuild the catalog with a revision greater than the current revision:

   ```bash
   python3 scripts/build_registry.py --write --revision <next-revision>
   ```

4. Run `python3 scripts/build_registry.py --check`.
5. Open a pull request using the template and explain the tested Android version/application.
6. Address automated validation and human safety review.

Merging the pull request publishes the new catalog. Alfred clients see it on their next manual or
automatic refresh.
