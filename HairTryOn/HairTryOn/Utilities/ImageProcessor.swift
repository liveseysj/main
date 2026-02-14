import UIKit
import CoreImage
import CoreGraphics

class ImageProcessor {
    private let context = CIContext()

    func applyHairOverlay(
        to image: UIImage,
        hairStyle: HairStyle,
        hairRegion: CGRect
    ) -> UIImage? {
        guard let cgImage = image.cgImage else { return nil }

        UIGraphicsBeginImageContextWithOptions(image.size, false, image.scale)
        defer { UIGraphicsEndImageContext() }

        guard let context = UIGraphicsGetCurrentContext() else { return nil }

        image.draw(at: .zero)

        context.saveGState()
        drawHairStyle(hairStyle, in: hairRegion, context: context)
        context.restoreGState()

        return UIGraphicsGetImageFromCurrentImageContext()
    }

    private func drawHairStyle(
        _ hairStyle: HairStyle,
        in region: CGRect,
        context: CGContext
    ) {
        let color = UIColor(hairStyle.color.color)

        switch hairStyle.type {
        case .long:
            drawLongHair(in: region, color: color, context: context)
        case .short:
            drawShortHair(in: region, color: color, context: context)
        case .bob:
            drawBobHair(in: region, color: color, context: context)
        case .pixie:
            drawPixieHair(in: region, color: color, context: context)
        case .curly:
            drawCurlyHair(in: region, color: color, context: context)
        case .wavy:
            drawWavyHair(in: region, color: color, context: context)
        case .straight:
            drawStraightHair(in: region, color: color, context: context)
        case .afro:
            drawAfroHair(in: region, color: color, context: context)
        case .buzz:
            drawBuzzCut(in: region, color: color, context: context)
        case .mohawk:
            drawMohawk(in: region, color: color, context: context)
        }
    }

    private func drawLongHair(in region: CGRect, color: UIColor, context: CGContext) {
        context.setFillColor(color.withAlphaComponent(0.7).cgColor)

        let path = UIBezierPath()
        path.move(to: CGPoint(x: region.minX, y: region.minY))
        path.addQuadCurve(
            to: CGPoint(x: region.minX + region.width * 0.2, y: region.maxY),
            controlPoint: CGPoint(x: region.minX, y: region.midY)
        )
        path.addLine(to: CGPoint(x: region.maxX - region.width * 0.2, y: region.maxY))
        path.addQuadCurve(
            to: CGPoint(x: region.maxX, y: region.minY),
            controlPoint: CGPoint(x: region.maxX, y: region.midY)
        )
        path.close()

        context.addPath(path.cgPath)
        context.fillPath()
    }

    private func drawShortHair(in region: CGRect, color: UIColor, context: CGContext) {
        context.setFillColor(color.withAlphaComponent(0.8).cgColor)

        let shortRegion = CGRect(
            x: region.minX,
            y: region.minY,
            width: region.width,
            height: region.height * 0.5
        )

        let path = UIBezierPath(roundedRect: shortRegion, cornerRadius: region.width * 0.2)
        context.addPath(path.cgPath)
        context.fillPath()
    }

    private func drawBobHair(in region: CGRect, color: UIColor, context: CGContext) {
        context.setFillColor(color.withAlphaComponent(0.75).cgColor)

        let bobRegion = CGRect(
            x: region.minX,
            y: region.minY,
            width: region.width,
            height: region.height * 0.7
        )

        let path = UIBezierPath()
        path.move(to: CGPoint(x: bobRegion.minX, y: bobRegion.minY))
        path.addLine(to: CGPoint(x: bobRegion.minX, y: bobRegion.maxY))
        path.addQuadCurve(
            to: CGPoint(x: bobRegion.maxX, y: bobRegion.maxY),
            controlPoint: CGPoint(x: bobRegion.midX, y: bobRegion.maxY + 20)
        )
        path.addLine(to: CGPoint(x: bobRegion.maxX, y: bobRegion.minY))
        path.close()

        context.addPath(path.cgPath)
        context.fillPath()
    }

    private func drawPixieHair(in region: CGRect, color: UIColor, context: CGContext) {
        context.setFillColor(color.withAlphaComponent(0.85).cgColor)

        let pixieRegion = CGRect(
            x: region.minX + region.width * 0.1,
            y: region.minY,
            width: region.width * 0.8,
            height: region.height * 0.4
        )

        let path = UIBezierPath(roundedRect: pixieRegion, cornerRadius: region.width * 0.15)
        context.addPath(path.cgPath)
        context.fillPath()
    }

