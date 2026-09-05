"""Dependency-free minimal PDF invoice renderer."""

from __future__ import annotations

from typing import Any


def render_invoice(invoice: dict[str, Any], order: dict[str, Any], customer: dict[str, Any]) -> bytes:
    lines = ["VYAPAAR PE CHARCHA - OPERATIONAL INVOICE", f"Invoice: {invoice['invoiceNumber']}",
             f"Customer: {customer['name']}", f"Order: {order['orderNumber']}",
             f"Delivery: {order['deliveryDate']}", ""]
    lines.extend(f"{line['label']}  {line['quantity']} {line['unit']}  INR {line['lineTotalPaise'] / 100:.2f}"
                 for line in order["lines"])
    lines.extend(["", f"TOTAL INR {invoice['totalPaise'] / 100:.2f}"])
    if order.get("collectionAmountPaise"):
        lines.append(f"COLLECTION RECORDED INR {order['collectionAmountPaise'] / 100:.2f}")
    lines.append("Not a statutory GST invoice.")
    escaped = [str(line).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") for line in lines]
    stream = "BT /F1 12 Tf 50 790 Td " + " ".join(
        ("0 -18 Td " if index else "") + f"({line}) Tj" for index, line in enumerate(escaped)) + " ET"
    objects = ["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
               f"<< /Length {len(stream.encode())} >>\nstream\n{stream}\nendstream",
               "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    output = b"%PDF-1.4\n"; offsets = [0]
    for index, item in enumerate(objects, start=1):
        offsets.append(len(output)); output += f"{index} 0 obj\n{item}\nendobj\n".encode("latin-1", "replace")
    xref = len(output); output += f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode()
    output += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
    output += f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return output
