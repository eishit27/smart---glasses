# VisionAid Mobile Companion App 📱👓

The official cross-platform Flutter companion application for the **VisionAid Smart Glasses** project.

Specifically engineered for **zero-touch in-pocket background operation** and **complete accessibility for visually impaired and blind users**.

---

## 🌟 Key Accessibility & Architecture Features

### 1. Zero-Touch In-Pocket Operation
- The phone remains securely in the user's pocket or bag.
- Automatic background BLE reconnect and cryptographic challenge-response authentication (`AUTH:<token>`).
- Temple button clicks on the glasses directly stream camera frames and trigger local neural models without needing to touch or unlock the phone.

### 2. Tactile 4-Quadrant Dashboard (Non-Visual Muscle Memory)
When the user does hold the phone, the interface is organized into a bold 2×2 tactile grid allowing immediate activation by screen quadrant position:
- **Top-Left**: `DESCRIBE SCENE` — instant spatial scene breakdown.
- **Top-Right**: `READ TEXT` — offline OCR for signs, medication bottles, and restaurant menus.
- **Bottom-Left**: `WHO IS HERE?` — face identification for enrolled family, friends, and caregivers.
- **Bottom-Right**: `LOST ITEM` — ground-plane drop scanner to locate fallen keys, badges, or coins.

### 3. WCAG AAA High-Contrast Visual Design
- **Background**: Pure OLED Black (`#000000`) for zero glare, battery efficiency, and contrast.
- **Primary Elements**: High-intensity Tactile Yellow (`#FFD700`) exceeding 15:1 optical contrast ratio.
- **Touch Targets**: Minimum **64dp** interactive height on all buttons and tiles (exceeds Android 48dp and Apple 44dp guidelines).

### 4. TalkBack & VoiceOver First-Class Integration
- Every widget is wrapped with semantic descriptors (`Semantics`), live regions (`liveRegion: true` for spoken hazard alerts), and button hints.
- Physical haptic confirmation patterns (`HapticFeedback.selectionClick()` and `heavyImpact()`) give tactile feedback on every interaction.

### 5. Face Directory & Emergency SOS
- Local offline biometric database for loved ones, doctors, and friends.
- Emergency SOS triple-click temple button action triggers instant SMS/location dispatch to designated emergency contacts.

---

## 🏗️ Project Architecture (MVVM & Clean Architecture)

```
mobile/
├── lib/
│   ├── main.dart                               # MultiProvider injection & root app
│   ├── data/
│   │   ├── models/
│   │   │   ├── glasses_status.dart             # Connection state, battery, walking mode
│   │   │   ├── face_profile.dart               # Enrolled face metadata & relations
│   │   │   └── user_settings.dart              # Audio speed, earcons, SOS contact
│   │   └── services/
│   │       ├── ble_service.dart                # BLE 5.0 scanning, MTU chunking, token auth
│   │       └── audio_feedback_service.dart     # Haptic engine & TalkBack announcements
│   ├── domain/
│   │   └── repositories/
│   │       └── glasses_repository.dart         # Repository bridging BLE & local storage
│   └── ui/
│       ├── core/
│       │   ├── app_theme.dart                  # WCAG AAA pure black + yellow themes
│       │   └── accessible_widgets.dart         # >=64dp buttons, tactile quadrant tiles
│       └── features/
│           ├── home/                           # 4-quadrant tactile home screen
│           ├── faces/                          # Family & friends enrollment screen
│           └── settings/                       # Voice speed, running mode & SOS setup
└── pubspec.yaml
```

---

## 🚀 Setup & Execution Guide

### Prerequisites
- [Flutter SDK](https://flutter.dev/docs/get-started/install) (`>= 3.2.0`)
- Android Studio / Xcode
- Physical smartphone with Bluetooth Low Energy (BLE 4.2 or 5.0+)

### Permissions Configuration

#### Android (`android/app/src/main/AndroidManifest.xml`):
```xml
<uses-permission android:name="android.permission.BLUETOOTH_SCAN" android:usesPermissionFlags="neverForLocation" />
<uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<uses-permission android:name="android.permission.VIBRATE" />
```

#### iOS (`ios/Runner/Info.plist`):
```xml
<key>NSBluetoothAlwaysUsageDescription</key>
<string>VisionAid requires Bluetooth to communicate with your smart glasses.</string>
<key>NSCameraUsageDescription</key>
<string>Camera is used to enroll faces of family and friends.</string>
```

### Install Dependencies & Run
```bash
cd mobile

# Fetch pub dependencies
flutter pub get

# Run on connected Android or iOS device
flutter run
```
