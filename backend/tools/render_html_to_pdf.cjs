const fs = require('fs');
const path = require('path');

async function main() {
  const [, , inputHtmlPath, outputPdfPath] = process.argv;

  if (!inputHtmlPath || !outputPdfPath) {
    throw new Error('Usage: node render_html_to_pdf.cjs <input_html_path> <output_pdf_path>');
  }

  const htmlPath = path.resolve(inputHtmlPath);
  const pdfPath = path.resolve(outputPdfPath);

  if (!fs.existsSync(htmlPath)) {
    throw new Error(`Input HTML does not exist: ${htmlPath}`);
  }

  const html = fs.readFileSync(htmlPath, 'utf8');
  const { chromium } = require('playwright');

  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage();
    await page.setContent(html, { waitUntil: 'networkidle' });
    await page.pdf({
      path: pdfPath,
      format: 'A4',
      printBackground: true,
      margin: {
        top: '18mm',
        right: '14mm',
        bottom: '18mm',
        left: '14mm'
      }
    });
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error?.stack || String(error));
  process.exit(1);
});
