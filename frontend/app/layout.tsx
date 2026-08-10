import './globals.css';
import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import { Inter, DM_Serif_Display } from 'next/font/google';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

const dmSerif = DM_Serif_Display({
  weight: '400',
  subsets: ['latin'],
  variable: '--font-dm-serif',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'Plum Claims AI',
  description: 'Autonomous medical claims intake & adjudication',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${dmSerif.variable}`}>
      <body className="font-sans bg-plum-900 text-text-primary antialiased min-h-screen">
        {children}
      </body>
    </html>
  );
}
