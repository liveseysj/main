# Hair Try-On Web App 💇

A web-based application that allows you to take selfies and virtually try on different hairstyles and colors using AI-powered face detection. Works on any device with a camera!

## 🚀 Quick Start

### Option 1: Open Directly in Browser (Easiest!)

1. Navigate to the `web-app` directory
2. Open `index.html` in your web browser:
   - **Double-click** the `index.html` file, or
   - **Right-click** → Open with → Your browser (Chrome, Firefox, Safari, Edge)

That's it! The app will load in your browser.

### Option 2: Using a Local Web Server (Recommended)

For the best experience, run a local web server:

**Using Python:**
```bash
# If you have Python 3:
cd web-app
python -m http.server 8000

# Then open: http://localhost:8000
```

**Using Node.js:**
```bash
# Install http-server globally (one time):
npm install -g http-server

# Run the server:
cd web-app
http-server -p 8000

# Then open: http://localhost:8000
```

**Using PHP:**
```bash
cd web-app
php -S localhost:8000

# Then open: http://localhost:8000
```

## 📱 How to Use

1. **Open the App**: Load `index.html` in your browser
2. **Wait for Models**: The face detection AI models will load (takes 5-10 seconds)
3. **Take a Selfie**:
   - Click "Take Selfie"
   - Allow camera access when prompted
   - Position your face in the frame
   - Click the capture button
4. **Try Different Styles**:
   - Wait for face detection to complete
   - Select a hairstyle (Long, Short, Bob, Pixie, etc.)
   - Choose a hair color
   - The preview updates automatically
5. **Save Your Look**: Click "Save Photo" to download the image
6. **Try Again**: Click "New Photo" to take another selfie

## ✨ Features

- **10+ Hairstyles**: Long, Short, Bob, Pixie, Curly, Wavy, Straight, Afro, Buzz Cut, Mohawk
- **12+ Hair Colors**: Black, Brown, Blonde, Red, Auburn, Platinum, Pink, Blue, Purple, Green, Silver, Rainbow
- **AI Face Detection**: Automatic face detection using face-api.js
- **Real-time Preview**: See changes instantly
- **Save Photos**: Download your favorite looks
- **Mobile Friendly**: Works on phones, tablets, and computers
- **No Installation**: Runs entirely in your browser

## 📋 Requirements

- **Browser**: Modern web browser (Chrome, Firefox, Safari, Edge)
- **Camera**: Any webcam or phone camera
- **Internet**: Required for loading face detection models from CDN
- **HTTPS or Localhost**: Camera access requires secure context

## 🔒 Privacy

- All processing happens **locally** in your browser
- No photos are uploaded to any server
- No data is stored or transmitted
- Face detection models are loaded from a public CDN

## 🌐 Browser Compatibility

| Browser | Support |
|---------|---------|
| Chrome | ✅ Full support |
| Firefox | ✅ Full support |
| Safari | ✅ Full support (iOS 11+) |
| Edge | ✅ Full support |
| Opera | ✅ Full support |

## 💡 Tips for Best Results

1. **Good Lighting**: Use well-lit environments for better face detection
2. **Face the Camera**: Look directly at the camera for accurate detection
3. **Clear Background**: Simple backgrounds work best
4. **Remove Accessories**: Take off hats or sunglasses
5. **Stable Position**: Hold still when capturing the photo

## 🛠️ Technical Details

### Technologies Used

- **HTML5**: Structure and Canvas API for image manipulation
- **CSS3**: Styling with gradients, flexbox, and grid
- **JavaScript (ES6+)**: Application logic and user interactions
- **face-api.js**: Face detection and facial landmark detection
- **WebRTC**: Camera access via getUserMedia API

### Project Structure

```
web-app/
├── index.html          # Main HTML file
├── css/
│   └── styles.css      # Styling and responsive design
├── js/
│   └── app.js          # Application logic
└── README.md           # This file
```

### How It Works

1. **Camera Access**: Uses WebRTC `getUserMedia()` to access the device camera
2. **Face Detection**: face-api.js analyzes the captured image to detect faces and facial landmarks
3. **Hair Region Calculation**: Based on detected facial landmarks, the app calculates where hair should be positioned
4. **Hair Rendering**: Canvas API draws the selected hairstyle with the chosen color as an overlay
5. **Export**: Canvas content is converted to PNG for download

## 🎨 Customization

### Adding New Hair Colors

Edit `js/app.js` and add to the `hairColors` object:

```javascript
this.hairColors = {
    // ... existing colors
    yourColor: '#HEXCODE'
};
```

### Adding New Hairstyles

1. Add the style name to the `hairStyles` array in `js/app.js`
2. Create a new drawing method:

```javascript
drawYourStyle(r) {
    // r = region object with x, y, width, height
    // Use this.previewCtx to draw on the canvas
    this.previewCtx.beginPath();
    // Your drawing code here
    this.previewCtx.fill();
}
```

3. Add the case to the `drawHair()` switch statement

## 🐛 Troubleshooting

**Camera not working:**
- Make sure you're using HTTPS or localhost
- Check browser permissions (Settings → Privacy → Camera)
- Try a different browser

**Face detection fails:**
- Ensure good lighting
- Face the camera directly
- Wait for models to fully load
- Check internet connection (models load from CDN)

**Models not loading:**
- Check your internet connection
- Try refreshing the page
- Check browser console for errors

**App not opening:**
- Make sure you're opening `index.html`, not other files
- Try using a local web server instead of opening directly
- Check browser compatibility

## 📄 License

This project is open source and available for educational and personal use.

## 🤝 Contributing

Feel free to submit issues or pull requests to improve the app!

## 🙏 Credits

- **face-api.js**: Face detection powered by [@vladmandic/face-api](https://github.com/vladmandic/face-api)
- Built with vanilla JavaScript for maximum compatibility

## 📞 Support

If you encounter any issues:
1. Check the troubleshooting section above
2. Make sure you're using a modern browser
3. Verify camera permissions are granted
4. Try using a local web server

---

**Enjoy trying on different hairstyles!** 💇‍♀️💇‍♂️
