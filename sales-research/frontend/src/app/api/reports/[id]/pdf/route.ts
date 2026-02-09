import { NextRequest, NextResponse } from 'next/server';
import puppeteer from 'puppeteer';

export async function GET(
    req: NextRequest,
    { params }: { params: { id: string } }
) {
    const id = params.id;
    if (!id) {
        return NextResponse.json({ error: 'Missing report ID' }, { status: 400 });
    }

    let browser;
    try {
        console.log(`Starting PDF generation for report: ${id}`);
        browser = await puppeteer.launch({
            headless: true,
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });

        const page = await browser.newPage();

        // Construct the URL to the report page in print mode
        const protocol = process.env.NODE_ENV === 'development' ? 'http' : 'https';
        const host = req.headers.get('host') || 'localhost:3000';
        const url = `${protocol}://${host}/reports?id=${id}&print=true`;

        console.log(`Navigating to: ${url}`);

        // Navigate and wait for content to load
        await page.goto(url, {
            waitUntil: 'networkidle0',
            timeout: 60000
        });

        // Additional delay to ensure all animations/dynamic content settle
        await new Promise(resolve => setTimeout(resolve, 2000));

        console.log('Generating PDF buffer...');
        const pdfBuffer = await page.pdf({
            format: 'A4',
            printBackground: true,
            margin: {
                top: '20mm',
                right: '20mm',
                bottom: '20mm',
                left: '20mm'
            },
            preferCSSPageSize: true
        });

        const filename = `analysis-report-${id}.pdf`;

        return new NextResponse(pdfBuffer, {
            status: 200,
            headers: {
                'Content-Type': 'application/pdf',
                'Content-Disposition': `attachment; filename="${filename}"`,
                'Content-Length': pdfBuffer.length.toString(),
            },
        });

    } catch (error: any) {
        console.error('SSR PDF Error:', error);
        return NextResponse.json(
            { error: 'Failed to generate PDF', details: error.message },
            { status: 500 }
        );
    } finally {
        if (browser) {
            await browser.close();
            console.log('Puppeteer browser closed');
        }
    }
}
