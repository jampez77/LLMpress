import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { UserService } from '../services/UserService';
import { NotificationService } from '../services/NotificationService';
import { UserProfile, UserSettings, UserNotification } from '../types';
import { ApiResponse, PaginatedResponse } from '../types/ApiResponse';

interface DashboardProps {
  userId: string;
  initialTab?: 'profile' | 'settings' | 'notifications';
}

export const UserDashboard: React.FC<DashboardProps> = ({
  userId,
  initialTab = 'profile',
}) => {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [notifications, setNotifications] = useState<UserNotification[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);
  const [activeTab, setActiveTab] = useState<string>(initialTab);
  const [page, setPage] = useState<number>(1);

  const fetchProfile = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response: ApiResponse<UserProfile> = await UserService.getProfile(userId);
      setProfile(response.data);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  const fetchSettings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response: ApiResponse<UserSettings> = await UserService.getSettings(userId);
      setSettings(response.data);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  const fetchNotifications = useCallback(async (pageNum: number) => {
    setLoading(true);
    setError(null);
    try {
      const response: ApiResponse<PaginatedResponse<UserNotification>> =
        await NotificationService.getNotifications(userId, pageNum);
      setNotifications(prev =>
        pageNum === 1 ? response.data.items : [...prev, ...response.data.items]
      );
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  const updateProfile = useCallback(async (updates: Partial<UserProfile>) => {
    setLoading(true);
    setError(null);
    try {
      const response: ApiResponse<UserProfile> = await UserService.updateProfile(userId, updates);
      setProfile(response.data);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  const updateSettings = useCallback(async (updates: Partial<UserSettings>) => {
    setLoading(true);
    setError(null);
    try {
      const response: ApiResponse<UserSettings> = await UserService.updateSettings(userId, updates);
      setSettings(response.data);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  const markNotificationRead = useCallback(async (notificationId: string) => {
    try {
      await NotificationService.markRead(userId, notificationId);
      setNotifications(prev =>
        prev.map(n => n.id === notificationId ? { ...n, read: true } : n)
      );
    } catch (err) {
      setError(err as Error);
    }
  }, [userId]);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  useEffect(() => {
    if (activeTab === 'settings') fetchSettings();
    if (activeTab === 'notifications') fetchNotifications(1);
  }, [activeTab, fetchSettings, fetchNotifications]);

  const unreadCount = useMemo(
    () => notifications.filter(n => !n.read).length,
    [notifications]
  );

  if (loading && !profile) return <LoadingScreen />;
  if (error && !profile) return <ErrorScreen error={error} onRetry={fetchProfile} />;

  return (
    <div className="dashboard">
      <TabBar
        tabs={['profile', 'settings', 'notifications']}
        active={activeTab}
        onSelect={setActiveTab}
        badges={{ notifications: unreadCount }}
      />
      {activeTab === 'profile' && profile && (
        <ProfileTab
          profile={profile}
          loading={loading}
          onUpdate={updateProfile}
        />
      )}
      {activeTab === 'settings' && (
        <SettingsTab
          settings={settings}
          loading={loading}
          onUpdate={updateSettings}
        />
      )}
      {activeTab === 'notifications' && (
        <NotificationsTab
          notifications={notifications}
          loading={loading}
          onMarkRead={markNotificationRead}
          onLoadMore={() => fetchNotifications(page + 1)}
        />
      )}
    </div>
  );
};
