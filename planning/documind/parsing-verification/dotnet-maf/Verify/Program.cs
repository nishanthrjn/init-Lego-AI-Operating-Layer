// Design-verification harness only. Not production code, not part of DocuMind.
// References DocuMind-AgentFramework's Core/Domain projects read-only to observe
// actual runtime behavior of PdfDocumentParser / PlainTextParser against the
// shared fixture set. No DocuMind source file is modified.
//
// IVisionExtractionService is stubbed with a canned, offline response ONLY to
// confirm that the OCR fallback branch is actually reached for a low-text-yield
// PDF -- per instruction, no paid/network AI call is made for this gate. OCR
// content quality is explicitly NOT being characterized here (out of v1 scope).

using DocuMind.Core.Parsers;
using DocuMind.Domain.Interfaces;

var fixturesDir = @"D:\Work\Projects\implement-DocuMind-into-LegoAI\init-Lego-AI-Operating-Layer\planning\documind\parsing-verification\fixtures";

async Task RunPdf(IVisionExtractionService vision, string name)
{
    Console.WriteLine($"\n--- MAF PdfDocumentParser: {name} ---");
    var parser = new PdfDocumentParser(vision);
    await using var fs = File.OpenRead(Path.Combine(fixturesDir, name));
    try
    {
        var text = await parser.ParseAsync(fs, "application/pdf", CancellationToken.None);
        Console.WriteLine($"OK. Length={text.Length}");
        Console.WriteLine("Repr: " + System.Text.Json.JsonSerializer.Serialize(text));
    }
    catch (Exception ex)
    {
        Console.WriteLine($"THREW: {ex.GetType().FullName}: {ex.Message}");
    }
}

async Task RunText(string name)
{
    Console.WriteLine($"\n--- MAF PlainTextParser: {name} ---");
    var parser = new PlainTextParser();
    await using var fs = File.OpenRead(Path.Combine(fixturesDir, name));
    try
    {
        var text = await parser.ParseAsync(fs, "text/plain", CancellationToken.None);
        Console.WriteLine($"OK. Length={text.Length}");
        Console.WriteLine("Repr: " + System.Text.Json.JsonSerializer.Serialize(text));
    }
    catch (Exception ex)
    {
        Console.WriteLine($"THREW: {ex.GetType().FullName}: {ex.Message}");
    }
}

var noCallVision = new NoCallVisionExtractionService();
var stubVision = new StubVisionExtractionService();

await RunText("01_empty_utf8.txt");
await RunText("15_invalid_utf8.txt");

Console.WriteLine("\n=== Deterministic-path fixtures (real text layer, OCR should NOT be invoked) ===");
await RunPdf(noCallVision, "08_one_page_text.pdf");
await RunPdf(noCallVision, "09_multi_page_text.pdf");
await RunPdf(noCallVision, "10_blank_page_middle.pdf");
await RunPdf(noCallVision, "11_unicode_pdf.pdf");
await RunPdf(noCallVision, "13_malformed_truncated.pdf");
await RunPdf(noCallVision, "13b_malformed_garbage.pdf");
await RunPdf(noCallVision, "14_encrypted.pdf");

Console.WriteLine("\n=== Image-only fixture (expected to fall back to OCR -- using an offline stub, not a real model) ===");
await RunPdf(stubVision, "12_image_only.pdf");
Console.WriteLine($"Offline OCR stub was invoked: {stubVision.WasInvoked} (confirms wiring only; content quality not characterized)");

Console.WriteLine("\nDone.");

// Throws if ever called -- proves the deterministic-path fixtures never reach OCR.
sealed class NoCallVisionExtractionService : IVisionExtractionService
{
    public Task<string> ExtractTextAsync(byte[] imageBytes, string mediaType, CancellationToken ct)
        => throw new InvalidOperationException("OCR should not have been invoked for this fixture.");
}

// Offline stub confirming only that the fallback branch is reached; no network/model call.
sealed class StubVisionExtractionService : IVisionExtractionService
{
    public bool WasInvoked { get; private set; }
    public Task<string> ExtractTextAsync(byte[] imageBytes, string mediaType, CancellationToken ct)
    {
        WasInvoked = true;
        return Task.FromResult("[STUB OCR OUTPUT -- not a real model call]");
    }
}
