import { vi, describe, it, expect, beforeEach } from "vitest"

const { saveMock, textMock, setFontSizeMock, setTextColorMock, autoTableMock } = vi.hoisted(() => ({
  saveMock: vi.fn(),
  textMock: vi.fn(),
  setFontSizeMock: vi.fn(),
  setTextColorMock: vi.fn(),
  autoTableMock: vi.fn(),
}))

vi.mock("jspdf", () => ({
  jsPDF: class {
    text = textMock
    setFontSize = setFontSizeMock
    setTextColor = setTextColorMock
    save = saveMock
  },
}))

vi.mock("jspdf-autotable", () => ({
  default: autoTableMock,
}))

import { exportToPdf } from "@/lib/pdf-export"

describe("exportToPdf", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("creates and saves a PDF document", () => {
    exportToPdf(
      "test.pdf",
      "Test Report",
      ["Name", "Value"],
      [["Alice", 42], ["Bob", 99]],
    )

    expect(saveMock).toHaveBeenCalledWith("test.pdf")
    expect(textMock).toHaveBeenCalledWith("Test Report", 14, 18)
    expect(autoTableMock).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({
        head: [["Name", "Value"]],
        body: [["Alice", "42"], ["Bob", "99"]],
      }),
    )
  })

  it("handles empty rows gracefully", () => {
    exportToPdf("empty.pdf", "Empty Report", ["A", "B"], [])

    expect(saveMock).toHaveBeenCalledWith("empty.pdf")
    expect(autoTableMock).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({
        head: [["A", "B"]],
        body: [],
      }),
    )
  })

  it("converts null values to empty strings", () => {
    exportToPdf(
      "nulls.pdf",
      "Null Test",
      ["Col"],
      [[null], [undefined], ["valid"]],
    )

    expect(autoTableMock).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({
        body: [[""], [""], ["valid"]],
      }),
    )
  })
})
