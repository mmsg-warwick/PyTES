# Changelog fragments

Each pull request with a user-visible change adds one file here, named
`<PR number>.<type>.md`, holding one or two sentences for users. The types are `breaking`,
`contract`, `deprecated`, `feature`, `improvement` and `fix`; a PR may add several. See
[`CONTRIBUTING.md`](../CONTRIBUTING.md#changelog-entries). At release, `towncrier build`
assembles the fragments into [`CHANGELOG.md`](../CHANGELOG.md) and deletes them.
