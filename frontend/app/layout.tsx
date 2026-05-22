import type { Metadata } from "next";
import { Archivo_Black, Noto_Sans_SC, Space_Mono, Work_Sans } from "next/font/google";
import { AuthProvider } from "@/lib/auth";
import { TopBar } from "@/components/top-bar";
import { Footer } from "@/components/footer";
import "./globals.css";

const archivoBlack = Archivo_Black({
  weight: "400",
  subsets: ["latin"],
  display: "swap",
});

const workSans = Work_Sans({
  subsets: ["latin"],
  display: "swap",
});

const spaceMono = Space_Mono({
  weight: ["400", "700"],
  subsets: ["latin"],
  display: "swap",
});

const notoSansSC = Noto_Sans_SC({
  weight: ["400", "500", "700"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Job Copilot — AI Job Search Companion",
  description: "Resume matching, mock interviews, career roadmap",
  icons: { icon: "/logo.png" },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${archivoBlack.className} ${workSans.className} ${spaceMono.className} ${notoSansSC.className}`}
    >
      <body className="font-[family-name:var(--font-body)]">
        <AuthProvider>
          <TopBar />
          <main className="pt-[60px] pb-[72px]">{children}</main>
          <Footer />
        </AuthProvider>
      </body>
    </html>
  );
}
