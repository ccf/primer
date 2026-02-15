import { jsPDF } from "jspdf"
import autoTable from "jspdf-autotable"

export function exportToPdf(
  filename: string,
  title: string,
  headers: string[],
  rows: (string | number | null | undefined)[][],
) {
  const doc = new jsPDF({ orientation: "landscape" })

  // Title
  doc.setFontSize(16)
  doc.text(title, 14, 18)

  // Generated date
  doc.setFontSize(9)
  doc.setTextColor(120, 120, 120)
  doc.text(`Generated ${new Date().toLocaleDateString()}`, 14, 25)
  doc.setTextColor(0, 0, 0)

  // Table
  autoTable(doc, {
    startY: 30,
    head: [headers],
    body: rows.map((row) => row.map((val) => (val == null ? "" : String(val)))),
    headStyles: {
      fillColor: [99, 102, 241], // Primer Indigo #6366F1
      fontSize: 9,
    },
    bodyStyles: {
      fontSize: 8,
    },
    styles: {
      cellPadding: 3,
    },
  })

  doc.save(filename)
}
