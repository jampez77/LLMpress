"""
llmpress CLI
============

Entry points:
  compress  <source_file> <prompt_or_file> [options]
  expand    <directory>  [options]
  llmpress  compress|expand  …  (same as above via sub-commands)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .core import Compressor, Decompressor
from .tokenizers import get_tokenizer

console = Console(stderr=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_prompt(prompt_or_file: str) -> str:
    """Accept either a literal prompt string or a path to a .txt file."""
    p = Path(prompt_or_file)
    if p.exists() and p.is_file():
        return p.read_text(encoding="utf-8").strip()
    return prompt_or_file


_SOURCE_EXTENSIONS = {
    ".dart", ".ts", ".tsx", ".js", ".jsx", ".py", ".java", ".cs",
    ".kt", ".swift", ".go", ".rs", ".rb", ".cpp", ".c", ".h",
}


def _resolve_directory(directory: Path) -> tuple[Path, str]:
    """Given a directory, find source_file and prompt.

    Looks for prompt.txt and the first source file with a recognised extension.
    Raises UsageError if either cannot be found.
    """
    prompt_path = directory / "prompt.txt"
    if not prompt_path.exists():
        raise click.UsageError(
            f"No prompt.txt found in {directory}. "
            "Create prompt.txt or pass the prompt text directly."
        )

    candidates = [
        f for f in sorted(directory.iterdir())
        if f.is_file() and f.suffix.lower() in _SOURCE_EXTENSIONS
    ]
    if not candidates:
        raise click.UsageError(
            f"No recognised source file found in {directory}. "
            f"Supported extensions: {', '.join(sorted(_SOURCE_EXTENSIONS))}"
        )
    if len(candidates) > 1:
        names = ", ".join(f.name for f in candidates)
        raise click.UsageError(
            f"Multiple source files found in {directory}: {names}. "
            "Pass the source file path explicitly."
        )

    return candidates[0], prompt_path.read_text(encoding="utf-8").strip()


def _detect_language(source_path: Path) -> str:
    return source_path.suffix.lstrip(".").lower() or "auto"


def _print_stats(stats_dict: dict) -> None:
    table = Table(title="Compression statistics", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="dim", min_width=28)
    table.add_column("Value", justify="right")

    t = stats_dict
    orig = t["original_tokens"]
    # compressed_tokens already includes prompt + compressed_source + dictionary
    comp = t["compressed_tokens"]
    saved = t["net_token_savings"]
    pct = 100 * saved / orig if orig > 0 else 0

    table.add_row("Tokenizer", t["tokenizer"])
    table.add_row("Original tokens (prompt + source)", str(orig))
    table.add_row("Total compressed (prompt + source + dict)", str(comp))
    table.add_row("  Thereof dictionary", str(t["dictionary_tokens"]))
    table.add_row("Net token savings", f"[green]{saved}[/green]")
    table.add_row("Compression ratio", f"{t['compression_ratio']:.1%}")
    table.add_row("Saving %", f"[bold green]{pct:.1f}%[/bold green]")
    table.add_row("Phrases detected", str(t["phrases_detected"]))
    table.add_row("Phrases compressed", str(t["phrases_compressed"]))

    console.print(table)

    if t.get("top_phrases"):
        phrase_table = Table(title="Top aliases by token saving", show_header=True, header_style="bold magenta")
        phrase_table.add_column("Phrase (truncated)", min_width=40)
        phrase_table.add_column("Freq", justify="right")
        phrase_table.add_column("Tokens", justify="right")
        phrase_table.add_column("Saving", justify="right")
        for row in t["top_phrases"][:10]:
            phrase_table.add_row(
                row["phrase"][:60],
                str(row["frequency"]),
                str(row["phrase_tokens"]),
                str(row["net_saving"]),
            )
        console.print(phrase_table)


# ---------------------------------------------------------------------------
# compress
# ---------------------------------------------------------------------------

@click.command("compress")
@click.argument("source_file", type=click.Path(exists=True, path_type=Path))
@click.argument("prompt", type=str, default="", required=False)
@click.option("--output-dir", "-o", type=click.Path(file_okay=False, path_type=Path),
              default=None, help="Directory for output files (default: next to source).")
@click.option("--tokenizer", "-t", default="auto",
              help="Tokenizer: auto | approximate | tiktoken | tiktoken:<model>")
@click.option("--strip-comments", is_flag=True, default=False,
              help="Remove comments before compression.")
@click.option("--strip-docs", is_flag=True, default=False,
              help="Remove doc comments (/** */ or ///) before compression.")
@click.option("--min-frequency", default=2, show_default=True,
              help="Minimum phrase occurrences to consider for compression.")
@click.option("--max-phrase-words", default=8, show_default=True,
              help="Maximum whitespace-separated tokens per alias phrase.")
@click.option("--stats-only", is_flag=True, default=False,
              help="Print statistics without writing output files.")
@click.option("--quiet", "-q", is_flag=True, default=False,
              help="Suppress statistics output.")
def compress(
    source_file: Path,
    prompt: str,
    output_dir: Path | None,
    tokenizer: str,
    strip_comments: bool,
    strip_docs: bool,
    min_frequency: int,
    max_phrase_words: int,
    stats_only: bool,
    quiet: bool,
) -> None:
    """
    Compress SOURCE_FILE using PROMPT (or a path to a .txt file) and write:

    \b
      compressed_prompt.txt  — send this to your LLM
      dictionary.json        — needed to expand the response
      stats.json             — compression statistics

    SOURCE_FILE may also be a directory containing exactly one source file
    and a prompt.txt — llmpress will find them automatically.
    """
    if source_file.is_dir():
        source_file, prompt_text = _resolve_directory(source_file)
    else:
        if not prompt:
            raise click.UsageError("PROMPT is required when SOURCE_FILE is a file.")
        prompt_text = _resolve_prompt(prompt)
    source_text = source_file.read_text(encoding="utf-8")
    language = _detect_language(source_file)

    tok = get_tokenizer(tokenizer)
    comp = Compressor(
        tokenizer=tok,
        strip_comments=strip_comments,
        strip_docs=strip_docs,
        language=language,
        min_frequency=min_frequency,
        max_phrase_words=max_phrase_words,
    )

    if not quiet:
        console.print(f"[bold]llmpress compress[/bold]  {source_file.name}  [{tok.name()}]")

    result = comp.compress(source=source_text, prompt=prompt_text)

    if not quiet:
        _print_stats(result.stats.to_dict())

    if stats_only:
        return

    out_dir = output_dir or source_file.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    prompt_out = out_dir / "compressed_prompt.txt"
    dict_out = out_dir / "dictionary.json"
    stats_out = out_dir / "stats.json"

    prompt_out.write_text(result.compressed_prompt, encoding="utf-8")
    dict_out.write_text(
        json.dumps(result.dictionary.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    stats_out.write_text(
        json.dumps(result.stats.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    if not quiet:
        console.print(Panel(
            f"[green]✓[/green] [bold]{prompt_out}[/bold]\n"
            f"[green]✓[/green] [bold]{dict_out}[/bold]\n"
            f"[green]✓[/green] [bold]{stats_out}[/bold]",
            title="Output files",
            expand=False,
        ))


# ---------------------------------------------------------------------------
# expand
# ---------------------------------------------------------------------------

@click.command("expand")
@click.argument("directory", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--quiet", "-q", is_flag=True, default=False)
def expand(
    directory: Path,
    quiet: bool,
) -> None:
    """
    Expand aliases in DIRECTORY using its dictionary.json.

    Expects: dictionary.json, compressed_prompt.txt.
    Produces: expanded_prompt.txt.
    """
    dictionary_file = directory / "dictionary.json"
    prompt_file = directory / "compressed_prompt.txt"

    if not dictionary_file.exists():
        raise click.ClickException(f"dictionary.json not found in {directory}")
    if not prompt_file.exists():
        raise click.ClickException(f"compressed_prompt.txt not found in {directory}")

    if not quiet:
        console.print(f"[bold]llmpress expand[/bold]  {directory}")

    decomp = Decompressor()

    out_prompt = directory / "expanded_prompt.txt"
    out_prompt.write_text(decomp.expand_file(prompt_file, dictionary_file), encoding="utf-8")
    if not quiet:
        console.print(f"[green]✓[/green] {out_prompt}")


# ---------------------------------------------------------------------------
# run  (compress → LLM → expand → print)
# ---------------------------------------------------------------------------

@click.command("run")
@click.argument("source_file", type=click.Path(exists=True, path_type=Path))
@click.argument("prompt", type=str, default="", required=False)
@click.option("--provider", "-p", default="anthropic", show_default=True,
              type=click.Choice(["anthropic", "openai"], case_sensitive=False),
              help="LLM provider.")
@click.option("--model", "-m", default=None,
              help="Model name (default: claude-sonnet-4-6 for anthropic, gpt-4o for openai).")
@click.option("--max-tokens", default=4096, show_default=True,
              help="Maximum tokens in the LLM response.")
@click.option("--output-dir", "-o", type=click.Path(file_okay=False, path_type=Path),
              default=None, help="Save intermediate files here (compressed_prompt.txt, dictionary.json, stats.json, response.txt).")
@click.option("--tokenizer", "-t", default="auto",
              help="Tokenizer: auto | approximate | tiktoken | tiktoken:<model>")
@click.option("--strip-comments", is_flag=True, default=False)
@click.option("--strip-docs", is_flag=True, default=False)
@click.option("--min-frequency", default=2, show_default=True)
@click.option("--max-phrase-words", default=8, show_default=True)
@click.option("--quiet", "-q", is_flag=True, default=False,
              help="Suppress compression statistics.")
def run(
    source_file: Path,
    prompt: str,
    provider: str,
    model: str | None,
    max_tokens: int,
    output_dir: Path | None,
    tokenizer: str,
    strip_comments: bool,
    strip_docs: bool,
    min_frequency: int,
    max_phrase_words: int,
    quiet: bool,
) -> None:
    """
    Compress SOURCE_FILE, send to an LLM, expand the response, and print it.

    \b
    Reads ANTHROPIC_API_KEY from the environment.
    SOURCE_FILE may be a directory containing a source file and prompt.txt.
    """
    import json as _json

    # --- resolve source + prompt ---
    if source_file.is_dir():
        source_file, prompt_text = _resolve_directory(source_file)
    else:
        if not prompt:
            raise click.UsageError("PROMPT is required when SOURCE_FILE is a file.")
        prompt_text = _resolve_prompt(prompt)
    source_text = source_file.read_text(encoding="utf-8")
    language = _detect_language(source_file)

    tok = get_tokenizer(tokenizer)
    comp = Compressor(
        tokenizer=tok,
        strip_comments=strip_comments,
        strip_docs=strip_docs,
        language=language,
        min_frequency=min_frequency,
        max_phrase_words=max_phrase_words,
    )

    # --- resolve model default per provider ---
    _DEFAULT_MODELS = {"anthropic": "claude-sonnet-4-6", "openai": "gpt-4o"}
    resolved_model = model or _DEFAULT_MODELS[provider]

    # --- compress ---
    if not quiet:
        console.print(f"[bold]llmpress run[/bold]  {source_file.name}  [{tok.name()}]  → [cyan]{provider}/{resolved_model}[/cyan]")

    result = comp.compress(source=source_text, prompt=prompt_text)

    if not quiet:
        _print_stats(result.stats.to_dict())

    # --- call LLM ---
    from .providers import AnthropicProvider, OpenAIProvider
    try:
        llm = (
            AnthropicProvider(model=resolved_model, max_tokens=max_tokens)
            if provider == "anthropic"
            else OpenAIProvider(model=resolved_model, max_tokens=max_tokens)
        )
        if not quiet:
            console.print("[dim]Sending to LLM…[/dim]")
        raw_response = llm.complete(result.compressed_prompt)
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    # --- expand ---
    from .core import Decompressor
    decomp = Decompressor()
    expanded = decomp.expand(raw_response, result.dictionary)

    # --- save intermediates if requested ---
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "compressed_prompt.txt").write_text(result.compressed_prompt, encoding="utf-8")
        (output_dir / "dictionary.json").write_text(
            _json.dumps(result.dictionary.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (output_dir / "stats.json").write_text(
            _json.dumps(result.stats.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (output_dir / "response.txt").write_text(expanded, encoding="utf-8")
        if not quiet:
            console.print(f"[green]✓[/green] Files saved to [bold]{output_dir}[/bold]")

    # --- print expanded response ---
    click.echo(expanded)


# ---------------------------------------------------------------------------
# Top-level group
# ---------------------------------------------------------------------------

@click.group()
def main() -> None:
    """llmpress — LLM-native prompt compression for source code."""


main.add_command(compress)
main.add_command(expand)
main.add_command(run)

if __name__ == "__main__":
    main()
