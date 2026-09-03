"use client";

import { Card, CardContent, CardHeader } from "@/components/ui/Card";

export default function ReportsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--md-on-surface)]">Reports</h1>
        <p className="text-sm text-[var(--md-on-surface-variant)]">Business analytics and reports</p>
      </div>

      <Card>
        <CardHeader>
          <h2 className="font-semibold text-[var(--md-on-surface)]">Sales Reports</h2>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-[var(--md-on-surface-variant)]">
            Detailed sales analytics, profit margins, and trends. Coming soon.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="font-semibold text-[var(--md-on-surface)]">Inventory Reports</h2>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-[var(--md-on-surface-variant)]">
            Stock movement history, dead stock analysis, and reorder reports.
            Coming soon.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
