import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Portfolio AI Lab · Laboratorio de investigación",
  description: "Laboratorio local de investigación cuantitativa. Simulación PAPER con fixtures de prueba identificadas.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="es" data-theme="dark"><body>{children}</body></html>;
}
