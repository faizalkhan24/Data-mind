# Contributing to DataMind

Thank you for your interest in contributing to **DataMind**! 

DataMind is an enterprise-grade predictive intelligence and failure prevention platform. To maintain software reliability and prevent breaking changes from entering production, this repository follows the standard **Fork & Pull Request Open-Source Workflow**.

---

## 🔒 Branch Protection & Access Model

> [!IMPORTANT]
> **The `main` branch is strictly protected.** 
> Direct pushes (`git push origin main`) are disabled for all contributors. All modifications must arrive through Pull Requests that pass automated CI testing and receive maintainer review.

### Why We Use the Fork & Pull Request Model
* **Safety:** No external contributor can accidentally or intentionally push broken code, delete tags, or rewrite Git commit history on `main`.
* **Isolated Development:** Contributors work in their own independent forks and branches without requiring write access to this upstream repository.
* **Automated Verification:** GitHub Actions CI automatically runs the complete 98-test suite and code linter on every Pull Request before any code can be merged.

---

## 🛠️ Step-by-Step Contribution Workflow

```
[Upstream: faizalkhan24/Data-mind]
          │
          │ (1. Fork on GitHub)
          ▼
[Contributor's Fork: username/Data-mind]
          │
          │ (2. git clone & git checkout -b feat/your-feature)
          ▼
[Local Feature Branch]
          │
          │ (3. Write Code & Run All 98 Tests)
          ▼
[Push to Fork: git push origin feat/your-feature]
          │
          │ (4. Submit Pull Request)
          ▼
[GitHub Actions CI: 100% Green] ──► [Maintainer Review & Merge into main]
```

### Step 1: Fork the Repository
1. Navigate to [`https://github.com/faizalkhan24/Data-mind`](https://github.com/faizalkhan24/Data-mind).
2. Click the **Fork** button in the top-right corner.
3. This creates an isolated copy of the repository under your personal GitHub account.

### Step 2: Clone Your Fork Locally
```bash
git clone https://github.com/<YOUR-GITHUB-USERNAME>/Data-mind.git
cd Data-mind
```

Configure upstream remote tracking to keep your fork updated:
```bash
git remote add upstream https://github.com/faizalkhan24/Data-mind.git
git fetch upstream
```

### Step 3: Create a Dedicated Feature Branch
Never make changes directly on your fork's `main` branch. Create a descriptive topic branch:
```bash
git checkout -b feat/add-sensor-anomaly-filter
```
Branch naming conventions:
* `feat/` — New feature or capability
* `fix/` — Bug fix or error resolution
* `docs/` — Documentation updates
* `perf/` — Performance optimization
* `test/` — Adding or refactoring tests

### Step 4: Set Up the Development Environment
DataMind strictly requires **Python 3.11.x**:
```powershell
# Windows
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Linux / macOS
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 5: Implement Changes & Adhere to Coding Standards
* **Type Annotations:** All functions and methods must declare explicit type hints.
* **Docstrings:** Public modules, classes, and functions must include Google-style docstrings.
* **Zero Data Leakage:** Any temporal feature calculation must strictly respect the causal boundary (information at time $t$ uses only observations $\le t$).
* **Sub-5ms SLA:** Any inference or prediction API modifications must not breach the $5\text{ ms}$ latency budget.

### Step 6: Verify with the Automated Test Suite
Before committing, verify that all **98 automated tests** pass with 100% success rate:
```powershell
# Windows
$env:PYTHONPATH = "."
python -m unittest discover -s tests -t . -v

# Linux / macOS
PYTHONPATH=. python3 -m unittest discover -s tests -t . -v
```

### Step 7: Commit Changes Using Conventional Commits
```bash
git add .
git commit -m "feat(ingestion): add sliding window exponential moving average"
```
Format: `<type>(<scope>): <short description>`

### Step 8: Push to Your Fork & Open a Pull Request
```bash
git push origin feat/add-sensor-anomaly-filter
```
1. Open your fork on GitHub.
2. Click **Compare & pull request**.
3. Fill out the PR template describing the motivation, changes made, and test verification.
4. Ensure all automated GitHub Actions CI checks complete successfully.
5. The repository maintainer (@faizalkhan24) will review your PR, request changes if necessary, and merge it into `main`.

---

## 📋 Pull Request Review Criteria

Every PR will be evaluated against the following checklist:
1. **CI Green:** All GitHub Actions jobs (Linting, Test Suite, Docker build validation) pass without failures.
2. **Test Coverage:** Any new feature or bugfix must include corresponding automated unit tests in `tests/`.
3. **No Breaking Changes:** APIs must preserve backward compatibility or increment the version appropriately.
4. **Documentation:** Any changes to APIs, configuration variables, or architecture must be reflected in [`docs/USER_MANUAL.md`](docs/USER_MANUAL.md) and [`README.md`](README.md).

---

## 💡 Reporting Issues

* **Bug Reports:** Open an issue with reproduction steps, expected vs. actual behavior, Python version, and system environment.
* **Feature Requests:** Open an issue describing the proposed feature, real-world IoT use case, and potential implementation approach.

Thank you for helping make DataMind even better!
