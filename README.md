# MathsMate — Adaptive Game Based Learning Engine

An AI-powered adaptive educational gaming platform designed to support children with dyscalculia through personalized mathematical learning experiences. The system dynamically adjusts game difficulty, rewards, and learning activities based on learner performance and engagement using machine learning and reinforcement learning techniques.

This component is part of a larger adaptive learning ecosystem developed for dyscalculia learners. The Adaptive Game-Based Learning Engine focuses on improving learner engagement, reducing mathematics anxiety, and providing personalized game-based educational support through intelligent adaptation mechanisms.



---

## Architecture

```
┌────────────────────┐      REST API      ┌────────────────────────┐      Database      ┌──────────────────┐
│   React Frontend   │ ─────────────────▶ │   Node.js + Express    │ ─────────────────▶ │     SuperBase      │
│   Educational UI   │                    │ Adaptive Learning API  │                    │ Learner Profiles │
│   Interactive Games│ ◀───────────────── │  ML Integration Layer  │ ◀───────────────── │ Gameplay History │
└────────────────────┘                    └────────────────────────┘                    └──────────────────┘
                                              │
                                              ▼
                                    ┌────────────────────┐
                                    │ Machine Learning   │
                                    │ Reinforcement RL   │
                                    │           
                                    └────────────────────┘
```

**Data flow:**

1. The learner interacts with educational games through the frontend interface.
2. The system collects learner interaction data such as response time, accuracy, attempts, and engagement behavior.
3. Interaction data is sent to the backend API for processing and analysis.
4. Machine learning models analyze learner behavior and engagement patterns.
5. The adaptive engine dynamically adjusts:
       Game difficulty
       Reward mechanisms
       Game types
       Learning activities
6. Updated learner data and gameplay history are stored in MongoDB.
7. The system generates learner progress analytics and adaptive recommendations.

## Project structure

```
MathsMate/
├── App.tsx                          ← Entry point
├── app/
│   ├── navigation/
│   │   ├── AppNavigator.tsx         ← Root navigator (Auth vs Main)
│   │   ├── AuthNavigator.tsx        ← Login / Register flow
│   │   ├── TabNavigator.tsx         ← Bottom tab (Home / Progress)
│   │   ├── GameNavigator.tsx        ← All game screens
│   │   └── types.ts                 ← All route & param types
│   │
│   ├── screens/
│   │   ├── auth/
│   │   │   ├── LoginScreen.tsx      ← JWT login + Google
│   │   │   └── RegisterScreen.tsx   ← Avatar, age, username, password strength
│   │   ├── home/
│   │   │   └── HomeScreen.tsx       ← Game grid + daily challenge + stats
│   │   ├── games/
│   │   │   ├── CountingGameScreen.tsx    ← Count objects, tap answer
│   │   │   ├── ComparisonGameScreen.tsx  ← Bigger/smaller with visual dots
│   │   │   ├── ArithmeticGameScreen.tsx  ← Add/subtract operations
│   │   │   ├── PuzzleGameScreen.tsx      ← Missing number with numpad
│   │   │   ├── SequenceGameScreen.tsx    ← Find pattern in sequence
│   │   │   └── DragDropGameScreen.tsx    ← Sort numbers into slots
│   │   └── progress/
│   │       └── ProgressScreen.tsx   ← Stars, badges, accuracy history
│   │
│   ├── context/
│   │   ├── ThemeContext.tsx          ← Light/Dark mode + color palette
│   │   └── AuthContext.tsx           ← Student state, isAuthenticated
│   │
│   ├── services/
│   │   └── api.ts                   ← All FastAPI calls (axios + JWT refresh)
│   │
│   ├── constants/
│   │   ├── colors.ts                ← LightColors / DarkColors palettes
│   │   ├── typography.ts            ← Font sizes, weights, text presets
│   │   └── spacing.ts               ← Spacing scale, border radius, shadows
│   │
│   └── types/
│       └── index.ts                 ← Shared TypeScript interfaces
 
```

> **4-member integration:** The folder structure includes reserved directories
> for each team member's module. See `client/src/screens/README.md` and
> `server/app/README.md` for the integration guide.

---

## Quick start

### 1. Backend 

```powershell
cd backend
npm install
npm start
```

Server runs on **port 8000**.
Swagger UI → http://localhost:8000/docs

> Alternative: `.\start.ps1` (Windows) or `start.bat` — creates venv automatically.

### 2. Frontend 

In a **new, separate terminal**:

```powershell
cd frontend
npm install
npm start
```

Scan the QR code with **Expo Go** on your phone.
> ```
> EXPO_PUBLIC_API_BASE=http://YOUR_LAN_IP:8000
> EXPO_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
> EXPO_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
> ```
> Find your IP: `ipconfig` (Windows) 
> Phone and computer must be on the same WiFi.

### 3. Database (Supabase)

1. Create a [Supabase](https://supabase.com) project.
2. Run `server/supabase_schema.sql` in the Supabase SQL editor — creates 6 tables:
   - `id`, `student_id`, `interaction_id`, `interactions`, `accuracy_rate`, `average_response_time`, `attempt_frequency`,
   - `hint_usage_rate`, `error_frequency`, `engagement_score`, `created_at`
3. Fill in `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and `SUPABASE_ANON_KEY` in `server/.env`.

### 4. ML Model

The server loads a trained Reinforcement Learning.

Use Google Colab with a larger synthetic dataset (1000+ rows).

---

## API endpoints

| Method | Endpoint      | Description                         |
| ------ | ------------- | ----------------------------------- |
| GET    | /games        | Get available educational games     |
| POST   | /interactions | Save learner interaction data       |
| POST   | /adapt        | Generate adaptive learning response |
| GET    | /progress     | Retrieve learner progress           |
| GET    | /analytics    | Retrieve learner analytics          |


---

## ML model details

-Main Algorithm
   -Reinforcement Learning (RL)
-Additional Algorithms
   -Decision Tree Classifier
   -Random Forest Classifier
-Input Features
   -Response time
   -Correct / incorrect answers
   -Number of attempts
   -Interaction frequency
   -Engagement duration
   -Error patterns
-Adaptive Actions
   -Increase / decrease difficulty
   -Change game type
   -Modify rewards
   -Provide hints

---

## Tech stack

| Layer             | Technology                       |
| ----------------- | -------------------------------- |
| Frontend          | React.js                         |
| Backend           | Node.js, Express.js              |
| Database          | MongoDB                          |
| Machine Learning  | Python, Scikit-learn, TensorFlow |
| Game Development  | Phaser.js, HTML5 Canvas          |
| API Communication | REST API                         |


---
## Adaptive Learning Features
 -Dynamic difficulty adjustment
 -Personalized rewards and achievements
 -Real-time learner engagement monitoring
 -Reinforcement Learning–based adaptation
 -Performance tracking and analytics
 -Personalized learning pathways
 -Immediate feedback and hints
 ---

## Educational Games

The system currently includes multiple interactive educational games designed for dyscalculia learners:

-Counting Game
-Number Comparison Game
-Arithmetic Puzzle Game
-Drag-and-Drop Activity
-Pattern Recognition Game

Each game is integrated with adaptive learning and gamification mechanisms to personalize learner experiences.

```



---

## Team members

| Member | Component | Status |
|--------|-----------|--------|
| 1 - IT22136206 | Cognitive Skill Profiling System | Completed till the Progress Presentation 1 |
| 2 | Personalised Math Learning Engine | Pending integration |
| 3 - IT22117878 | Adaptive Game-Based Learning Engine | Pending integration |
| 4 | Learning Insight and Early Warning System | Pending integration |
