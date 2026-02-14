import SwiftUI

struct HairStyle: Identifiable, Hashable {
    let id = UUID()
    let name: String
    let type: HairStyleType
    let color: HairColor

    enum HairStyleType: String, CaseIterable {
        case long = "Long"
        case short = "Short"
        case bob = "Bob"
        case pixie = "Pixie"
        case curly = "Curly"
        case wavy = "Wavy"
        case straight = "Straight"
        case afro = "Afro"
        case buzz = "Buzz Cut"
        case mohawk = "Mohawk"
    }

    enum HairColor: String, CaseIterable {
        case black = "Black"
        case brown = "Brown"
        case blonde = "Blonde"
        case red = "Red"
        case auburn = "Auburn"
        case platinum = "Platinum"
        case pink = "Pink"
        case blue = "Blue"
        case purple = "Purple"
        case green = "Green"
        case silver = "Silver"
        case rainbow = "Rainbow"

        var color: Color {
            switch self {
            case .black: return .black
            case .brown: return Color(red: 0.4, green: 0.26, blue: 0.13)
            case .blonde: return Color(red: 0.98, green: 0.87, blue: 0.54)
            case .red: return Color(red: 0.72, green: 0.16, blue: 0.16)
            case .auburn: return Color(red: 0.55, green: 0.25, blue: 0.07)
            case .platinum: return Color(red: 0.95, green: 0.95, blue: 0.95)
            case .pink: return Color(red: 1.0, green: 0.41, blue: 0.71)
            case .blue: return Color(red: 0.0, green: 0.48, blue: 0.80)
            case .purple: return Color(red: 0.58, green: 0.44, blue: 0.86)
            case .green: return Color(red: 0.0, green: 0.5, blue: 0.0)
            case .silver: return Color(red: 0.75, green: 0.75, blue: 0.75)
            case .rainbow: return .purple
            }
        }
    }

    static let presets: [HairStyle] = {
        var styles: [HairStyle] = []

        for styleType in HairStyleType.allCases {
            for color in HairColor.allCases {
                styles.append(HairStyle(
                    name: "\(color.rawValue) \(styleType.rawValue)",
                    type: styleType,
                    color: color
                ))
            }
        }

        return styles
    }()
}
