import Foundation
import AppKit
import PDFKit

// Read-only rendering fallback for PDFs requiring Adobe-Japan1 CMaps.
// Poppler on this host omitted text; PDFKit retains the catalogue labels.
for argument in CommandLine.arguments.dropFirst() {
    let url = URL(fileURLWithPath: argument)
    guard let document = PDFDocument(url: url) else { fatalError(argument) }
    var texts: [String] = []
    for index in 0..<document.pageCount {
        let page = document.page(at: index)!
        let bounds = page.bounds(for: .mediaBox)
        let factor = 2200.0 / max(bounds.width, bounds.height)
        let image = page.thumbnail(of: NSSize(width: bounds.width * factor,
                                              height: bounds.height * factor), for: .mediaBox)
        let bitmap = NSBitmapImageRep(data: image.tiffRepresentation!)!
        let output = url.deletingPathExtension().path + "_PDFKit_\(index + 1).png"
        try bitmap.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: output))
        texts.append("PAGE \(index + 1)\n" + (page.string ?? ""))
    }
    try texts.joined(separator: "\n").write(toFile: url.deletingPathExtension().path + "_PDFKit.txt", atomically: true, encoding: .utf8)
    print(url.lastPathComponent, document.pageCount)
}
