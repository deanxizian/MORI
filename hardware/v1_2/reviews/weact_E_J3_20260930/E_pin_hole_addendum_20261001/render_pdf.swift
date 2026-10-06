import Foundation
import AppKit
import PDFKit
let base=URL(fileURLWithPath:CommandLine.arguments[1])
for stem in ["61300821121_current","61300821821_current"] {
 let doc=PDFDocument(url:base.appendingPathComponent(stem+".pdf"))!
 let page=doc.page(at:0)!
 try page.string!.write(to:base.appendingPathComponent(stem+"_p1.txt"),atomically:true,encoding:.utf8)
 let im=page.thumbnail(of:NSSize(width:1500,height:2100),for:.mediaBox)
 let b=NSBitmapImageRep(data:im.tiffRepresentation!)!
 try b.representation(using:.png,properties:[:])!.write(to:base.appendingPathComponent(stem+"_p1.png"))
 print(stem, doc.pageCount, "pages")
}
