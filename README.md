# llmpress

**LLM-native prompt compression for source code.**

llmpress reduces the token cost of sending source code to an LLM by detecting
repeated patterns, replacing them with short aliases, and transparently
restoring the originals in the model's response.

The compression is **lossless**: the user never sees the compressed
representation.

```
Original prompt (1 000 tokens)
         │
         ▼
    llmpress compress
         │
         ├─ parse + normalise whitespace
         ├─ detect repeated token sequences
         ├─ score each candidate for token savings
         ├─ build optimal alias dictionary
         └─ rewrite source using T0, T1, T2 …
         │
         ▼
Compressed prompt (600 tokens)  ←── sent to the LLM
         │
         ▼
    LLM response (uses aliases)
         │
         ▼
    llmpress expand
         │
         ├─ replace T0 → PortfolioActivityBloc
         └─ replace T1 → Either<Failure, List<Item>>
         │
         ▼
 Readable response (original identifiers restored)
```

---

## Installation

### From source (development)

```bash
git clone <repo>
cd llmpress
python3 -m pip install -e ".[dev]"
```

> **Note:** use `python3 -m pip`, not `pip` or `pip3` directly — on macOS the
> system pip may be too old to handle `pyproject.toml`.  The quotes around
> `".[dev]"` are required to stop the shell glob-expanding `[dev]`.

### Making the CLI available

The `llmpress` script is installed to `~/Library/Python/3.9/bin` (or
equivalent for your Python version), which is not on `PATH` by default.
Add it once:

