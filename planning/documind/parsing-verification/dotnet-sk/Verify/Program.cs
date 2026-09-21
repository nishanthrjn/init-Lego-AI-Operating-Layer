// Design-verification harness only. Not production code, not part of DocuMind.
// References DocuMind-SK's Core/Domain projects read-only to observe actual
// runtime behavior of PdfDocumentParser / PlainTextParser against the shared
// fixture set. No DocuMind source file is modified.

using DocuMind.Core.Parsers;

var fixturesDir = @"D:\Work\Projects\implement-DocuMind-into-LegoAI\init-Lego-AI-Operating-Layer\planning\documind\parsing-verification\fixtures";
Console.WriteLine($"Fixtures dir: {fixturesDir}");

async Task RunPdf(string name)
{
    Console.WriteLine($"\n--- SK PdfDocumentParser: {name} ---");
    var parser = new PdfDocumentParser();
    await using var fs = File.OpenRead(Path.Combine(fixturesDir, name));
    try
    {
        var text = await parser.ParseAsync(fs, CancellationToken.None);
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
    Console.WriteLine($"\n--- SK PlainTextParser: {name} ---");
    var parser = new PlainTextParser();
    await using var fs = File.OpenRead(Path.Combine(fixturesDir, name));
    try
    {
        var text = await parser.ParseAsync(fs, CancellationToken.None);
        Console.WriteLine($"OK. Length={text.Length}");
        Console.WriteLine("Repr: " + System.Text.Json.JsonSerializer.Serialize(text));
    }
    catch (Exception ex)
    {
        Console.WriteLine($"THREW: {ex.GetType().FullName}: {ex.Message}");
    }
}

await RunText("01_empty_utf8.txt");
await RunText("02_ascii.txt");
await RunText("03_unicode_utf8.txt");
await RunText("04_multiline.txt");
await RunText("05_leading_trailing_ws.txt");
await RunText("06_markdown_opaque.md");
await RunText("07_html_opaque.html");
await RunText("15_invalid_utf8.txt");

await RunPdf("08_one_page_text.pdf");
await RunPdf("09_multi_page_text.pdf");
await RunPdf("10_blank_page_middle.pdf");
await RunPdf("11_unicode_pdf.pdf");
await RunPdf("12_image_only.pdf");
await RunPdf("13_malformed_truncated.pdf");
await RunPdf("13b_malformed_garbage.pdf");
await RunPdf("14_encrypted.pdf");

Console.WriteLine("\nDone.");
