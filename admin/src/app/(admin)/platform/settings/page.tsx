"use client";

import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

export default function PlatformSettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--md-on-surface)]">Platform Settings</h1>
        <p className="text-sm text-[var(--md-on-surface-variant)]">Configure platform-wide settings</p>
      </div>

      <Card>
        <CardHeader>
          <h2 className="font-semibold text-[var(--md-on-surface)]">Subscription Plans</h2>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-[var(--md-on-surface-variant)]">
            Manage subscription plans for stores. Coming soon.
          </p>
          <Button className="mt-4" disabled>
            Manage Plans
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="font-semibold text-[var(--md-on-surface)]">Platform Configuration</h2>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-[var(--md-on-surface-variant)]">
            Platform-wide settings like default currency, tax rates, and feature
            flags. Coming soon.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
