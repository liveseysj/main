# Hair Try-On App

A virtual hair try-on application that lets you take selfies and see yourself with different hairstyles and colors using AI-powered face detection.

## 📦 Available Versions

This repository contains **two versions** of the Hair Try-On app:

### 1. Web App (Recommended - Run Immediately!) 🌐

**Location**: `web-app/`

A browser-based version that works on any device with a camera. No installation required!

**Quick Start**:
```bash
cd web-app
# Then open index.html in your browser, or run a local server:
python -m http.server 8000
# Open: http://localhost:8000
```

**Features**:
- ✅ Works immediately in any browser
- ✅ No installation or build process
- ✅ Works on phone, tablet, or computer
- ✅ Cross-platform (Windows, Mac, Linux, iOS, Android)

[See web-app/README.md for detailed instructions](web-app/README.md)

### 2. iOS App (iPhone/iPad) 📱

**Location**: `HairTryOn/`

A native iOS application built with SwiftUI. Requires Xcode and macOS to build.

**Requirements**:
- macOS computer
- Xcode 15.0 or later
- iOS 15.0 or later device

**Quick Start**:
```bash
cd HairTryOn
open HairTryOn.xcodeproj
# Build and run in Xcode
```

[See HairTryOn/README.md for detailed instructions](HairTryOn/README.md)

## 🎨 Features (Both Versions)

### Hairstyles (10+)
- Long
- Short
- Bob
- Pixie
- Curly
- Wavy
- Straight
- Afro
- Buzz Cut
- Mohawk

### Hair Colors (12+)
- **Natural**: Black, Brown, Blonde, Red, Auburn, Platinum, Silver
- **Fun**: Pink, Blue, Purple, Green, Rainbow

### Technology
- AI-powered face detection
- Real-time preview
- Save your favorite looks
- Intuitive interface

## 🚀 Which Version Should I Use?

| Situation | Recommended Version |
|-----------|-------------------|
| Want to try it **right now** | 🌐 **Web App** |
| Don't have a Mac | 🌐 **Web App** |
| Want it on Android | 🌐 **Web App** |
| Want it on iPhone | 🌐 **Web App** (works in browser!) |
| Building native iOS apps | 📱 iOS App |
| Need offline functionality | 📱 iOS App |

**TL;DR**: Use the **Web App** unless you specifically need a native iOS app.

## 📸 How It Works

1. **Take a Selfie**: Use your device's camera to capture a photo
2. **Face Detection**: AI automatically detects your face and landmarks
3. **Try Styles**: Select from 10+ hairstyles and 12+ colors
4. **See Preview**: View yourself with the new style in real-time
5. **Save**: Download your favorite looks

## 🛠️ Development

### Web App Development
```bash
cd web-app
# No build process needed - edit HTML/CSS/JS directly
# Open index.html to test
```

### iOS App Development
```bash
cd HairTryOn
open HairTryOn.xcodeproj
# Build and run in Xcode
```

## 📋 Requirements

### Web App
- Modern web browser (Chrome, Firefox, Safari, Edge)
- Device with camera
- Internet connection (for loading AI models)

### iOS App
- macOS with Xcode 15.0+
- iPhone/iPad with iOS 15.0+
- Apple Developer account (for device deployment)

## 🔒 Privacy

- All face detection happens **on your device**
- No photos uploaded to any server
- No data stored or transmitted
- Completely private and secure

## 📁 Repository Structure

```
.
├── web-app/                 # Web version (browser-based)
│   ├── index.html
│   ├── css/
│   │   └── styles.css
│   ├── js/
│   │   └── app.js
│   └── README.md
│
├── HairTryOn/              # iOS version (native app)
│   ├── HairTryOn.xcodeproj/
│   ├── HairTryOn/
│   │   ├── Models/
│   │   ├── Views/
│   │   ├── ViewModels/
│   │   └── Utilities/
│   └── README.md
│
└── README.md               # This file
```

## 🎯 Quick Start (Web App)

The fastest way to get started:

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd main/web-app
   ```

2. **Open in browser**:
   - Double-click `index.html`, or
   - Run: `python -m http.server 8000`
   - Open: http://localhost:8000

3. **Start using**:
   - Click "Take Selfie"
   - Allow camera access
   - Capture your photo
   - Try different styles!

## 💡 Tips

- Use good lighting for best face detection
- Face the camera directly
- Try different styles and colors
- Save your favorites

## 🐛 Troubleshooting

**Camera not working?**
- Check browser permissions
- Use HTTPS or localhost
- Try a different browser

**Face not detected?**
- Ensure good lighting
- Face the camera directly
- Remove sunglasses/hats

## 📄 License

This project is available for educational and personal use.

## 🤝 Contributing

Contributions are welcome! Feel free to submit issues or pull requests.

---

**Start with the Web App for instant results!** 🎉
