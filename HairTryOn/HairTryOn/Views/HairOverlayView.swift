import SwiftUI

struct HairOverlayView: View {
    @ObservedObject var viewModel: CameraViewModel

    var body: some View {
        VStack {
            if let image = viewModel.processedImage ?? viewModel.capturedImage {
                Image(uiImage: image)
                    .resizable()
                    .aspectRatio(contentMode: .fit)
                    .frame(maxHeight: UIScreen.main.bounds.height * 0.5)
                    .cornerRadius(10)
            } else {
                Color.gray.opacity(0.3)
                    .frame(height: UIScreen.main.bounds.height * 0.5)
                    .cornerRadius(10)
                    .overlay(
                        Text("No image captured")
                            .foregroundColor(.gray)
                    )
            }

            if viewModel.isProcessing {
                ProgressView("Processing...")
                    .padding()
            } else if let errorMessage = viewModel.errorMessage {
                Text(errorMessage)
                    .foregroundColor(errorMessage.contains("success") ? .green : .red)
                    .padding()
            }

            if !viewModel.detectedFaces.isEmpty {
                Text("Face detected! Select a hairstyle below")
                    .font(.headline)
                    .foregroundColor(.green)
                    .padding(.top, 10)
            }
        }
    }
}
