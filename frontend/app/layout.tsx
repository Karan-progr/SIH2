import "./globals.css";

export const metadata = { title: "ImpactR | Social Intelligence", description: "Evidence-first narrative analysis" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}
