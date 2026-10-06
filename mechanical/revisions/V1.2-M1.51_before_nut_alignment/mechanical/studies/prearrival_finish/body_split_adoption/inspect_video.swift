import Foundation
import AVFoundation
import AppKit

let asset = AVURLAsset(url: URL(fileURLWithPath: CommandLine.arguments[1]))
let out = URL(fileURLWithPath: CommandLine.arguments[2], isDirectory: true)
let generator = AVAssetImageGenerator(asset: asset)
generator.appliesPreferredTrackTransform = true
generator.requestedTimeToleranceBefore = .zero
generator.requestedTimeToleranceAfter = .zero
var results: [[String: Any]] = []
for (name, seconds) in [("bench_complete", 69.0), ("front_closed", 73.2), ("rear_locked", 78.3), ("overview", 85.0)] {
    var actual = CMTime.zero
    let image = try generator.copyCGImage(at: CMTime(seconds: seconds, preferredTimescale: 600), actualTime: &actual)
    let bitmap = NSBitmapImageRep(cgImage: image)
    let file = out.appendingPathComponent("video_\(name).png")
    try bitmap.representation(using: .png, properties: [:])!.write(to: file)
    results.append(["file": file.lastPathComponent, "requested_seconds": seconds,
                    "actual_seconds": actual.seconds, "width": image.width, "height": image.height])
}
let data = try JSONSerialization.data(withJSONObject: results, options: [.prettyPrinted, .sortedKeys])
try data.write(to: out.appendingPathComponent("decoded_video_frames.json"))
print("VIDEO_FRAMES_DECODED")
