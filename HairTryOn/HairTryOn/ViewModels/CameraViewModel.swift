import SwiftUI
import AVFoundation
import Combine

class CameraViewModel: NSObject, ObservableObject {
    @Published var capturedImage: UIImage?
    @Published var processedImage: UIImage?
    @Published var selectedHairStyle: HairStyle?
    @Published var isShowingCamera = false
    @Published var isCameraAuthorized = false
    @Published var detectedFaces: [FaceDetector.FaceObservation] = []
    @Published var isProcessing = false
    @Published var errorMessage: String?

    private let faceDetector = FaceDetector()
    private let imageProcessor = ImageProcessor()

    private var captureSession: AVCaptureSession?
    private var photoOutput: AVCapturePhotoOutput?
    private var previewLayer: AVCaptureVideoPreviewLayer?

    override init() {
        super.init()
        checkCameraAuthorization()
    }

    func checkCameraAuthorization() {
        switch AVCaptureDevice.authorizationStatus(for: .video) {
        case .authorized:
            isCameraAuthorized = true
        case .notDetermined:
            AVCaptureDevice.requestAccess(for: .video) { [weak self] granted in
                DispatchQueue.main.async {
                    self?.isCameraAuthorized = granted
                }
            }
        case .denied, .restricted:
            isCameraAuthorized = false
            errorMessage = "Camera access is required to use this app"
        @unknown default:
            isCameraAuthorized = false
        }
    }

    func setupCamera(completion: @escaping (AVCaptureVideoPreviewLayer?) -> Void) {
        let session = AVCaptureSession()
        session.sessionPreset = .photo

        guard let device = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .front),
              let input = try? AVCaptureDeviceInput(device: device) else {
            completion(nil)
            return
        }

        if session.canAddInput(input) {
            session.addInput(input)
        }

        let output = AVCapturePhotoOutput()
        if session.canAddOutput(output) {
            session.addOutput(output)
        }

        let preview = AVCaptureVideoPreviewLayer(session: session)
        preview.videoGravity = .resizeAspectFill

        captureSession = session
        photoOutput = output
        previewLayer = preview

        DispatchQueue.global(qos: .userInitiated).async {
            session.startRunning()
            DispatchQueue.main.async {
                completion(preview)
            }
        }
    }

    func capturePhoto() {
        guard let photoOutput = photoOutput else { return }

        let settings = AVCapturePhotoSettings()
        photoOutput.capturePhoto(with: settings, delegate: self)
    }

    func processCapturedImage() {
        guard let image = capturedImage else { return }

        isProcessing = true
        errorMessage = nil

        faceDetector.detectFaces(in: image) { [weak self] faces in
            guard let self = self else { return }

            DispatchQueue.main.async {
                self.detectedFaces = faces
                self.isProcessing = false

                if faces.isEmpty {
                    self.errorMessage = "No face detected in the image"
                }
            }
        }
    }

    func applyHairStyle(_ hairStyle: HairStyle) {
        guard let image = capturedImage,
              let face = detectedFaces.first else { return }

        selectedHairStyle = hairStyle
        isProcessing = true

        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            guard let self = self else { return }

            let hairRegion = self.faceDetector.getHairRegion(
                from: face,
                imageSize: image.size
            )

            let processed = self.imageProcessor.applyHairOverlay(
                to: image,
                hairStyle: hairStyle,
                hairRegion: hairRegion
            )

            DispatchQueue.main.async {
                self.processedImage = processed
                self.isProcessing = false
            }
        }
    }

    func saveImage() {
        guard let image = processedImage ?? capturedImage else { return }

        imageProcessor.saveToPhotoLibrary(image: image) { [weak self] success, error in
            DispatchQueue.main.async {
                if success {
                    self?.errorMessage = "Image saved successfully!"
                } else {
                    self?.errorMessage = "Failed to save image: \(error?.localizedDescription ?? "Unknown error")"
                }
            }
        }
    }

    func reset() {
        capturedImage = nil
        processedImage = nil
        selectedHairStyle = nil
        detectedFaces = []
        errorMessage = nil
        isShowingCamera = false
    }

    func stopCamera() {
        captureSession?.stopRunning()
        captureSession = nil
        photoOutput = nil
        previewLayer = nil
    }
}

extension CameraViewModel: AVCapturePhotoCaptureDelegate {
    func photoOutput(
        _ output: AVCapturePhotoOutput,
        didFinishProcessingPhoto photo: AVCapturePhoto,
        error: Error?
    ) {
        if let error = error {
            DispatchQueue.main.async {
                self.errorMessage = "Photo capture error: \(error.localizedDescription)"
            }
            return
        }

        guard let imageData = photo.fileDataRepresentation(),
              let image = UIImage(data: imageData) else {
            DispatchQueue.main.async {
                self.errorMessage = "Failed to process captured photo"
            }
            return
        }

        DispatchQueue.main.async {
            self.capturedImage = image
            self.isShowingCamera = false
            self.stopCamera()
            self.processCapturedImage()
        }
    }
}
