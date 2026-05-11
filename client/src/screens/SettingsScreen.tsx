import React, { useState, useCallback } from 'react';
import {
  Image,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import PrimaryButton from '../components/PrimaryButton';
import ProfileControls from '../components/ProfileControls';
import AlertToast from '../components/AlertToast';
import type { AlertType } from '../components/AlertToast';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../i18n/LanguageContext';
import { api } from '../api/client';
import { colors as lightColors, radius, spacing, typography, useAppTheme } from '../theme';

// DiceBear avatar styles that are kid-friendly
const DICEBEAR_STYLES = [
  'adventurer',
  'adventurer-neutral',
  'big-ears',
  'big-ears-neutral',
  'big-smile',
  'bottts',
  'croodles',
  'fun-emoji',
  'lorelei',
  'miniavs',
  'open-peeps',
  'personas',
  'pixel-art',
] as const;

function getDiceBearUrl(seed: string, style: string = 'adventurer') {
  return `https://api.dicebear.com/9.x/${style}/png?seed=${encodeURIComponent(seed)}&size=200`;
}

export default function SettingsScreen() {
  const { user, logout, updateUser } = useAuth();
  const { t } = useLanguage();
  const navigation = useNavigation<any>();
  const { colors, isDark } = useAppTheme();
  const s = createStyles(colors);

  // Avatar state
  const currentAvatarUrl = user?.avatar_url || getDiceBearUrl(user?.id || 'default', 'adventurer');
  const [avatarStyle, setAvatarStyle] = useState('adventurer');
  const [avatarSeed, setAvatarSeed] = useState(user?.id || 'default');
  const [avatarPreview, setAvatarPreview] = useState(currentAvatarUrl);
  const [showAvatarPicker, setShowAvatarPicker] = useState(false);

  // Edit name state
  const [editingName, setEditingName] = useState(false);
  const [nameValue, setNameValue] = useState(user?.full_name || '');

  // Change password state
  const [showPassword, setShowPassword] = useState(false);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Alert state
  const [alert, setAlert] = useState<{ visible: boolean; type: AlertType; title: string; message?: string }>({
    visible: false, type: 'success', title: '',
  });

  const [saving, setSaving] = useState(false);

  const showAlert = useCallback((type: AlertType, title: string, message?: string) => {
    setAlert({ visible: true, type, title, message });
  }, []);

  // ── Save name ──
  const handleSaveName = async () => {
    if (!nameValue.trim() || nameValue.trim().length < 2) {
      showAlert('error', 'Oops!', 'Name must be at least 2 characters.');
      return;
    }
    setSaving(true);
    try {
      const res = await api.updateProfile({ full_name: nameValue.trim() });
      updateUser(res.user);
      setEditingName(false);
      showAlert('success', 'Name Updated! ✨', `You're now ${res.user.full_name}`);
    } catch (e: any) {
      showAlert('error', 'Oops!', e?.message || 'Failed to update name.');
    } finally {
      setSaving(false);
    }
  };

  // ── Save password ──
  const handleSavePassword = async () => {
    if (newPassword.length < 6) {
      showAlert('error', 'Too Short!', 'Password must be at least 6 characters.');
      return;
    }
    if (newPassword !== confirmPassword) {
      showAlert('error', 'Mismatch!', 'Passwords do not match. Try again.');
      return;
    }
    setSaving(true);
    try {
      await api.updateProfile({ password: newPassword });
      setNewPassword('');
      setConfirmPassword('');
      setShowPassword(false);
      showAlert('success', 'Password Changed! 🔒', 'Your new password is saved.');
    } catch (e: any) {
      showAlert('error', 'Oops!', e?.message || 'Failed to change password.');
    } finally {
      setSaving(false);
    }
  };

  // ── Save avatar ──
  const handleSaveAvatar = async () => {
    setSaving(true);
    try {
      const url = getDiceBearUrl(avatarSeed, avatarStyle);
      const res = await api.updateProfile({ avatar_url: url });
      updateUser(res.user);
      setShowAvatarPicker(false);
      showAlert('success', 'New Look! 🎨', 'Your avatar has been updated.');
    } catch (e: any) {
      showAlert('error', 'Oops!', e?.message || 'Failed to save avatar.');
    } finally {
      setSaving(false);
    }
  };

  const randomizeSeed = () => {
    const seed = `${user?.id || 'u'}_${Date.now()}_${Math.floor(Math.random() * 9999)}`;
    setAvatarSeed(seed);
    setAvatarPreview(getDiceBearUrl(seed, avatarStyle));
  };

  const handleLogout = async () => {
    await logout();
    navigation.reset({ index: 0, routes: [{ name: 'Login' }] });
  };

  return (
    <View style={{ flex: 1, backgroundColor: colors.background }}>
      <ScrollView contentContainerStyle={s.container}>
        {/* ── Logout at top ── */}
        <TouchableOpacity style={s.logoutRow} onPress={handleLogout} activeOpacity={0.7}>
          <Ionicons name="log-out-outline" size={22} color={colors.danger} />
          <Text style={s.logoutText}>Logout</Text>
        </TouchableOpacity>

        {/* ── Avatar + Info Card ── */}
        <View style={s.card}>
          <TouchableOpacity onPress={() => setShowAvatarPicker(!showAvatarPicker)} activeOpacity={0.8}>
            <View style={s.avatarWrap}>
              <Image
                source={{ uri: currentAvatarUrl }}
                style={s.avatarImg}
                defaultSource={{ uri: getDiceBearUrl('loading', 'adventurer') }}
              />
              <View style={s.avatarBadge}>
                <Ionicons name="camera" size={14} color="#fff" />
              </View>
            </View>
          </TouchableOpacity>

          {/* Name (editable) */}
          {editingName ? (
            <View style={s.editRow}>
              <TextInput
                style={s.nameInput}
                value={nameValue}
                onChangeText={setNameValue}
                autoFocus
                placeholder="Your name"
                placeholderTextColor={colors.textMuted}
              />
              <TouchableOpacity onPress={handleSaveName} disabled={saving} style={s.iconBtn}>
                <Ionicons name="checkmark-circle" size={28} color={colors.success} />
              </TouchableOpacity>
              <TouchableOpacity onPress={() => { setEditingName(false); setNameValue(user?.full_name || ''); }} style={s.iconBtn}>
                <Ionicons name="close-circle" size={28} color={colors.danger} />
              </TouchableOpacity>
            </View>
          ) : (
            <TouchableOpacity style={s.editRow} onPress={() => setEditingName(true)} activeOpacity={0.7}>
              <Text style={s.name}>{user?.full_name || ''}</Text>
              <Ionicons name="pencil" size={18} color={colors.textMuted} style={{ marginLeft: 6 }} />
            </TouchableOpacity>
          )}

          <Text style={s.email}>{user?.email || ''}</Text>
          <View style={s.roleBadge}>
            <Text style={s.roleText}>
              {user?.role === 'teacher' || user?.role === 'admin'
                ? `👩‍🏫 ${t.common?.teacher ?? 'Teacher'}`
                : `🧒 ${t.common?.student ?? 'Student'}`}
            </Text>
          </View>
        </View>

        {/* ── Avatar Picker ── */}
        {showAvatarPicker && (
          <View style={s.section}>
            <Text style={s.sectionTitle}>🎨 Choose Your Avatar</Text>

            {/* Preview */}
            <View style={s.avatarPreviewWrap}>
              <Image source={{ uri: avatarPreview }} style={s.avatarPreviewImg} />
            </View>

            {/* Randomize button */}
            <TouchableOpacity style={s.randomBtn} onPress={randomizeSeed} activeOpacity={0.7}>
              <Ionicons name="shuffle" size={20} color={colors.textWarm} />
              <Text style={s.randomBtnText}>Randomize</Text>
            </TouchableOpacity>

            {/* Style picker */}
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={s.stylePicker}>
              {DICEBEAR_STYLES.map((style) => (
                <TouchableOpacity
                  key={style}
                  style={[
                    s.styleChip,
                    avatarStyle === style && { backgroundColor: colors.warmYellow, borderColor: colors.warmYellow },
                  ]}
                  onPress={() => {
                    setAvatarStyle(style);
                    setAvatarPreview(getDiceBearUrl(avatarSeed, style));
                  }}
                  activeOpacity={0.7}
                >
                  <Image
                    source={{ uri: getDiceBearUrl(avatarSeed, style) }}
                    style={s.styleChipImg}
                  />
                  <Text style={[s.styleChipText, avatarStyle === style && { color: colors.textWarm, fontWeight: '800' }]}>
                    {style.replace(/-/g, ' ')}
                  </Text>
                </TouchableOpacity>
              ))}
            </ScrollView>

            <PrimaryButton title={saving ? 'Saving...' : 'Save Avatar'} onPress={handleSaveAvatar} />
          </View>
        )}

        {/* ── Change Password ── */}
        <View style={s.section}>
          <TouchableOpacity
            style={s.sectionHeader}
            onPress={() => setShowPassword(!showPassword)}
            activeOpacity={0.7}
          >
            <Ionicons name="lock-closed-outline" size={20} color={colors.textWarm} />
            <Text style={s.sectionTitle}>Change Password</Text>
            <Ionicons name={showPassword ? 'chevron-up' : 'chevron-down'} size={20} color={colors.textMuted} />
          </TouchableOpacity>

          {showPassword && (
            <View style={s.passwordFields}>
              <TextInput
                style={s.input}
                placeholder="New password (min 6 chars)"
                placeholderTextColor={colors.textMuted}
                secureTextEntry
                value={newPassword}
                onChangeText={setNewPassword}
              />
              <TextInput
                style={s.input}
                placeholder="Confirm new password"
                placeholderTextColor={colors.textMuted}
                secureTextEntry
                value={confirmPassword}
                onChangeText={setConfirmPassword}
              />
              <PrimaryButton
                title={saving ? 'Saving...' : 'Update Password'}
                onPress={handleSavePassword}
              />
            </View>
          )}
        </View>

        {/* ── Theme & Language ── */}
        <View style={s.section}>
          <Text style={s.sectionTitle}>Theme & {t.common.language}</Text>
          <ProfileControls />
        </View>

      </ScrollView>

      {/* ── Alert Toast ── */}
      <AlertToast
        visible={alert.visible}
        type={alert.type}
        title={alert.title}
        message={alert.message}
        onDismiss={() => setAlert(prev => ({ ...prev, visible: false }))}
      />
    </View>
  );
}

const createStyles = (colors: typeof lightColors) => StyleSheet.create({
  container: {
    padding: spacing.lg,
    paddingTop: spacing.md,
    paddingBottom: 120,
    gap: spacing.lg,
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.xl,
    padding: spacing.xl,
    alignItems: 'center',
    borderWidth: 2,
    borderColor: colors.border,
    gap: spacing.sm,
  },
  avatarWrap: {
    position: 'relative',
    marginBottom: spacing.sm,
  },
  avatarImg: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: colors.warmYellowSoft,
    borderWidth: 3,
    borderColor: colors.warmYellow,
  },
  avatarBadge: {
    position: 'absolute',
    bottom: 0,
    right: 0,
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
    borderColor: colors.surface,
  },
  editRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  nameInput: {
    ...typography.title,
    color: colors.textWarm,
    borderBottomWidth: 2,
    borderBottomColor: colors.warmYellow,
    paddingVertical: 4,
    paddingHorizontal: 8,
    minWidth: 150,
    textAlign: 'center',
  },
  iconBtn: {
    padding: 4,
  },
  name: {
    ...typography.title,
    color: colors.textWarm,
  },
  email: {
    ...typography.body,
    color: colors.textMuted,
  },
  roleBadge: {
    backgroundColor: colors.warmYellowSoft,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: radius.pill,
    marginTop: spacing.xs,
  },
  roleText: {
    ...typography.caption,
    color: colors.textWarm,
  },
  section: {
    backgroundColor: colors.surface,
    borderRadius: radius.xl,
    padding: spacing.lg,
    borderWidth: 2,
    borderColor: colors.border,
    gap: spacing.md,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  sectionTitle: {
    ...typography.subtitle,
    color: colors.textWarm,
    flex: 1,
  },
  avatarPreviewWrap: {
    alignItems: 'center',
    padding: spacing.md,
  },
  avatarPreviewImg: {
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: colors.warmYellowSoft,
    borderWidth: 3,
    borderColor: colors.warmYellow,
  },
  randomBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.xs,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.lg,
    backgroundColor: colors.warmYellowSoft,
    borderRadius: radius.pill,
    alignSelf: 'center',
  },
  randomBtnText: {
    ...typography.caption,
    color: colors.textWarm,
    fontWeight: '700',
  },
  stylePicker: {
    flexGrow: 0,
    marginVertical: spacing.sm,
  },
  styleChip: {
    alignItems: 'center',
    gap: 4,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.sm,
    marginRight: spacing.sm,
    borderRadius: radius.lg,
    borderWidth: 2,
    borderColor: colors.border,
    backgroundColor: colors.background,
    minWidth: 80,
  },
  styleChipImg: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: colors.warmYellowSoft,
  },
  styleChipText: {
    ...typography.caption,
    fontSize: 9,
    color: colors.textMuted,
    textAlign: 'center',
    textTransform: 'capitalize',
  },
  passwordFields: {
    gap: spacing.md,
  },
  input: {
    ...typography.body,
    color: colors.text,
    backgroundColor: colors.background,
    borderRadius: radius.lg,
    paddingVertical: 12,
    paddingHorizontal: spacing.md,
    borderWidth: 2,
    borderColor: colors.border,
  },
  logoutRow: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-end',
    gap: spacing.xs,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    backgroundColor: colors.dangerBg,
    borderRadius: radius.pill,
  },
  logoutText: {
    ...typography.caption,
    color: colors.danger,
    fontWeight: '700',
  },
});
