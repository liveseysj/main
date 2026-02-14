import SwiftUI
import AVFoundation

struct CameraView: UIViewRepresentable {
    let viewModel: CameraViewModel

    func makeUIView(context: Context) -> UIView {
        let view = UIView(frame: .zero)
        view.backgroundColor = .black

        viewModel.setupCamera { previewLayer in
            guard let previewLayer = previewLayer else { return }

            DispatchQueue.main.async {
                previewLayer.frame = view.bounds
                view.layer.addSublayer(previewLayer)
            }
        }

        return view
    }

    func updateUIView(_ uiView: UIView, context: Context) {
        if let previewLayer = uiView.layer.sublayers?.first as? AVCaptureVideoPreviewLayer {
            DispatchQueue.main.async {
                previewLayer.frame = uiView.bounds
            }
        }
    }
}

struct CameraOverlayView: View {
    @ObservedObject var viewModel: CameraViewModel

    var body: some View {
        ZStack {
            CameraView(viewModel: viewModel)
                .edgesIgnoringSafeArea(.all)

            VStack {
                Spacer()

                HStack {
                    Button(action: {
                        viewModel.isShowingCamera = false
                        viewModel.stopCamera()
                    }) {
                        Image(systemName: "xmark.circle.fill")
                            .font(.system(size: 40))
                            .foregroundColor(.white)
                            .padding()
                    }

                    Spacer()

                    Button(action: {
                        viewModel.capturePhoto()
                    }) {
                        Circle()
                            .fill(Color.white)
                            .frame(width: 70, height: 70)
                            .overlay(
                                Circle()
                                    .stroke(Color.white, lineWidth: 3)
                                    .frame(width: 80, height: 80)
                            )
                    }

                    Spacer()

                    Color.clear
                        .frame(width: 40, height: 40)
                        .padding()
                }
                .padding(.bottom, 30)
            }
        }
    }
}
