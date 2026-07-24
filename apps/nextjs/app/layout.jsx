export const metadata = {
  title: "devvpush Next.js E2E",
  description: "Controlled Next.js deployment fixture",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
