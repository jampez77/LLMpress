"""
Roundtrip tests: compress source → expand compressed source → get original back.

These are the most important correctness tests.  They verify the system is
truly lossless: any text that goes in must come out unchanged after
compress→expand.
"""
from __future__ import annotations

import pytest

from llmpress import Compressor, Decompressor
from llmpress.tokenizers import ApproximateTokenizer


def roundtrip(source: str, prompt: str = "Review.") -> str:
    """Compress *source* then expand the compressed version back."""
    comp = Compressor(tokenizer=ApproximateTokenizer())
    result = comp.compress(source, prompt)
    dec = Decompressor()
    return dec.expand(result.compressed_source, result.dictionary)


def assert_roundtrip(source: str, prompt: str = "Review."):
    restored = roundtrip(source, prompt)
    # Normalise for comparison (compressor may have normalised whitespace)
    comp = Compressor(tokenizer=ApproximateTokenizer())
    normalised = comp._whitespace.apply(source)
    assert restored == normalised, (
        f"Roundtrip failed.\n"
        f"Expected:\n{normalised[:300]}\n"
        f"Got:\n{restored[:300]}"
    )


# ── Generic roundtrip ─────────────────────────────────────────────────────

def test_roundtrip_empty():
    restored = roundtrip("")
    assert restored == ""


def test_roundtrip_no_repetition():
    source = "int x = 42; String name = 'hello';"
    assert_roundtrip(source)


def test_roundtrip_with_numbers():
    source = "final int count = 100; final double ratio = 0.75;"
    assert_roundtrip(source)


# ── Dart / Flutter ────────────────────────────────────────────────────────

def test_roundtrip_dart_bloc(sample_dart_bloc):
    assert_roundtrip(sample_dart_bloc)


def test_roundtrip_dart_with_generics():
    source = """\
Future<Either<Failure, List<PortfolioItem>>> fetchItems(String userId) async {
  try {
    final items = await _repository.fetchItems(userId);
    return Right(items);
  } on NetworkException catch (e) {
    return Left(NetworkFailure(e.message));
  } on CacheException catch (e) {
    return Left(CacheFailure(e.message));
  }
}

Future<Either<Failure, PortfolioItem>> fetchItem(String itemId) async {
  try {
    final item = await _repository.fetchItem(itemId);
    return Right(item);
  } on NetworkException catch (e) {
    return Left(NetworkFailure(e.message));
  } on CacheException catch (e) {
    return Left(CacheFailure(e.message));
  }
}"""
    assert_roundtrip(source)


def test_roundtrip_dart_freezed():
    source = """\
@freezed
class UserProfile with _$UserProfile {
  const factory UserProfile({
    required String id,
    required String name,
    required String email,
    String? avatarUrl,
    @Default([]) List<String> roles,
  }) = _UserProfile;

  factory UserProfile.fromJson(Map<String, dynamic> json) =>
      _$UserProfileFromJson(json);
}

@freezed
class UserSettings with _$UserSettings {
  const factory UserSettings({
    @Default(true) bool notificationsEnabled,
    @Default('en') String locale,
    @Default('light') String theme,
  }) = _UserSettings;

  factory UserSettings.fromJson(Map<String, dynamic> json) =>
      _$UserSettingsFromJson(json);
}"""
    assert_roundtrip(source)


# ── TypeScript / React ────────────────────────────────────────────────────

def test_roundtrip_typescript(sample_typescript):
    assert_roundtrip(sample_typescript)


def test_roundtrip_typescript_service():
    source = """\
export class ApiService {
  private readonly baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  async get<T>(path: string): Promise<ApiResponse<T>> {
    const response = await fetch(`${this.baseUrl}${path}`);
    if (!response.ok) throw new ApiError(response.status, response.statusText);
    const data: T = await response.json();
    return { data, status: response.status, ok: true };
  }

  async post<T>(path: string, body: unknown): Promise<ApiResponse<T>> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!response.ok) throw new ApiError(response.status, response.statusText);
    const data: T = await response.json();
    return { data, status: response.status, ok: true };
  }

  async put<T>(path: string, body: unknown): Promise<ApiResponse<T>> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!response.ok) throw new ApiError(response.status, response.statusText);
    const data: T = await response.json();
    return { data, status: response.status, ok: true };
  }
}"""
    assert_roundtrip(source)


# ── Python ────────────────────────────────────────────────────────────────

def test_roundtrip_python_fastapi():
    source = """\
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List

app = FastAPI()

@app.get('/users/{user_id}', response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')
    return user

@app.post('/users/', response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Email already registered')
    db_user = User(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.put('/users/{user_id}', response_model=UserResponse)
async def update_user(user_id: int, user: UserUpdate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')
    for key, value in user.dict(exclude_unset=True).items():
        setattr(db_user, key, value)
    db.commit()
    db.refresh(db_user)
    return db_user"""
    assert_roundtrip(source)


# ── LLM response expansion ────────────────────────────────────────────────

def test_expand_llm_response_with_aliases():
    """The LLM response uses aliases; expansion must restore originals."""
    comp = Compressor(tokenizer=ApproximateTokenizer())
    source = """\
class UserRepository {
  Future<Either<Failure, User>> getUser(String id);
  Future<Either<Failure, User>> updateUser(User user);
  Future<Either<Failure, bool>> deleteUser(String id);
}
class UserRepositoryImpl implements UserRepository {
  final UserDataSource _dataSource;
  UserRepositoryImpl(UserDataSource dataSource) : _dataSource = dataSource;
  Future<Either<Failure, User>> getUser(String id) async {
    try {
      final user = await _dataSource.fetchUser(id);
      return Right(user);
    } catch (e) {
      return Left(ServerFailure(e.toString()));
    }
  }
  Future<Either<Failure, User>> updateUser(User user) async {
    try {
      final updated = await _dataSource.updateUser(user);
      return Right(updated);
    } catch (e) {
      return Left(ServerFailure(e.toString()));
    }
  }
  Future<Either<Failure, bool>> deleteUser(String id) async {
    try {
      await _dataSource.deleteUser(id);
      return Right(true);
    } catch (e) {
      return Left(ServerFailure(e.toString()));
    }
  }
}"""
    result = comp.compress(source, "Review.")
    dec = Decompressor()

    # Build an LLM response that uses some aliases and also introduces new names
    alias_map = {e.alias: e.original for e in result.dictionary.entries}
    # Construct a response using the first 2 aliases (if they exist)
    aliases_used = list(alias_map.keys())[:2]
    llm_response = "The code looks good. "
    for a in aliases_used:
        llm_response += f"{a} is used correctly. "
    llm_response += "Consider adding UserRepositoryCache as a new abstraction."

    expanded = dec.expand(llm_response, result.dictionary)

    # All used aliases must be expanded
    for a in aliases_used:
        assert a not in expanded or alias_map[a] in expanded

    # New human-readable names pass through unchanged
    assert "UserRepositoryCache" in expanded


def test_prompts_all_succeed(sample_dart_bloc):
    """All standard prompts must produce a valid compressed prompt."""
    prompts = [
        "Review this code.",
        "Find bugs.",
        "Improve performance.",
        "Refactor.",
        "Add caching.",
        "Write unit tests.",
        "Convert to async.",
        "Explain this class.",
    ]
    comp = Compressor(tokenizer=ApproximateTokenizer())
    for prompt in prompts:
        result = comp.compress(sample_dart_bloc, prompt)
        assert prompt in result.compressed_prompt
        assert result.stats is not None
