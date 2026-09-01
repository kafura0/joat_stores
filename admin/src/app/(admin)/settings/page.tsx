"use client";

import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { useAuthStore } from "@/stores/authStore";

export default function SettingsPage() {
  const user = useAuthStore((s) => s.user);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-sm text-gray-500">Store configuration</p>
      </div>

      <Card>
        <CardHeader>
          <h2 className="font-semibold">Store Profile</h2>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <p className="text-sm text-gray-600">Email</p>
              <p className="font-medium">{user?.email}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Role</p>
              <p className="font-medium capitalize">
                {user?.role?.replace("_", " ")}
              </p>
            </div>
            <Button disabled>Edit Store Profile</Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="font-semibold">Notifications</h2>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-600">
            Configure email and SMS notifications. Coming soon.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
