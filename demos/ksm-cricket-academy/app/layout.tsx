import type { Metadata } from 'next';
import { Barlow_Condensed, Inter } from 'next/font/google';
import Nav from '@/components/nav';
import Footer from '@/components/footer';
import './globals.css';

const barlowCondensed = Barlow_Condensed({
  weight: ['400', '600', '700', '800'],
  subsets: ['latin'],
  variable: '--font-display',
  display: 'swap',
});

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'KSM Cricket Academy',
  description: 'Connecting cricket talent from village to state level. Join KSM for Rs. 100 a year.',
  keywords: ['cricket academy', 'cricket training', 'village cricket', 'district cricket', 'state cricket'],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${barlowCondensed.variable} ${inter.variable} antialiased`}>
        <Nav />
        <main>{children}</main>
        <Footer />
      </body>
    </html>
  );
}
