"""
Benchmark tests: verify meaningful compression on realistic fixture files.

These tests are slow and require the fixture files in tests/fixtures/.
They run with --benchmark flag or when run explicitly.  In CI they are
skipped if the fixture file is missing.
"""
from __future__ import annotations

import pytest

from llmpress import Compressor, Decompressor
from llmpress.tokenizers import ApproximateTokenizer

from .conftest import fixture_exists, load_fixture


def compress_fixture(path: str, prompt: str = "Review this code."):
    comp = Compressor(tokenizer=ApproximateTokenizer())
    source = load_fixture(path)
    return comp.compress(source, prompt)


def check_fixture(path: str, prompt: str = "Review this code.", min_saving: int = 0):
    if not fixture_exists(path):
        pytest.skip(f"Fixture not found: {path}")
    result = compress_fixture(path, prompt)
    assert result.stats.net_token_savings >= min_saving, (
        f"Expected >= {min_saving} token savings for {path}, "
        f"got {result.stats.net_token_savings}"
    )
    # Roundtrip
    dec = Decompressor()
    restored = dec.expand(result.compressed_source, result.dictionary)
    comp = Compressor(tokenizer=ApproximateTokenizer())
    normalised = comp._whitespace.apply(load_fixture(path))
    assert restored == normalised, f"Roundtrip failed for {path}"
    return result


# ── Flutter ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("fixture", [
    "flutter/bloc_widget.dart",
    "flutter/riverpod_page.dart",
    "flutter/freezed_model.dart",
    "flutter/repository.dart",
])
def test_flutter_roundtrip(fixture):
    check_fixture(fixture)


@pytest.mark.parametrize("fixture,prompt", [
    ("flutter/bloc_widget.dart", "Review this code."),
    ("flutter/bloc_widget.dart", "Find bugs."),
    ("flutter/bloc_widget.dart", "Improve performance."),
    ("flutter/bloc_widget.dart", "Write unit tests."),
])
def test_flutter_prompts(fixture, prompt):
    if not fixture_exists(fixture):
        pytest.skip(f"Fixture not found: {fixture}")
    result = compress_fixture(fixture, prompt)
    assert prompt in result.compressed_prompt


# ── Dart ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("fixture", [
    "dart/generics.dart",
    "dart/extensions.dart",
])
def test_dart_roundtrip(fixture):
    check_fixture(fixture)


# ── TypeScript ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("fixture", [
    "typescript/react_component.tsx",
    "typescript/service.ts",
])
def test_typescript_roundtrip(fixture):
    check_fixture(fixture)


# ── Java ──────────────────────────────────────────────────────────────────

def test_java_roundtrip():
    check_fixture("java/spring_repository.java")


# ── C# ────────────────────────────────────────────────────────────────────

def test_csharp_roundtrip():
    check_fixture("csharp/aspnet_controller.cs")


# ── Python ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("fixture", [
    "python/fastapi_app.py",
    "python/dataclasses_example.py",
])
def test_python_roundtrip(fixture):
    check_fixture(fixture)


# ── Summary ───────────────────────────────────────────────────────────────

def test_benchmark_summary(capsys):
    """Print a summary table of savings across all available fixtures."""
    fixtures = [
        ("flutter/bloc_widget.dart", "Review."),
        ("flutter/repository.dart", "Review."),
        ("typescript/react_component.tsx", "Review."),
        ("java/spring_repository.java", "Review."),
        ("csharp/aspnet_controller.cs", "Review."),
        ("python/fastapi_app.py", "Review."),
    ]
    print("\n\nBenchmark summary")
    print("-" * 70)
    print(f"{'Fixture':<40} {'Orig':>6} {'Comp':>6} {'Saved':>6} {'Ratio':>7}")
    print("-" * 70)

    any_ran = False
    for path, prompt in fixtures:
        if not fixture_exists(path):
            continue
        result = compress_fixture(path, prompt)
        s = result.stats
        print(
            f"{path:<40} {s.original_tokens:>6} "
            f"{s.compressed_tokens:>6} {s.net_token_savings:>6} "
            f"{1 - s.compression_ratio:>6.1%}"
        )
        any_ran = True

    print("-" * 70)

    if not any_ran:
        pytest.skip("No fixture files available for benchmark")
