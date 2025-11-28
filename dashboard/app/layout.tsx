import type { Metadata } from "next";
import "./globals.css";
import { TutorialProvider } from "@/components/Tutorial";

export const metadata: Metadata = {
  title: "Claude-Nine Dashboard",
  description: "AI Development Teams Orchestration Platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  // Apply dark mode immediately based on system preference
                  if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
                    document.documentElement.classList.add('dark');
                  }
                } catch (e) {}
              })();
            `,
          }}
        />
      </head>
      <body className="antialiased">
        <TutorialProvider>
          {children}
        </TutorialProvider>
      </body>
    </html>
  );
}
