"""Shared pytest fixtures."""
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_fixture(relative_path: str) -> str:
    return (FIXTURE_DIR / relative_path).read_text(encoding="utf-8")


def fixture_exists(relative_path: str) -> bool:
    return (FIXTURE_DIR / relative_path).exists()


@pytest.fixture()
def approximate_compressor():
    from llmpress import Compressor
    from llmpress.tokenizers import ApproximateTokenizer

    return Compressor(tokenizer=ApproximateTokenizer())


@pytest.fixture()
def decompressor():
    from llmpress import Decompressor

    return Decompressor()


@pytest.fixture()
def sample_dart_bloc():
    return """\
class UserBloc extends Bloc<UserEvent, UserState> {
  final UserRepository _userRepository;

  UserBloc({required UserRepository userRepository})
      : _userRepository = userRepository,
        super(UserInitial()) {
    on<LoadUser>(_onLoadUser);
    on<UpdateUser>(_onUpdateUser);
    on<DeleteUser>(_onDeleteUser);
  }

  Future<void> _onLoadUser(
    LoadUser event,
    Emitter<UserState> emit,
  ) async {
    emit(UserLoading());
    final result = await _userRepository.getUser(event.userId);
    result.fold(
      (failure) => emit(UserError(failure: failure)),
      (user) => emit(UserLoaded(user: user)),
    );
  }

  Future<void> _onUpdateUser(
    UpdateUser event,
    Emitter<UserState> emit,
  ) async {
    emit(UserLoading());
    final result = await _userRepository.updateUser(event.user);
    result.fold(
      (failure) => emit(UserError(failure: failure)),
      (user) => emit(UserLoaded(user: user)),
    );
  }

  Future<void> _onDeleteUser(
    DeleteUser event,
    Emitter<UserState> emit,
  ) async {
    emit(UserLoading());
    final result = await _userRepository.deleteUser(event.userId);
    result.fold(
      (failure) => emit(UserError(failure: failure)),
      (_) => emit(UserDeleted()),
    );
  }
}
"""


@pytest.fixture()
def sample_typescript():
    return """\
import { useState, useEffect, useCallback } from 'react';
import { UserService } from '../services/UserService';
import { UserProfile } from '../types/UserProfile';
import { ApiResponse } from '../types/ApiResponse';

interface UserProfileProps {
  userId: string;
  onSuccess?: (profile: UserProfile) => void;
  onError?: (error: Error) => void;
}

export const UserProfileComponent: React.FC<UserProfileProps> = ({
  userId,
  onSuccess,
  onError,
}) => {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchProfile = useCallback(async () => {
    setLoading(true);
    try {
      const response: ApiResponse<UserProfile> = await UserService.getProfile(userId);
      setProfile(response.data);
      setLoading(false);
      onSuccess?.(response.data);
    } catch (err) {
      const error = err as Error;
      setError(error);
      setLoading(false);
      onError?.(error);
    }
  }, [userId, onSuccess, onError]);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;
  if (!profile) return null;

  return <UserProfileView profile={profile} />;
};
"""
