// Hair Try-On App
class HairTryOnApp {
    constructor() {
        this.video = document.getElementById('video');
        this.canvas = document.getElementById('overlay');
        this.previewCanvas = document.getElementById('previewCanvas');
        this.ctx = this.canvas.getContext('2d');
        this.previewCtx = this.previewCanvas.getContext('2d');

        this.stream = null;
        this.capturedImage = null;
        this.detectedFace = null;
        this.modelsLoaded = false;

        this.selectedStyle = 'long';
        this.selectedColor = 'brown';

        this.hairStyles = [
            'long', 'short', 'bob', 'pixie', 'curly',
            'wavy', 'straight', 'afro', 'buzz', 'mohawk'
        ];

        this.hairColors = {
            black: '#000000',
            brown: '#4A2511',
            blonde: '#FAD787',
            red: '#B71C1C',
            auburn: '#8B4000',
            platinum: '#E8E8E8',
            pink: '#FF69B4',
            blue: '#1976D2',
            purple: '#9C27B0',
            green: '#388E3C',
            silver: '#B0B0B0',
            rainbow: '#9C27B0'
        };

        this.init();
    }

    async init() {
        this.setupEventListeners();
        await this.loadModels();
    }

    async loadModels() {
        const loadingMessage = document.getElementById('loadingMessage');
        loadingMessage.style.display = 'block';

        try {
            const MODEL_URL = 'https://cdn.jsdelivr.net/npm/@vladmandic/face-api/model/';
            await faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL);
            await faceapi.nets.faceLandmark68Net.loadFromUri(MODEL_URL);

            this.modelsLoaded = true;
            loadingMessage.style.display = 'none';
            console.log('Face detection models loaded');
        } catch (error) {
            console.error('Error loading models:', error);
            loadingMessage.innerHTML = '<p style="color: red;">Error loading face detection models. Please refresh the page.</p>';
        }
    }

    setupEventListeners() {
        document.getElementById('startButton').addEventListener('click', () => this.startCamera());
        document.getElementById('cancelButton').addEventListener('click', () => this.cancelCamera());
        document.getElementById('captureButton').addEventListener('click', () => this.capturePhoto());
        document.getElementById('newPhotoButton').addEventListener('click', () => this.reset());
        document.getElementById('saveButton').addEventListener('click', () => this.savePhoto());
        document.getElementById('resetButton').addEventListener('click', () => this.resetStyle());
    }

    async startCamera() {
        if (!this.modelsLoaded) {
            alert('Please wait for face detection models to load');
            return;
        }

        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: 'user',
                    width: { ideal: 640 },
                    height: { ideal: 480 }
                }
            });

            this.video.srcObject = this.stream;
            this.showScreen('cameraScreen');

            this.video.addEventListener('loadedmetadata', () => {
                this.canvas.width = this.video.videoWidth;
                this.canvas.height = this.video.videoHeight;
            });
        } catch (error) {
            console.error('Error accessing camera:', error);
            alert('Could not access camera. Please make sure you have granted camera permissions.');
        }
    }

    cancelCamera() {
        this.stopCamera();
        this.showScreen('welcomeScreen');
    }

    stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
    }

    async capturePhoto() {
        const captureCanvas = document.createElement('canvas');
        captureCanvas.width = this.video.videoWidth;
        captureCanvas.height = this.video.videoHeight;
        const captureCtx = captureCanvas.getContext('2d');

        captureCtx.save();
        captureCtx.scale(-1, 1);
        captureCtx.drawImage(this.video, -captureCanvas.width, 0, captureCanvas.width, captureCanvas.height);
        captureCtx.restore();

        this.capturedImage = captureCanvas;
        this.stopCamera();

        await this.detectFace();
        this.showEditor();
    }

    async detectFace() {
        const statusDiv = document.getElementById('detectionStatus');
        statusDiv.className = 'status-message info';
        statusDiv.textContent = 'Detecting face...';

        try {
            const detections = await faceapi
                .detectSingleFace(this.capturedImage, new faceapi.TinyFaceDetectorOptions())
                .withFaceLandmarks();

            if (detections) {
                this.detectedFace = detections;
                statusDiv.className = 'status-message success';
                statusDiv.textContent = '✓ Face detected! Choose a hairstyle below';
                document.getElementById('styleControls').style.display = 'block';
                this.renderStyleButtons();
                this.renderColorButtons();
                this.applyHairStyle();
            } else {
                this.detectedFace = null;
                statusDiv.className = 'status-message error';
                statusDiv.textContent = '✗ No face detected. Try taking another photo with better lighting.';
                document.getElementById('styleControls').style.display = 'none';
                this.drawPreview();
            }
        } catch (error) {
            console.error('Error detecting face:', error);
            statusDiv.className = 'status-message error';
            statusDiv.textContent = '✗ Error detecting face. Please try again.';
            this.drawPreview();
        }
    }

    showEditor() {
        this.showScreen('editorScreen');
    }

    renderStyleButtons() {
        const container = document.getElementById('styleButtons');
        container.innerHTML = '';

        this.hairStyles.forEach(style => {
            const btn = document.createElement('button');
            btn.className = 'style-btn';
            btn.textContent = this.capitalize(style);
            if (style === this.selectedStyle) {
                btn.classList.add('active');
            }
            btn.addEventListener('click', () => {
                this.selectedStyle = style;
                this.renderStyleButtons();
                this.applyHairStyle();
            });
            container.appendChild(btn);
        });
    }

    renderColorButtons() {
        const container = document.getElementById('colorButtons');
        container.innerHTML = '';

        Object.keys(this.hairColors).forEach(colorName => {
            const btn = document.createElement('button');
            btn.className = 'color-btn';
            if (colorName === this.selectedColor) {
                btn.classList.add('active');
            }

            const swatch = document.createElement('span');
            swatch.className = 'color-swatch';
            swatch.style.background = this.hairColors[colorName];

            const label = document.createElement('span');
            label.textContent = this.capitalize(colorName);

            btn.appendChild(swatch);
            btn.appendChild(label);

            btn.addEventListener('click', () => {
                this.selectedColor = colorName;
                this.renderColorButtons();
                this.applyHairStyle();
            });

            container.appendChild(btn);
        });
    }

    applyHairStyle() {
        if (!this.detectedFace) {
            this.drawPreview();
            return;
        }

        this.previewCanvas.width = this.capturedImage.width;
        this.previewCanvas.height = this.capturedImage.height;

        this.previewCtx.drawImage(this.capturedImage, 0, 0);

        const landmarks = this.detectedFace.landmarks;
        const hairRegion = this.calculateHairRegion(landmarks);

        this.drawHair(hairRegion);

        document.getElementById('saveButton').style.display = 'inline-flex';

        const currentStyleDiv = document.getElementById('currentStyle');
        const currentStyleText = document.getElementById('currentStyleText');
        currentStyleDiv.style.display = 'flex';
        currentStyleText.textContent = `Current: ${this.capitalize(this.selectedColor)} ${this.capitalize(this.selectedStyle)}`;
    }

    calculateHairRegion(landmarks) {
        const jawline = landmarks.getJawOutline();
        const topOfHead = jawline[jawline.length - 1];

        let leftMost = jawline[0];
        let rightMost = jawline[jawline.length - 1];

        jawline.forEach(point => {
            if (point.x < leftMost.x) leftMost = point;
            if (point.x > rightMost.x) rightMost = point;
        });

        const width = (rightMost.x - leftMost.x) * 1.2;
        const height = width * 0.8;
        const centerX = (leftMost.x + rightMost.x) / 2;

        return {
            x: centerX - width / 2,
            y: topOfHead.y - height,
            width: width,
            height: height
        };
    }

    drawHair(region) {
        this.previewCtx.globalAlpha = 0.75;
        this.previewCtx.fillStyle = this.hairColors[this.selectedColor];

        switch (this.selectedStyle) {
            case 'long':
                this.drawLongHair(region);
                break;
            case 'short':
                this.drawShortHair(region);
                break;
            case 'bob':
                this.drawBobHair(region);
                break;
            case 'pixie':
                this.drawPixieHair(region);
                break;
            case 'curly':
                this.drawCurlyHair(region);
                break;
            case 'wavy':
                this.drawWavyHair(region);
                break;
            case 'straight':
                this.drawStraightHair(region);
                break;
            case 'afro':
                this.drawAfroHair(region);
                break;
            case 'buzz':
                this.drawBuzzCut(region);
                break;
            case 'mohawk':
                this.drawMohawk(region);
                break;
        }

        this.previewCtx.globalAlpha = 1.0;
    }

    drawLongHair(r) {
        this.previewCtx.beginPath();
        this.previewCtx.moveTo(r.x, r.y);
        this.previewCtx.quadraticCurveTo(r.x, r.y + r.height / 2, r.x + r.width * 0.2, r.y + r.height);
        this.previewCtx.lineTo(r.x + r.width * 0.8, r.y + r.height);
        this.previewCtx.quadraticCurveTo(r.x + r.width, r.y + r.height / 2, r.x + r.width, r.y);
        this.previewCtx.closePath();
        this.previewCtx.fill();
    }

    drawShortHair(r) {
        const shortHeight = r.height * 0.5;
        this.previewCtx.beginPath();
        this.previewCtx.roundRect(r.x, r.y, r.width, shortHeight, r.width * 0.2);
        this.previewCtx.fill();
    }

    drawBobHair(r) {
        const bobHeight = r.height * 0.7;
        this.previewCtx.beginPath();
        this.previewCtx.moveTo(r.x, r.y);
        this.previewCtx.lineTo(r.x, r.y + bobHeight);
        this.previewCtx.quadraticCurveTo(r.x + r.width / 2, r.y + bobHeight + 20, r.x + r.width, r.y + bobHeight);
        this.previewCtx.lineTo(r.x + r.width, r.y);
        this.previewCtx.closePath();
        this.previewCtx.fill();
    }

    drawPixieHair(r) {
        const pixieHeight = r.height * 0.4;
        const pixieWidth = r.width * 0.8;
        const offsetX = r.width * 0.1;
        this.previewCtx.beginPath();
        this.previewCtx.roundRect(r.x + offsetX, r.y, pixieWidth, pixieHeight, r.width * 0.15);
        this.previewCtx.fill();
    }

    drawCurlyHair(r) {
        this.previewCtx.beginPath();
        this.previewCtx.moveTo(r.x, r.y);

        let currentX = r.x;
        const waveHeight = 15;
        const waveWidth = 20;

        while (currentX < r.x + r.width) {
            this.previewCtx.quadraticCurveTo(currentX + waveWidth / 2, r.y + waveHeight, currentX + waveWidth, r.y);
            this.previewCtx.quadraticCurveTo(currentX + waveWidth * 1.5, r.y - waveHeight, currentX + waveWidth * 2, r.y);
            currentX += waveWidth * 2;
        }

        this.previewCtx.lineTo(r.x + r.width, r.y + r.height);
        this.previewCtx.lineTo(r.x, r.y + r.height);
        this.previewCtx.closePath();
        this.previewCtx.fill();
    }

    drawWavyHair(r) {
        this.previewCtx.beginPath();
        this.previewCtx.moveTo(r.x, r.y);

        let currentX = r.x;
        const waveHeight = 8;
        const waveWidth = 30;

        while (currentX < r.x + r.width) {
            this.previewCtx.quadraticCurveTo(currentX + waveWidth / 2, r.y + waveHeight, currentX + waveWidth, r.y);
            currentX += waveWidth;
        }

        this.previewCtx.lineTo(r.x + r.width, r.y + r.height);
        this.previewCtx.lineTo(r.x, r.y + r.height);
        this.previewCtx.closePath();
        this.previewCtx.fill();
    }

    drawStraightHair(r) {
        this.previewCtx.fillRect(r.x, r.y, r.width, r.height);
    }

    drawAfroHair(r) {
        const afroWidth = r.width * 1.4;
        const afroHeight = r.height * 1.2;
        const centerX = r.x + r.width / 2;
        const centerY = r.y + r.height / 2 - r.height * 0.1;

        this.previewCtx.beginPath();
        this.previewCtx.ellipse(centerX, centerY, afroWidth / 2, afroHeight / 2, 0, 0, Math.PI * 2);
        this.previewCtx.fill();
    }

    drawBuzzCut(r) {
        const buzzHeight = r.height * 0.2;
        const buzzWidth = r.width * 0.8;
        const offsetX = r.width * 0.1;
        this.previewCtx.globalAlpha = 0.9;
        this.previewCtx.beginPath();
        this.previewCtx.roundRect(r.x + offsetX, r.y, buzzWidth, buzzHeight, r.width * 0.1);
        this.previewCtx.fill();
    }

    drawMohawk(r) {
        const centerWidth = r.width * 0.3;
        const mohawkHeight = r.height * 1.2;
        const centerX = r.x + r.width / 2;

        this.previewCtx.beginPath();
        this.previewCtx.roundRect(centerX - centerWidth / 2, r.y - r.height * 0.2, centerWidth, mohawkHeight, centerWidth * 0.2);
        this.previewCtx.fill();
    }

    drawPreview() {
        this.previewCanvas.width = this.capturedImage.width;
        this.previewCanvas.height = this.capturedImage.height;
        this.previewCtx.drawImage(this.capturedImage, 0, 0);
    }

    resetStyle() {
        this.selectedStyle = 'long';
        this.selectedColor = 'brown';
        this.renderStyleButtons();
        this.renderColorButtons();
        this.applyHairStyle();
    }

    savePhoto() {
        const link = document.createElement('a');
        link.download = `hair-tryon-${Date.now()}.png`;
        link.href = this.previewCanvas.toDataURL('image/png');
        link.click();

        const statusDiv = document.getElementById('detectionStatus');
        const originalText = statusDiv.textContent;
        statusDiv.className = 'status-message success';
        statusDiv.textContent = '✓ Photo saved successfully!';

        setTimeout(() => {
            statusDiv.className = 'status-message success';
            statusDiv.textContent = originalText;
        }, 3000);
    }

    reset() {
        this.capturedImage = null;
        this.detectedFace = null;
        this.selectedStyle = 'long';
        this.selectedColor = 'brown';
        document.getElementById('styleControls').style.display = 'none';
        document.getElementById('saveButton').style.display = 'none';
        document.getElementById('currentStyle').style.display = 'none';
        this.showScreen('welcomeScreen');
    }

    showScreen(screenId) {
        document.querySelectorAll('.screen').forEach(screen => {
            screen.classList.remove('active');
        });
        document.getElementById(screenId).classList.add('active');
    }

    capitalize(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new HairTryOnApp();
});
