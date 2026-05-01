# Screen Folder Structure

This app is part of a **4-member integrated MathsMate platform**. Each member owns a module that integrates into the shared mobile app.

## Folder Layout

```
src/screens/
├── onboarding/          # Shared onboarding flow (all members)
│   ├── LogoScreen       # Animated branding splash
│   ├── SplashScreen     # Cognitive skill profiling intro
│   └── LanguageSelectScreen  # EN / Sinhala language picker
│
├── auth/                # Shared authentication (all members)
│   ├── LoginScreen      # Sign in with email/password
│   └── SignUpScreen     # Create new account
│
├── cognitive-profile/   # Member 1: Cognitive Skill Profiling
│   ├── StudentDashboard
│   ├── MathActivityScreen
│   ├── ProfileResultScreen
│   ├── ProfileHistoryScreen
│   └── TeacherDashboard
│
├── [member-2]/          # Member 2: (To be integrated)
├── [member-3]/          # Member 3: (To be integrated)
├── [member-4]/          # Member 4: (To be integrated)
│
└── shared/              # Cross-module shared screens
    └── WelcomeScreen
```

## Integration Guide

Each member should:
1. Create their own subfolder under `src/screens/`
2. Add their screen types to `RootStackParamList` in `App.tsx`
3. Register screens in the `Stack.Navigator` in `App.tsx`
4. Add translations under their own key in `src/i18n/translations.ts`
5. Use the shared `theme.ts`, `PrimaryButton`, `Card`, and `LanguageToggle` components
