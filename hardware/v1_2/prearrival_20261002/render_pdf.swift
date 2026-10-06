import Foundation
import PDFKit
import AppKit
let args = CommandLine.arguments
let url = URL(fileURLWithPath: args[1])
guard let document = PDFDocument(url: url) else { fatalError("Invalid PDF") }
for indexString in args.dropFirst(2) {
    let index = Int(indexString)!
    guard let page = document.page(at: index) else { continue }
    let rect = page.bounds(for: .mediaBox)
    let scale = CGFloat(1800) / rect.width
    let picture = page.thumbnail(of: CGSize(width: 1800, height: rect.height * scale), for: .mediaBox)
    guard let tiff = picture.tiffRepresentation,
          let bitmap = NSBitmapImageRep(data: tiff),
          let png = bitmap.representation(using: .png, properties: [:]) else { fatalError("PNG failed") }
    let output = url.deletingPathExtension().path + "_p\(index + 1).png"
    try png.write(to: URL(fileURLWithPath: output))
    print(output)
}
