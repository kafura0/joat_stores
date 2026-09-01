export default function WaiterLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b bg-white px-4 py-3">
        <h1 className="text-lg font-bold text-gray-900">JOAT STORES</h1>
      </header>
      <main className="mx-auto max-w-lg p-4">{children}</main>
    </div>
  );
}
