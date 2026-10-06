import Foundation
import AppKit
import PDFKit
let base = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
let requested: [String:[Int]] = ["JST_XH.pdf":[1,3], "JST_GH.pdf":[1,2], "FEETECH_SCS0009_A0.pdf":[3,4,8], "CAM_V1.pdf":[1], "CAM_V11.pdf":[1], "TI_SDAA284_CC.pdf":[3,4,5,6], "TE_55A0111_drawing.pdf":[1,2], "GCT_USB4151_drawing.pdf":[1,2,3]]
let out = base.appendingPathComponent("previews",isDirectory:true)
try FileManager.default.createDirectory(at: out, withIntermediateDirectories: true)
for (name, pages) in requested.sorted(by:{$0.key < $1.key}) {
 let src=base.appendingPathComponent("sources/"+name)
 guard let doc=PDFDocument(url:src) else {print("Not available: "+name); continue}
 var allText:[String]=[]
 for i in 0..<doc.pageCount { allText.append("PAGE \(i+1)\n"+(doc.page(at:i)?.string ?? "")) }
 try allText.joined(separator:"\n").write(to:out.appendingPathComponent(name+".txt"),atomically:true,encoding:.utf8)
 for n in pages {
  guard let page=doc.page(at:n-1) else {continue}
  let b=page.bounds(for:.mediaBox); let factor=2200.0/max(b.width,b.height)
  let img=page.thumbnail(of:NSSize(width:b.width*factor,height:b.height*factor),for:.mediaBox)
  let bitmap=NSBitmapImageRep(data:img.tiffRepresentation!)!
  try bitmap.representation(using:.png,properties:[:])!.write(to:out.appendingPathComponent(name+"_p\(n).png"))
 }
 print(name,doc.pageCount,"pages; rendered",pages)
}
