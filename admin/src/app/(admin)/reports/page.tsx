"use client";

import { Card, CardContent, CardHeader } from "@/components/ui/Card";

export default function ReportsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
        <p className="text-sm text-gray-500">Business analytics and reports</p>
      </div>

      <Card>
        <CardHeader>
          <h2 className="font-semibold">Sales Reports</h2>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-600">
            Detailed sales analytics, profit margins, and trends. Coming soon.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="font-semibold">Inventory Reports</h2>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-600">
            Stock movement history, dead stock analysis, and reorder reports.
            Coming soon.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
