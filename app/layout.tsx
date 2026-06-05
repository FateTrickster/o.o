import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI素养测评题库系统",
  description: "本地运行的 AI 素养测评题库管理 MVP"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
