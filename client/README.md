# MathMinds – Client (Expo / React Native)

Kid-friendly math quiz app that captures interaction signals (accuracy,
response time, retries, hints, answer changes) and sends them to the
Cognitive Skill Profiling backend to produce a 4-dimensional brain profile.

## Setup

```powershell
cd client
npm install
```

## Configure API URL

Edit `app.json` → `expo.extra.apiUrl`.

- Web / iOS simulator: `http://localhost:8000`
- Android emulator: `http://10.0.2.2:8000`
- Expo Go on a real device: `http://<your-PC-LAN-IP>:8000` (run the server
  with `--host 0.0.0.0`, and make sure your phone is on the same Wi-Fi).

## Run

```powershell
npm run start
```

Scan the QR code with Expo Go, or press `a` / `i` / `w`.

## Screens

- **Home** – ask for a name, create/load a local user id.
- **Quiz** – 8 adaptive math questions; measures behavioural signals per question.
- **Profile** – shows memory / attention / number sense / processing speed as low / medium / high.

## Theme

Light sky blue, white and matching blues — defined in `src/theme.ts`.
