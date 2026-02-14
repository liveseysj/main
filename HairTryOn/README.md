# Hair Try-On iOS App

An iPhone application that allows users to take selfies and virtually try on different hairstyles and colors using advanced face detection technology.

## Features

- **Real-time Camera Integration**: Take selfies using the front-facing camera
- **AI-Powered Face Detection**: Automatic face and facial landmark detection using Apple's Vision framework
- **10+ Hairstyles**: Choose from various styles including:
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

- **12+ Hair Colors**: Try different colors including:
  - Natural colors: Black, Brown, Blonde, Red, Auburn
  - Fun colors: Pink, Blue, Purple, Green, Silver, Platinum, Rainbow

- **Save Your Look**: Save your favorite hairstyle combinations to your photo library
- **Intuitive UI**: Easy-to-use interface with smooth navigation

## Requirements

- iOS 15.0 or later
- iPhone with front-facing camera
- Xcode 15.0 or later (for building)

## Installation

### Option 1: Build from Source

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd HairTryOn
   ```

2. Open the project in Xcode:
   ```bash
   open HairTryOn.xcodeproj
   ```

3. Connect your iPhone or select an iOS Simulator

4. Update the Development Team:
   - Select the HairTryOn project in the navigator
   - Go to "Signing & Capabilities"
   - Select your development team

5. Build and run (⌘R)

### Option 2: Direct Installation

If you have the built app:
1. Connect your iPhone to your Mac
2. Use Xcode or other deployment tools to install the app

## Usage

1. **Launch the App**: Open Hair Try-On on your iPhone

2. **Take a Selfie**:
   - Tap "Take Selfie" on the home screen
   - Grant camera permissions when prompted
   - Position your face in the frame
   - Tap the capture button

3. **Try Different Styles**:
   - Once your face is detected, browse available hairstyles
   - Select a style type (Long, Short, Bob, etc.)
   - Choose a hair color
   - The preview updates in real-time

4. **Save Your Look**:
   - Once you find a style you like, tap "Save"
   - The image will be saved to your photo library

5. **Start Over**:
   - Tap "New Photo" to take another selfie

## Permissions

The app requires the following permissions:

- **Camera Access**: To take selfies
- **Photo Library Access**: To save your try-on results

These permissions are requested when you first use the relevant features.

## Technical Details

### Architecture

The app is built using:
- **SwiftUI**: Modern declarative UI framework
- **AVFoundation**: Camera capture and management
- **Vision Framework**: Face detection and facial landmark analysis
- **Core Graphics**: Image processing and hair overlay rendering

### Project Structure

```
HairTryOn/
├── HairTryOn.xcodeproj/       # Xcode project file
├── HairTryOn/
│   ├── HairTryOnApp.swift     # App entry point
│   ├── Info.plist             # App configuration
│   ├── Models/
│   │   └── HairStyle.swift    # Hair style and color models
│   ├── Views/
│   │   ├── ContentView.swift          # Main view
│   │   ├── CameraView.swift           # Camera interface
│   │   ├── HairOverlayView.swift      # Image display
│   │   └── HairStyleSelectionView.swift  # Style picker
│   ├── ViewModels/
│   │   └── CameraViewModel.swift      # Business logic
│   └── Utilities/
│       ├── FaceDetector.swift         # Face detection
│       └── ImageProcessor.swift       # Image manipulation
└── README.md
```

### How It Works

1. **Face Detection**: When you capture a photo, the Vision framework analyzes the image to detect faces and facial landmarks

2. **Hair Region Calculation**: Based on the detected face, the app calculates the approximate hair region above and around the face

3. **Hair Overlay**: The selected hairstyle is rendered as an overlay on top of the original image using Core Graphics

4. **Color Application**: Hair color is applied with appropriate transparency to create a realistic effect

## Customization

### Adding New Hairstyles

To add new hairstyle types, edit `HairStyle.swift`:

```swift
enum HairStyleType: String, CaseIterable {
    case yourNewStyle = "Your Style Name"
    // ... existing styles
}
```

Then implement the drawing method in `ImageProcessor.swift`:

```swift
private func drawYourNewStyle(in region: CGRect, color: UIColor, context: CGContext) {
    // Your drawing code here
}
```

### Adding New Colors

Add new colors in `HairStyle.swift`:

```swift
enum HairColor: String, CaseIterable {
    case yourNewColor = "Color Name"
    // ... existing colors

    var color: Color {
        switch self {
        case .yourNewColor: return Color(red: r, green: g, blue: b)
        // ... existing colors
        }
    }
}
```

## Known Limitations

- Hair overlays are simplified representations and may not match real hair physics
- Works best with frontal face photos with good lighting
- Face detection requires a clear view of the face
- Some hairstyles may need adjustment for different face shapes

## Future Enhancements

- More realistic hair rendering with textures
- Machine learning-based hair segmentation
- Video mode for real-time preview
- Social sharing features
- Custom hairstyle uploads
- AR mode with live camera feed

## Troubleshooting

**Camera not working:**
- Check that camera permissions are granted in Settings > Privacy > Camera

**Face not detected:**
- Ensure good lighting
- Face the camera directly
- Remove sunglasses or items covering your face

**App crashes:**
- Ensure you're running iOS 15.0 or later
- Try restarting the app

## License

This project is available for educational and personal use.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Support

For questions or issues, please open an issue on the repository.
