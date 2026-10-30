import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "紫微斗数 · 本地管理后台",
  description:
    "基于开源库 iztro 的紫微斗数排盘与本地数据库管理系统，支持查询、编辑、运限与批量导入。",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
