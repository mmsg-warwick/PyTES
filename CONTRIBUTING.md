# Contributing to PyTES

If you'd like to contribute to PyTES (thanks!), please have a look at the
[workflow below](#workflow). If you're already familiar with it, the
[checks before you commit](#checks-before-you-commit) are directly below.

## Checks before you commit

- [All tests pass](#testing): `uv run pytest`
- [The pre-commit hooks pass](#pre-commit-hooks): `uv run pre-commit run --all-files`
- [A changelog fragment](#changelog-entries) describes any user-visible change.

### Pre-commit hooks

PyTES uses [pre-commit](https://pre-commit.com) hooks to check and format the code (ruff,
and checks for YAML, TOML, file endings and whitespace). Install them once, after
[setting up your environment](#a-before-you-begin):

```bash
uv run pre-commit install
```

They then run on the files of every commit. To run them on all files:

```bash
uv run pre-commit run --all-files
```

To commit anyway, for example to push work in progress for discussion, use
`git commit --no-verify`.

## Workflow

We use [Git](https://en.wikipedia.org/wiki/Git) and [GitHub](https://github.com) to
coordinate our work. When making any kind of change, we follow the procedure below.

### A. Before you begin

1. Open an [issue](https://docs.github.com/en/issues) to discuss your proposal before any
   coding is done.
2. If the change affects the design (models, variables, parameters, submodel interfaces),
   read [`docs/design/DESIGN.md`](docs/design/DESIGN.md) first. It records what is
   **decided**, what is **deferred** (and the hooks that must stay in place) and what is
   **open**. Decided points are not reopened without discussion.
3. Create a [branch](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-branches),
   ideally on your own [fork](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/about-forks),
   where all your changes will be made.
4. Clone the repository (or your fork) and set up the development environment with
   [uv](https://docs.astral.sh/uv/):

   ```bash
   uv sync
   ```

   This installs PyTES in editable mode with the development and notebook tools, from the
   lock file `uv.lock`.
5. Check that everything works: `uv run pytest`.

You now have everything you need to start making changes!

### B. Writing your code

6. PyTES is written in [Python](https://www.python.org) on top of
   [PyBaMM](https://pybamm.org): every model is a PyBaMM model, and PyBaMM is never hidden
   from the user. If you know PyBaMM, you know most of what you need.
7. Follow the [coding style guidelines](#coding-style-guidelines).
8. Commit your changes with [useful, descriptive commit messages](https://cbea.ms/git-commit/).
   They are public and should still make sense a few months from now.
9. If you change the **model contract** (variable names, units, signs, parameter names,
   submodel interfaces), add an entry to [`docs/design/findings.md`](docs/design/findings.md)
   explaining what changed and why, and a `contract` [changelog fragment](#changelog-entries).
   If the change alters a design decision, update `DESIGN.md` in the same pull request.
10. If you want to add a dependency or reuse code from elsewhere, read
    [Dependencies and reusing code](#dependencies-and-reusing-code).

### C. Merging your changes into PyTES

11. [Test your code](#testing), including the conformance suite.
12. Add a [changelog fragment](#changelog-entries) for any user-visible change.
13. Document your change: [docstrings](#documentation), and for a new capability a short
    [example notebook](#example-notebooks).
14. When your code is finished, or ready for serious discussion, run the
    [checks](#checks-before-you-commit) and open a
    [pull request](https://docs.github.com/en/pull-requests) (PR).
15. Your PR will be reviewed, and changes may be suggested, which you make by adding commits
    to your branch. When everything is ready, a maintainer merges it.

## Changelog entries

PyTES keeps its changelog with [towncrier](https://towncrier.readthedocs.io). Instead of
editing [`CHANGELOG.md`](CHANGELOG.md), each PR with a user-visible change adds a small
file, a *fragment*, to [`changelog.d/`](changelog.d), named `<PR number>.<type>.md`, with
one or two sentences written for users. Fragments never conflict with each other, and at
each release they are assembled into `CHANGELOG.md` and deleted.

The types, in the order they appear in the changelog:

- `breaking` (**Breaking changes**): anything existing code or results would notice, such as
  a renamed or removed variable or parameter, a removal, or a new default that moves
  results. Say how to adapt.
- `contract` (**Model contract changes**): any change to the model contract (variable
  names, units, signs, parameter names, submodel interfaces), additions included. Name the
  entry in [`docs/design/findings.md`](docs/design/findings.md) that logs it (e.g. F-049). A
  contract change that existing code would notice also has a `breaking` fragment.
- `deprecated` (**Deprecations**): an API that now warns and will be removed in a later
  release; say when.
- `feature` (**New features**): a model, an option, a submodel, a toolkit function.
- `improvement` (**Improvements**): better existing behaviour that breaks nothing: speed,
  clearer errors, more outputs.
- `fix` (**Bug fixes**): wrong behaviour corrected.

For example, for PR 42:

```bash
echo 'Experiment steps report which termination ended them.' > changelog.d/42.feature.md
```

A PR can belong to several sections: add one fragment for each, all named with its number
(`42.feature.md` and `42.breaking.md`). For two entries in the same section, add a counter
(`42.feature.md` and `42.feature.1.md`).

A PR with no user-visible change (a refactor, tests, CI, a typo) needs no fragment: label it
`no changelog`, and the CI check for a fragment is skipped. To preview the next changelog:

```bash
uv run towncrier build --draft --version <next version>
```

At release, a maintainer runs `uv run towncrier build --version <version>`, which writes
the new section into `CHANGELOG.md` and deletes the fragments.

## Coding style guidelines

PyTES follows [PEP 8](https://peps.python.org/pep-0008/), checked and formatted by
[ruff](https://docs.astral.sh/ruff/) through the [pre-commit hooks](#pre-commit-hooks).
Its configuration is in `pyproject.toml`; the ruff version in `.pre-commit-config.yaml`
matches the one in the development environment.

### Language

Write prose in British English: docstrings, comments, documentation, notebooks and the names
of variables and parameters (behaviour, colour, centre, licence, modelling; -ise endings such
as discretise). Identifiers from Python and other libraries keep their own spelling
(matplotlib's `color=`, pytest's `parametrize`).

### Naming

Naming is hard. Aim for descriptive names, and avoid abbreviations where this does not make
names overly long. Class names are CamelCase (`PackedBedModel`); functions, methods and
variables are lower case with underscores (`energy_between`). Short mathematical names are
fine inside equations when they follow the docstring's notation (`T_f`, `h`).

### PyTES and PyBaMM conventions

- **Parameter names** carry their units, as in PyBaMM: `"PCM latent heat [J.kg-1]"`.
  Material and fluid properties start with their layer's prefix (`PCM ...`, `Metal ...`,
  `Heat transfer fluid ...`); geometry starts with the geometric object (`Tube ...`,
  `Bed ...`, `Capsule ...`, `Storage ...`).
- **SI units only** in models. Twins in °C, kW, kWh, minutes and hours are generated when a
  model is built; never write them by hand. Temperature differences contain "temperature
  difference" in their names and get no twin.
- **Power** is positive on discharge and defined from the fluid's enthalpy,
  `mdot (h_out - h_in)`.
- **Fluid properties** come only from the fluid-property object; the heat transfer
  coefficient belongs to the coupling's surface flux law.
- **Workarounds for PyBaMM** live only in `src/pytes/compat/`, each with the upstream issue
  and the condition for removing it.
- Docstrings follow the [NumPy style](https://numpydoc.readthedocs.io/en/latest/format.html),
  and models provide PyBaMM's `default_*` properties.

## Contributing a model

PyTES is a curated catalogue: what makes it useful is that every model shares the same
interface, so models compare like for like. A model is admitted (DESIGN D1) when it:

1. is a fixed composition of PyTES submodels (`model.submodels`), with variants chosen
   through `options`;
2. passes the conformance suite (`tests/conformance/`) with every combination of its
   options, which includes exact energy conservation;
3. uses the shared parameter layers and materials;
4. has at least one validation case, analytical or experimental;
5. belongs to a declared family; and
6. has been reviewed by a maintainer.

Open an issue first to discuss where the model fits. To try ideas before that, build a model
from submodels with `pytes.ComposedModel` (see `examples/composing_models.ipynb`).
Physics outside PyTES's scope (`DESIGN.md` D2) is best built directly with PyBaMM.

## Dependencies and reusing code

PyTES depends on PyBaMM, NumPy and SciPy. Optional features use extras: `plot` (matplotlib)
for the standard plots. Import optional dependencies only where they are used, so that
`import pytes` works without them. Before adding a dependency, open an issue: each one is a
maintenance cost for everyone.

Reusing code from elsewhere is fine if its licence allows it (PyTES is BSD 3-Clause). Say
where it comes from in the code and in the PR.

## Testing

All code needs tests. We use [pytest](https://docs.pytest.org):

```bash
uv run pytest             # the fast tests (the default)
uv run pytest -m slow     # the slow tests (e.g. the full-size mush model)
uv run pytest --nbmake examples/   # the example notebooks
uv run pytest -m "" --cov          # everything, with coverage
uv run pytest tests/models/test_packed_bed.py::test_charge_melts_the_pcm   # one test
```

The suite is organised as:

- `tests/conformance/`: the model contract, run over every model and every combination of
  its options. **Where the contract's prose and these tests disagree, the tests win.**
- `tests/models/`, `tests/submodels/`, `tests/experiments/`, `tests/toolkit/`: each part of
  PyTES.
- `tests/validation/`: comparisons with analytical solutions.

Tests are grouped by what they test, not split into unit and integration tests; the `slow`
marker separates the expensive ones.

### Writing tests

Every new feature needs its own tests, and coverage stays at 100 % of lines and branches
(`uv run pytest -m "" --cov` fails below it): if a line cannot be reached, it is probably
dead code to remove rather than test. Look for a test of something similar and start from
it. Check behaviour, not only that the code runs: compare with an exact or analytical value
where there is one, and state the tolerance and why it is what it is. Keep regular tests
fast (coarse meshes, `tests/conftest.py`), and mark long ones `@pytest.mark.slow`.

### Debugging

Isolate the problem with the smallest example that shows it. PyTES models are PyBaMM models,
so PyBaMM's tools apply: inspect `model.submodels` and `model.print_submodel_info()`, solve
with a coarse mesh, or tighten the solver tolerances to tell discretisation error from
solver error.

## Documentation

Every public class, method and function has a docstring saying, in plain terms, what it does
and what its inputs and outputs are, in the NumPy style.

The design is documented in [`docs/design/`](docs/design): `DESIGN.md` (the decisions and
their reasons), `contract.md` (what every model provides) and `findings.md` (the log of
changes and discrepancies).

### Example notebooks

Each capability has a short example notebook in [`examples/`](examples). Notebooks are
committed with their outputs, so run them before committing, and keep them short. CI
executes every notebook (`uv run pytest --nbmake examples/`) and fails if a cell raises.
Add a new notebook to the list in [`docs/examples/index.md`](docs/examples/index.md), so
that it appears on the documentation site.

### Documentation site

The documentation site is built with [Sphinx](https://www.sphinx-doc.org) from
[`docs/`](docs) and hosted on [Read the Docs](https://readthedocs.org) (configured in
`.readthedocs.yaml`). It has the API reference, generated from the docstrings
(`docs/api/`), the example notebooks, rendered from their committed outputs, the design
documents, the changelog and this guide. To build it:

```bash
uv run --group docs sphinx-build -W --keep-going docs docs/_build/html
```

and open `docs/_build/html/index.html`. Any warning fails the build, here and in CI: a
broken cross-reference, a malformed docstring, or a page missing from every table of
contents. A new public module needs an entry in one of the pages of `docs/api/`.

## Releasing

For maintainers. PyTES uses [semantic versioning](https://semver.org), with pre-releases
such as `0.1.0a1` before 1.0.

1. Make sure CI is green on `main`.
2. Set the new version in `pyproject.toml` (`version`) and in `CITATION.cff` (`version`
   and `date-released`).
3. Build the changelog: `uv run towncrier build --version <version>`. It writes the new
   section into `CHANGELOG.md` and deletes the fragments; check it and edit if needed.
4. The README is also the PyPI project page: keep its links absolute (relative links break
   there), and drop `--pre` from the installation commands at the first stable release.
5. Commit, push, and wait for CI.
6. Create a GitHub release with the tag `v<version>` (e.g. `v0.1.0a1`), mark pre-releases as
   such, and paste the new changelog section as its notes.

Publishing the release runs `.github/workflows/release.yml`: it checks that the tag matches
the version, builds the package, and attaches it to the release. Zenodo archives the release
and mints its DOI. The upload to PyPI runs only when the repository variable
`PUBLISH_TO_PYPI` is `true`, with PyPI's trusted publishing set up for the workflow.

## Infrastructure

### Installation

The environment is managed with [uv](https://docs.astral.sh/uv/), configured in
`pyproject.toml`; the lock file `uv.lock` makes it reproducible.

### Continuous integration

Every push and pull request runs, with [GitHub Actions](https://docs.github.com/en/actions)
(`.github/workflows/tests.yml`):

- the pre-commit hooks;
- the tests against the latest PyBaMM release: on Linux with every Python version PyBaMM
  supports, and on macOS and Windows with the oldest and newest;
- coverage: every test, slow ones included, reported to
  [Codecov](https://codecov.io/gh/mmsg-warwick/PyTES) (configured in `codecov.yml`);
- the example notebooks;
- the documentation site, built with warnings treated as errors;
- the tests against PyBaMM's `main` branch (non-blocking, to catch upstream changes early);
- on pull requests, the check for a changelog fragment.

Publishing a GitHub release runs `.github/workflows/release.yml` (see
[Releasing](#releasing)).

### GitHub

GitHub shows [`README.md`](README.md) on the repository's front page, links the licence in
[`LICENSE`](LICENSE), and links this file when new issues and pull requests are opened. New
issues offer the forms in [`.github/ISSUE_TEMPLATE/`](.github/ISSUE_TEMPLATE) (bug report,
feature request, new model), and new pull requests start from the checklist in
[`.github/pull_request_template.md`](.github/pull_request_template.md).

## Acknowledgements

This file is adapted from [PyBaMM's contributing guidelines](https://github.com/pybamm-team/PyBaMM/blob/main/CONTRIBUTING.md),
which were in turn copied from the excellent [PINTS GitHub repository](https://github.com/pints-team/pints).
