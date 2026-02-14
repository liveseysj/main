import Vision
import UIKit
import CoreImage

class FaceDetector {
    struct FaceObservation {
        let boundingBox: CGRect
        let landmarks: VNFaceLandmarks2D?
        let roll: NSNumber?
        let yaw: NSNumber?
    }

    func detectFaces(in image: UIImage, completion: @escaping ([FaceObservation]) -> Void) {
        guard let cgImage = image.cgImage else {
            completion([])
            return
        }

        let request = VNDetectFaceLandmarksRequest { request, error in
            guard error == nil,
                  let observations = request.results as? [VNFaceObservation] else {
                completion([])
                return
            }

            let faceObservations = observations.map { observation in
                FaceObservation(
                    boundingBox: observation.boundingBox,
                    landmarks: observation.landmarks,
                    roll: observation.roll,
                    yaw: observation.yaw
                )
            }

            completion(faceObservations)
        }

        let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
        try? handler.perform([request])
    }

    func getHairRegion(from face: FaceObservation, imageSize: CGSize) -> CGRect {
        let faceRect = VNImageRectForNormalizedRect(
            face.boundingBox,
            Int(imageSize.width),
            Int(imageSize.height)
        )

        let hairHeight = faceRect.height * 0.6
        let hairWidth = faceRect.width * 1.2
        let hairX = faceRect.origin.x - (hairWidth - faceRect.width) / 2
        let hairY = faceRect.origin.y + faceRect.height

        return CGRect(
            x: hairX,
            y: hairY,
            width: hairWidth,
            height: hairHeight
        )
    }
}