    private func drawCurlyHair(in region: CGRect, color: UIColor, context: CGContext) {
        context.setFillColor(color.withAlphaComponent(0.7).cgColor)

        let path = UIBezierPath()
        path.move(to: CGPoint(x: region.minX, y: region.minY))

        var currentX = region.minX
        let waveHeight: CGFloat = 15
        let waveWidth: CGFloat = 20

        while currentX < region.maxX {
            path.addQuadCurve(
                to: CGPoint(x: currentX + waveWidth, y: region.midY),
                controlPoint: CGPoint(x: currentX + waveWidth / 2, y: region.minY + waveHeight)
            )
            path.addQuadCurve(
                to: CGPoint(x: currentX + waveWidth * 2, y: region.midY),
                controlPoint: CGPoint(x: currentX + waveWidth * 1.5, y: region.midY - waveHeight)
            )
            currentX += waveWidth * 2
        }

        path.addLine(to: CGPoint(x: region.maxX, y: region.maxY))
        path.addLine(to: CGPoint(x: region.minX, y: region.maxY))
        path.close()

        context.addPath(path.cgPath)
        context.fillPath()
    }

    private func drawWavyHair(in region: CGRect, color: UIColor, context: CGContext) {
        context.setFillColor(color.withAlphaComponent(0.75).cgColor)

        let path = UIBezierPath()
        path.move(to: CGPoint(x: region.minX, y: region.minY))

        var currentX = region.minX
        let waveHeight: CGFloat = 8
        let waveWidth: CGFloat = 30

        while currentX < region.maxX {
            path.addQuadCurve(
                to: CGPoint(x: currentX + waveWidth, y: region.minY),
                controlPoint: CGPoint(x: currentX + waveWidth / 2, y: region.minY + waveHeight)
            )
            currentX += waveWidth
        }

        path.addLine(to: CGPoint(x: region.maxX, y: region.maxY))
        path.addLine(to: CGPoint(x: region.minX, y: region.maxY))
        path.close()

        context.addPath(path.cgPath)
        context.fillPath()
    }

    private func drawStraightHair(in region: CGRect, color: UIColor, context: CGContext) {
        context.setFillColor(color.withAlphaComponent(0.8).cgColor)

        let path = UIBezierPath()
        path.move(to: CGPoint(x: region.minX, y: region.minY))
        path.addLine(to: CGPoint(x: region.minX, y: region.maxY))
        path.addLine(to: CGPoint(x: region.maxX, y: region.maxY))
        path.addLine(to: CGPoint(x: region.maxX, y: region.minY))
        path.close()

        context.addPath(path.cgPath)
        context.fillPath()
    }

    private func drawAfroHair(in region: CGRect, color: UIColor, context: CGContext) {
        context.setFillColor(color.withAlphaComponent(0.8).cgColor)

        let afroRegion = CGRect(
            x: region.minX - region.width * 0.2,
            y: region.minY - region.height * 0.3,
            width: region.width * 1.4,
            height: region.height * 1.2
        )

        let path = UIBezierPath(ovalIn: afroRegion)
        context.addPath(path.cgPath)
        context.fillPath()
    }

    private func drawBuzzCut(in region: CGRect, color: UIColor, context: CGContext) {
        context.setFillColor(color.withAlphaComponent(0.9).cgColor)

        let buzzRegion = CGRect(
            x: region.minX + region.width * 0.1,
            y: region.minY,
            width: region.width * 0.8,
            height: region.height * 0.2
        )

        let path = UIBezierPath(roundedRect: buzzRegion, cornerRadius: region.width * 0.1)
        context.addPath(path.cgPath)
        context.fillPath()
    }

    private func drawMohawk(in region: CGRect, color: UIColor, context: CGContext) {
        context.setFillColor(color.withAlphaComponent(0.8).cgColor)

        let centerWidth = region.width * 0.3
        let mohawkRegion = CGRect(
            x: region.midX - centerWidth / 2,
            y: region.minY - region.height * 0.2,
            width: centerWidth,
            height: region.height * 1.2
        )

        let path = UIBezierPath(roundedRect: mohawkRegion, cornerRadius: centerWidth * 0.2)
        context.addPath(path.cgPath)
        context.fillPath()
    }

    func saveToPhotoLibrary(image: UIImage, completion: @escaping (Bool, Error?) -> Void) {
        UIImageWriteToSavedPhotosAlbum(image, nil, nil, nil)
        completion(true, nil)
    }
}
