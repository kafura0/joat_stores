"use client";

import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useAuthStore } from "@/stores/authStore";

export default function SettingsPage() {
  const user = useAuthStore((s) => s.user);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--md-on-surface)]">Settings</h1>
        <p className="text-sm text-[var(--md-on-surface-variant)]">Store configuration</p>
      </div>

      <Card>
        <CardHeader>
          <h2 className="font-semibold text-[var(--md-on-surface)]">Store Profile</h2>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <p className="text-sm text-[var(--md-on-surface-variant)]">Email</p>
              <p className="font-medium text-[var(--md-on-surface)]">{user?.email}</p>
            </div>
            <div>
              <p className="text-sm text-[var(--md-on-surface-variant)]">Role</p>
              <p className="font-medium capitalize text-[var(--md-on-surface)]">
                {user?.role?.replace("_", " ")}
              </p>
            </div>
            <Button disabled>Edit Store Profile</Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="font-semibold text-[var(--md-on-surface)]">Notifications</h2>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-[var(--md-on-surface-variant)]">
            Configure email and SMS notifications. Coming soon.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
