# 1. Install dependencies (including dev/test deps)
cd /home/ed/projects/stellcasp
pip install -e ".[dev]"

# 2. Run all tests
pytest tests/ -v

# 3. Run only unit tests (no external services)
pytest tests/test_unit.py -v

# 4. Run only integration tests (mocked Neo4j + nargo)
pytest tests/integration/test_graph_to_zk.py -v -m integration

# 5. Run only endpoint tests
pytest tests/test_endpoints.py -v

# 6. Run a specific test class
pytest tests/test_endpoints.py::TestEntityRoutes -v

# 7. Run with coverage
pytest tests/ --cov=zkkyc --cov-report=term-missing

# 8. Lint
ruff check zkkyc tests

# 9. Type check
mypy zkkyc