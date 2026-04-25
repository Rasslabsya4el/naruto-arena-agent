from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings(
    "ignore",
    message="jsonschema.RefResolver is deprecated",
    category=DeprecationWarning,
)

from jsonschema import RefResolver
from jsonschema.validators import validator_for


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"
FIXTURE_DIR = SCHEMA_DIR / "fixtures"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_schema_store(schema_paths: list[Path]) -> tuple[dict[str, dict], dict[str, dict]]:
    schemas: dict[str, dict] = {}
    store: dict[str, dict] = {}

    for schema_path in schema_paths:
        schema = load_json(schema_path)
        schemas[schema_path.name] = schema
        store[schema_path.resolve().as_uri()] = schema
        store[schema_path.name] = schema
        store[f"./{schema_path.name}"] = schema

    return schemas, store


def format_error_path(error) -> str:
    if not error.absolute_path:
        return "<root>"
    return ".".join(str(part) for part in error.absolute_path)


def validate_fixture(
    fixture_path: Path,
    schema_path: Path,
    schema: dict,
    store: dict[str, dict],
) -> list[str]:
    instance = load_json(fixture_path)
    validator_cls = validator_for(schema)
    resolver = RefResolver(
        base_uri=schema_path.resolve().as_uri(),
        referrer=schema,
        store=store,
    )
    validator = validator_cls(schema, resolver=resolver)
    errors = sorted(
        validator.iter_errors(instance),
        key=lambda error: (
            format_error_path(error),
            error.message,
        ),
    )

    return [
        f"{fixture_path.name}: {format_error_path(error)}: {error.message}"
        for error in errors
    ]


def main() -> int:
    schema_paths = sorted(SCHEMA_DIR.glob("*.schema.json"))
    fixture_paths = sorted(FIXTURE_DIR.glob("*.sample.json"))

    if not schema_paths:
        print("No schema files found.", file=sys.stderr)
        return 1
    if not fixture_paths:
        print("No fixture files found.", file=sys.stderr)
        return 1

    schemas, store = build_schema_store(schema_paths)
    failures: list[str] = []

    for schema_path in schema_paths:
        schema = schemas[schema_path.name]
        validator_cls = validator_for(schema)
        try:
            validator_cls.check_schema(schema)
        except Exception as exc:  # pragma: no cover - explicit failure reporting
            failures.append(f"{schema_path.name}: schema check failed: {exc}")

    for fixture_path in fixture_paths:
        schema_name = fixture_path.name.replace(".sample.json", ".schema.json")
        schema = schemas.get(schema_name)
        if schema is None:
            failures.append(f"{fixture_path.name}: missing matching schema {schema_name}")
            continue

        schema_path = SCHEMA_DIR / schema_name
        try:
            failures.extend(validate_fixture(fixture_path, schema_path, schema, store))
        except Exception as exc:  # pragma: no cover - explicit failure reporting
            failures.append(f"{fixture_path.name}: validation raised {type(exc).__name__}: {exc}")

    if failures:
        print("Schema validation failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print(
        f"Validated {len(schema_paths)} schema files and {len(fixture_paths)} fixture files successfully."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