```bash
echo 'export PATH="$HOME/Library/Python/3.9/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

Verify:

```bash
llmpress --help
```

### Without modifying PATH

You can always invoke llmpress via the module runner instead:

```bash
python3 -m llmpress.cli --help
python3 -m llmpress.cli compress source.dart "Review this code."
python3 -m llmpress.cli expand dictionary.json response.txt
```

### Optional: exact token counting

By default llmpress uses a built-in heuristic tokenizer.  For exact GPT-4o
token counts install tiktoken:

```bash
python3 -m pip install tiktoken
```

Then pass `--tokenizer tiktoken` to the CLI or `TiktokenTokenizer()` in the
Python API.

---

## CLI usage

### Compress

```bash
llmpress compress source.dart "Review this code."
llmpress compress source.tsx prompt.txt
llmpress compress Service.java "Find bugs." --strip-comments --output-dir ./out
llmpress compress source.dart "Review." --tokenizer tiktoken
```

Outputs three files (next to the source, or in `--output-dir`):

| File | Description |
|---|---|
| `compressed_prompt.txt` | Send this to your LLM |
| `dictionary.json` | Needed to expand the response |
| `stats.json` | Compression statistics |

### Expand

```bash
llmpress expand dictionary.json llm_response.txt
llmpress expand dictionary.json llm_response.txt --output expanded.txt
```

### All options

```
llmpress compress --help

  SOURCE_FILE           Path to the source file to compress
  PROMPT                Prompt text, or path to a .txt file

  --output-dir PATH     Where to write output files (default: next to source)
  --tokenizer TEXT      approximate | tiktoken | tiktoken:<model>  [default: auto]
  --strip-comments      Remove // and /* */ comments before compressing
  --strip-docs          Remove doc comments (/** */ or ///)
  --min-frequency INT   Minimum phrase occurrences to consider  [default: 2]
  --max-phrase-words INT  Max whitespace tokens per alias  [default: 6]
  --stats-only          Print statistics without writing files
  --quiet / -q          Suppress statistics output
```

---

## Python API

```python
from llmpress import Compressor, Decompressor

# Compress
comp = Compressor()
result = comp.compress(source_code, "Review this code for issues.")

print(result.compressed_prompt)         # send this to your LLM
print(f"Saved: {result.stats.net_token_savings} tokens")

# Expand the LLM response
dec = Decompressor()
readable = dec.expand(llm_response, result.dictionary)
```

### Custom tokenizer

```python
from llmpress import Compressor
from llmpress.tokenizers import ApproximateTokenizer, TiktokenTokenizer

# Heuristic (no extra dependencies)
comp = Compressor(tokenizer=ApproximateTokenizer())

# Exact GPT-4o counts (requires: pip install tiktoken)
comp = Compressor(tokenizer=TiktokenTokenizer("gpt-4o"))
```

### Options

| Option | Default | Description |
|---|---|---|
| `tokenizer` | `"auto"` | `"approximate"` / `"tiktoken"` / `"tiktoken:<model>"` |
| `strip_comments` | `False` | Remove `//` and `/* */` comments |
| `strip_docs` | `False` | Remove doc comments |
| `language` | `"auto"` | Hint for the comment stripper |
| `min_frequency` | `2` | Minimum occurrences to consider a phrase |
| `max_phrase_words` | `6` | Maximum whitespace-separated tokens per alias |

---

## How it works

### 1. Whitespace normalisation

Collapse redundant whitespace, normalise line endings, strip trailing spaces.
Code structure is preserved exactly.

### 2. Phrase detection (two passes)

**Identifier pass** — find every long identifier (≥ 5 chars) that appears
more than once. CamelCase names like `PortfolioActivityBloc` are especially
profitable: the BPE tokeniser splits them into subwords
(`Portfolio` + `Activity` + `Bloc` = 3 tokens), so replacing them with a
short alias saves tokens per occurrence.

**N-gram pass** — find repeated whitespace-separated sequences of 2–6 tokens.
Patterns like `emit(PortfolioActivityLoading())` or
`result.fold( (failure) =>` appear verbatim in Bloc boilerplate.

### 3. Savings scoring

```
net_saving = (phrase_tokens − alias_tokens) × frequency − dict_entry_tokens
```

Only candidates with `net_saving > 0` are kept.

### 4. Alias assignment

Candidates are sorted by savings (descending) and assigned sequential aliases
`T0`, `T1`, `T2`, …  A greedy source-simulation pass eliminates overlapping
phrases: after each phrase is committed, subsequent candidates are only accepted
if they still appear at the required frequency in the already-compressed source.

### 5. Prompt construction

```
[LLMPRESS:DICT]
T0=PortfolioActivityBloc
T1=Either<PortfolioFailure, List<PortfolioItem>>
[END:DICT]

[LLMPRESS:RULES]
- Aliases T0, T1, ... represent EXISTING symbols in the source only.
- DO NOT invent new aliases or use Tn notation for any new code you write.
- New identifiers must follow the naming conventions visible in the source.
[END:RULES]

[LLMPRESS:TASK]
Review this code for issues.
[END:TASK]

[LLMPRESS:SOURCE]
class T0 extends Bloc<PortfolioEvent, PortfolioState> {
  ...
}
[END:SOURCE]
```

### 6. Response expansion

The postprocessor replaces every alias with its original text using
word-boundary-aware regex, processing longer aliases first to avoid
`T10` being treated as `T1` + `0`.

---

## When compression helps most

- **Large files** (> 300 lines): more repetition, higher savings
- **Boilerplate-heavy code**: BLoC, Repository, CRUD, Spring, ASP.NET
- **Long class names**: `PortfolioActivityBloc`, `CustomerOrderRepository`
- **Repeated type signatures**: `Either<Failure, List<Item>>`, `Future<ApiResponse<T>>`

---

## Architecture

```
src/llmpress/
├── __init__.py              # Public API: Compressor, Decompressor
├── cli.py                   # Click CLI: compress / expand / llmpress
├── core/
│   ├── models.py            # PhraseCandidate, Dictionary, CompressionStats, …
│   ├── compressor.py        # Pipeline orchestrator
│   └── decompressor.py      # Alias expansion
├── phases/
│   ├── base.py              # Phase ABC (extensible pipeline step)
│   ├── whitespace.py        # WhitespaceNormalizer
│   ├── comment_stripper.py  # Language-aware comment removal
│   ├── phrase_detector.py   # Two-pass detection + savings scoring
│   ├── dict_builder.py      # Greedy alias assignment with overlap elimination
│   └── rewriter.py          # Rewriter + Expander
└── tokenizers/
    ├── base.py              # Tokenizer ABC (pluggable)
    ├── approximate.py       # Heuristic CamelCase-aware counter (no deps)
    └── tiktoken_adapter.py  # Exact BPE token counter (optional)
```

### Extension points

| What to extend | Where |
|---|---|
| New tokenizer | Subclass `tokenizers.base.Tokenizer` |
| New compression pass | Subclass `phases.base.Phase`, add to `Compressor.__init__` |
| Language comment stripping | Extend `CommentStripper` |
| AST-aware phrase detection | Replace or extend `PhraseDetector` |
| Project-wide dictionaries | Pre-build a `Dictionary`, pass to `DictionaryBuilder` |

---

## Development

```bash
git clone <repo>
cd llmpress
python3 -m pip install -e ".[dev]"
python3 -m pytest tests/ -q
python3 -m pytest tests/ --cov=src/llmpress --cov-report=term-missing
```

---

## Roadmap

- AST-aware compression (language-specific parsers)
- Project-wide shared dictionaries
- Tokenizer-aware alias selection (guaranteed single-token aliases)
- Semantic phrase detection via embeddings
- VS Code extension
- Language plugins: Kotlin, Swift, Go, Ruby

---

## License

MIT
