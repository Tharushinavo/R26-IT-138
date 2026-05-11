import React from 'react';
import {
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import Card from '../components/Card';
import { useAuth } from '../context/AuthContext';
import { colors as lightColors, radius, spacing, typography, useAppTheme } from '../theme';

export default function TeacherHomeScreen({ route }: any) {
  const navigation = useNavigation<any>();
  const { teacherId } = route.params;
  const { user } = useAuth();
  const { colors } = useAppTheme();
  const styles = createStyles(colors);
  const teacherName = user?.full_name || 'Teacher';

  return (
    <View style={{ flex: 1, backgroundColor: colors.background }}>
    <ScrollView contentContainerStyle={styles.container}>
      <View style={styles.header}>
        <View>
          <Text style={styles.kicker}>Teacher workspace</Text>
          <Text style={styles.title}>Welcome, {teacherName}</Text>
          <Text style={styles.subtitle}>Manage student progress and cognitive question banks.</Text>
        </View>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>{teacherName.charAt(0).toUpperCase()}</Text>
        </View>
      </View>

      <TouchableOpacity
        activeOpacity={0.75}
        onPress={() => navigation.navigate('TeacherStudents', { teacherId })}
      >
        <Card style={styles.taskCard}>
          <View style={[styles.iconBubble, { backgroundColor: colors.skyBlueSoft }]}>
            <Text style={styles.iconText}>S</Text>
          </View>
          <View style={styles.taskCopy}>
            <Text style={styles.taskTitle}>Students Dashboard</Text>
            <Text style={styles.taskText}>View students, cognitive profiles, performance, and support needs.</Text>
          </View>
          <Text style={styles.arrow}>›</Text>
        </Card>
      </TouchableOpacity>

      <TouchableOpacity
        activeOpacity={0.75}
        onPress={() => navigation.navigate('TeacherQuestions', { teacherId })}
      >
        <Card style={styles.taskCard}>
          <View style={[styles.iconBubble, { backgroundColor: '#F2EDFF' }]}>
            <Text style={[styles.iconText, { color: colors.purple }]}>Q</Text>
          </View>
          <View style={styles.taskCopy}>
            <Text style={styles.taskTitle}>Cognitive Questions</Text>
            <Text style={styles.taskText}>Create, edit, delete, or generate questions with an AI API key.</Text>
          </View>
          <Text style={styles.arrow}>›</Text>
        </Card>
      </TouchableOpacity>

    </ScrollView>
    </View>
  );
}

const createStyles = (colors: typeof lightColors) => StyleSheet.create({
  container: {
    padding: spacing.lg,
    paddingTop: spacing.md,
    gap: spacing.md,
    paddingBottom: spacing.xxl,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: spacing.md,
    marginBottom: spacing.sm,
  },
  kicker: {
    ...typography.caption,
    color: colors.primaryDark,
    textTransform: 'uppercase',
  },
  title: {
    ...typography.title,
    color: colors.textWarm,
    marginTop: spacing.xs,
  },
  subtitle: {
    ...typography.body,
    color: colors.textMuted,
    marginTop: spacing.xs,
    maxWidth: 260,
  },
  avatar: {
    width: 58,
    height: 58,
    borderRadius: 29,
    backgroundColor: colors.warmYellow,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 3,
    borderColor: colors.surface,
  },
  avatarText: {
    fontSize: 24,
    fontWeight: '900',
    color: colors.textWarm,
  },
  taskCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  iconBubble: {
    width: 52,
    height: 52,
    borderRadius: 26,
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconText: {
    fontSize: 22,
    fontWeight: '900',
    color: colors.primaryDark,
  },
  taskCopy: {
    flex: 1,
  },
  taskTitle: {
    ...typography.subtitle,
    color: colors.textWarm,
  },
  taskText: {
    ...typography.caption,
    color: colors.textMuted,
    marginTop: 4,
    lineHeight: 18,
  },
  arrow: {
    fontSize: 34,
    color: colors.textMuted,
    fontWeight: '300',
  },
});
