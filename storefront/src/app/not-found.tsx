import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-4">
      <h1 className="text-4xl font-bold text-gray-900">404</h1>
      <p className="mt-2 text-gray-600">
        This page could not be found.
      </p>
      <Link
        href="/"
        className="mt-6 rounded-lg bg-gray-900 px-4 py-2 text-sm text-white transition hover:bg-gray-800"
      >
        Go home
      </Link>
    </main>
  );
}
