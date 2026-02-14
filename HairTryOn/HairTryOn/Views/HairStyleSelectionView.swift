import SwiftUI

struct HairStyleSelectionView: View {
    @ObservedObject var viewModel: CameraViewModel
    @State private var selectedStyleType: HairStyle.HairStyleType = .long
    @State private var selectedColor: HairStyle.HairColor = .brown

    var filteredStyles: [HairStyle] {
        HairStyle.presets.filter { style in
            style.type == selectedStyleType && style.color == selectedColor
        }
    }

    var body: some View {
        VStack(spacing: 15) {
            Text("Choose Your Style")
                .font(.title2)
                .fontWeight(.bold)
                .padding(.top)

            VStack(alignment: .leading, spacing: 10) {
                Text("Hair Style")
                    .font(.headline)

                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 10) {
                        ForEach(HairStyle.HairStyleType.allCases, id: \.self) { styleType in
                            Button(action: {
                                selectedStyleType = styleType
                                applyCurrentSelection()
                            }) {
                                Text(styleType.rawValue)
                                    .padding(.horizontal, 15)
                                    .padding(.vertical, 8)
                                    .background(
                                        selectedStyleType == styleType ?
                                        Color.blue : Color.gray.opacity(0.2)
                                    )
                                    .foregroundColor(
                                        selectedStyleType == styleType ?
                                        .white : .primary
                                    )
                                    .cornerRadius(20)
                            }
                        }
                    }
                    .padding(.horizontal)
                }
            }

            VStack(alignment: .leading, spacing: 10) {
                Text("Hair Color")
                    .font(.headline)

                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 10) {
                        ForEach(HairStyle.HairColor.allCases, id: \.self) { color in
                            Button(action: {
                                selectedColor = color
                                applyCurrentSelection()
                            }) {
                                HStack {
                                    Circle()
                                        .fill(color.color)
                                        .frame(width: 20, height: 20)
                                        .overlay(
                                            Circle()
                                                .stroke(Color.white, lineWidth: 2)
                                        )

                                    Text(color.rawValue)
                                }
                                .padding(.horizontal, 12)
                                .padding(.vertical, 8)
                                .background(
                                    selectedColor == color ?
                                    Color.blue.opacity(0.2) : Color.gray.opacity(0.1)
                                )
                                .cornerRadius(20)
                                .overlay(
                                    RoundedRectangle(cornerRadius: 20)
                                        .stroke(
                                            selectedColor == color ? Color.blue : Color.clear,
                                            lineWidth: 2
                                        )
                                )
                            }
                        }
                    }
                    .padding(.horizontal)
                }
            }

            if let currentStyle = viewModel.selectedHairStyle {
                HStack {
                    Text("Current: \(currentStyle.name)")
                        .font(.subheadline)
                        .foregroundColor(.secondary)

                    Spacer()

                    Button("Reset") {
                        viewModel.processedImage = nil
                        viewModel.selectedHairStyle = nil
                    }
                    .font(.subheadline)
                }
                .padding(.horizontal)
            }
        }
        .padding(.bottom)
    }

    private func applyCurrentSelection() {
        if let style = filteredStyles.first {
            viewModel.applyHairStyle(style)
        }
    }
}
