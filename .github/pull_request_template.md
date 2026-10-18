## Description

<!-- What does this change, and why? -->

Closes #

## Checklist

See [CONTRIBUTING.md](https://github.com/mmsg-warwick/PyTES/blob/main/CONTRIBUTING.md).

- [ ] The tests pass (`uv run pytest`), including the conformance suite.
- [ ] The pre-commit hooks pass (`uv run pre-commit run --all-files`).
- [ ] A changelog fragment `changelog.d/<PR number>.<type>.md` describes any user-visible
      change, or the PR has the `no changelog` label.
- [ ] New code has docstrings, and a new capability has a short example notebook.
- [ ] If the model contract changes (variable names, units, signs, parameter names,
      submodel interfaces): an entry in `docs/design/findings.md` and a `contract` fragment.
- [ ] If a design decision changes: `docs/design/DESIGN.md` is updated in this PR.
