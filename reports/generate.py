"""Generate the statutory PDF downloads used by the Compliance page."""

def _pdf(title: str, grower_name: str, season: str, headings: list[str], rows: list[list[object]]) -> bytes:
    """Render a compact dependency-free PDF report.

    The project runs on Windows without the native libraries required by
    WeasyPrint, so these reports use a small built-in PDF writer instead.
    """
    lines = [title, f"Grower: {grower_name} | Season: {season}", "", " | ".join(headings)]
    lines.extend(" | ".join(str(value) for value in row) for row in rows)
    if not rows:
        lines.append("No records for this season.")

    def escape_pdf(value: str) -> str:
        return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    commands = ["BT", "/F1 16 Tf", "50 790 Td"]
    for index, line in enumerate(lines):
        size = 16 if index == 0 else 10
        commands.append(f"/F1 {size} Tf")
        commands.append(f"({escape_pdf(line[:115])}) Tj")
        commands.append("0 -18 Td")
    commands.append("ET")
    stream = "\n".join(commands).encode("latin-1", "replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode())
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    pdf.extend(b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:]))
    pdf.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return bytes(pdf)


def licence_report_pdf(grower, contracts, paddocks, season: str) -> bytes:
    rows = [
        [contract.variety, f"{contract.area_contracted_ha:.1f}", f"${contract.price_per_kg:.2f}"]
        for contract in contracts
    ]
    rows.extend([[f"Paddock: {paddock.name}", f"{paddock.area_ha:.1f} ha", paddock.soil_type or "N/A"] for paddock in paddocks])
    return _pdf(
        "Licence Status Report",
        grower.name,
        season,
        ["Contract or Paddock", "Area", "Detail"],
        rows,
    )


def harvest_report_pdf(grower, harvests, season: str, price_per_kg: float) -> bytes:
    rows = [
        [
            harvest.paddock_name,
            harvest.variety,
            f"{harvest.area_ha:.1f}",
            f"{harvest.yield_kg_ha:.2f}",
            f"${harvest.yield_kg_ha * harvest.area_ha * price_per_kg:,.2f}",
        ]
        for harvest in harvests
    ]
    return _pdf(
        "Harvest Reconciliation Report",
        grower.name,
        season,
        ["Paddock", "Variety", "Area (ha)", "Yield (kg/ha)", "Gross Payment"],
        rows,
    )


def pesticide_log_pdf(grower, applications, season: str) -> bytes:
    rows = [
        [
            application.paddock_name,
            application.applied_date,
            application.chemical_name,
            f"{application.rate_L_ha:.2f}",
            application.withholding_days,
            application.harvest_date or "N/A",
        ]
        for application in applications
    ]
    return _pdf(
        "Pesticide Use Log",
        grower.name,
        season,
        ["Paddock", "Applied", "Chemical", "Rate (L/ha)", "WHP (days)", "Harvest Date"],
        rows,
    )
