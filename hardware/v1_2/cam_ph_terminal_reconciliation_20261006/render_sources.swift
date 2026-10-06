import Foundation
import AppKit
import PDFKit
let base = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
let pages: [String:[Int]] = ["JST_PH.pdf":[2,3], "JST_SH.pdf":[1,2], "JST_SPH004_crimp_2001.pdf":[1], "JST_crimp_precautions.pdf":[1,2,3,4], "JST_handling_precautions.pdf":[2,3,4]]
let out = base.appendingPathComponent("previews", isDirectory:true)
try FileManager.default.createDirectory(at:out,withIntermediateDirectories:true)
for (name, indices) in pages.sorted(by:{$0.key < $1.key}) {
    guard let doc = PDFDocument(url:base.appendingPathComponent("sources/"+name)) else { print("Unavailable",name);continue }
    var all:[String]=[]
    for i in 0..<doc.pageCount { all.append("PAGE \(i+1)\n"+(doc.page(at:i)?.string ?? "")) }
    try all.joined(separator:"\n").write(to:out.appendingPathComponent(name+".txt"),atomically:true,encoding:.utf8)
    for n in indices {
        guard let p=doc.page(at:n-1) else { continue }
        let b=p.bounds(for:.mediaBox), s=2200.0/max(p.bounds(for:.mediaBox).width,p.bounds(for:.mediaBox).height)
        let i=p.thumbnail(of:NSSize(width:b.width*s,height:b.height*s),for:.mediaBox)
        let bitmap=NSBitmapImageRep(data:i.tiffRepresentation!)!
        try bitmap.representation(using:.png,properties:[:])!.write(to:out.appendingPathComponent(name+"_p\(n).png"))
    }
    print(name,doc.pageCount,"pages; rendered",indices)
}
