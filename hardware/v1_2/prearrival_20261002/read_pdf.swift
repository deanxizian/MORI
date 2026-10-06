import Foundation
import PDFKit
import AppKit

for input in CommandLine.arguments.dropFirst() {
    let url = URL(fileURLWithPath: input)
    guard let document = PDFDocument(url: url) else { fatalError("Cannot open \(input)") }
    var text = ""
    for i in 0..<document.pageCount {
        guard let page = document.page(at: i) else { continue }
        text += "\n--- PAGE \(i + 1) ---\n" + (page.string ?? "")
    }
    try text.write(to: url.deletingPathExtension().appendingPathExtension("txt"), atomically: true, encoding: .utf8)
    print(url.lastPathComponent, document.pageCount)
}
