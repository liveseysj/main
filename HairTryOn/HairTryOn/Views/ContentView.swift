import SwiftUI

struct ContentView: View {
    @StateObject private var viewModel = CameraViewModel()

    var body: some View {
        NavigationView {
            ZStack {
                LinearGradient(
                    gradient: Gradient(colors: [
                        Color.purple.opacity(0.3),
                        Color.blue.opacity(0.3)
                    ]),
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
                .edgesIgnoringSafeArea(.all)

                VStack(spacing: 20) {
                    if viewModel.capturedImage == nil {
                        welcomeView
                    } else {
                        editorView
                    }
                }
                .padding()
            }
            .navigationTitle("Hair Try-On")
            .navigationBarTitleDisplayMode(.inline)
            .fullScreenCover(isPresented: $viewModel.isShowingCamera) {
                if viewModel.isCameraAuthorized {
                    CameraOverlayView(viewModel: viewModel)
                } else {
                    VStack {
                        Text("Camera access is required")
                            .font(.headline)
                        Text("Please enable camera access in Settings")
                            .font(.subheadline)
                            .foregroundColor(.secondary)

                        Button("Open Settings") {
                            if let url = URL(string: UIApplication.openSettingsURLString) {
                                UIApplication.shared.open(url)
                            }
                        }
                        .padding()
                    }
                }
            }
        }
    }

    var welcomeView: some View {
        VStack(spacing: 30) {
            Spacer()

            VStack(spacing: 15) {
                Image(systemName: "camera.circle.fill")
                    .font(.system(size: 100))
                    .foregroundColor(.white)

                Text("Hair Try-On")
                    .font(.largeTitle)
                    .fontWeight(.bold)
                    .foregroundColor(.white)

                Text("Take a selfie and see yourself with different hairstyles and colors!")
                    .font(.body)
                    .multilineTextAlignment(.center)
                    .foregroundColor(.white.opacity(0.9))
                    .padding(.horizontal)
            }

            Spacer()

            VStack(spacing: 15) {
                Button(action: {
                    viewModel.checkCameraAuthorization()
                    if viewModel.isCameraAuthorized {
                        viewModel.isShowingCamera = true
                    }
                }) {
                    HStack {
                        Image(systemName: "camera.fill")
                        Text("Take Selfie")
                            .fontWeight(.semibold)
                    }
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.white)
                    .foregroundColor(.blue)
                    .cornerRadius(15)
                }

                Text("Features:")
                    .font(.headline)
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity, alignment: .leading)

                VStack(alignment: .leading, spacing: 8) {
                    FeatureRow(icon: "scissors", text: "10+ different hairstyles")
                    FeatureRow(icon: "paintbrush.fill", text: "12+ color options")
                    FeatureRow(icon: "face.smiling", text: "Face detection powered by AI")
                    FeatureRow(icon: "square.and.arrow.down", text: "Save your favorite looks")
                }
            }
            .padding(.bottom, 30)
        }
    }

    var editorView: some View {
        VStack(spacing: 20) {
            HairOverlayView(viewModel: viewModel)

            if !viewModel.detectedFaces.isEmpty {
                HairStyleSelectionView(viewModel: viewModel)
            }

            HStack(spacing: 15) {
                Button(action: {
                    viewModel.reset()
                }) {
                    HStack {
                        Image(systemName: "arrow.left")
                        Text("New Photo")
                    }
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.gray.opacity(0.2))
                    .foregroundColor(.primary)
                    .cornerRadius(10)
                }

                if viewModel.processedImage != nil {
                    Button(action: {
                        viewModel.saveImage()
                    }) {
                        HStack {
                            Image(systemName: "square.and.arrow.down")
                            Text("Save")
                        }
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.blue)
                        .foregroundColor(.white)
                        .cornerRadius(10)
                    }
                }
            }
            .padding(.horizontal)
        }
    }
}

struct FeatureRow: View {
    let icon: String
    let text: String

    var body: some View {
        HStack {
            Image(systemName: icon)
                .frame(width: 24)
                .foregroundColor(.white)
            Text(text)
                .foregroundColor(.white.opacity(0.9))
        }
    }
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}
