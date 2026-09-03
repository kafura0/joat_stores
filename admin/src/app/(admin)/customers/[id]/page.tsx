"use client";

import { useRouter, useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { useCustomer } from "@/hooks/useCustomers";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { PageLoading } from "@/components/ui/LoadingSpinner";
import { formatCurrency, formatDate } from "@/lib/utils";

export default function CustomerDetailPage() {
  const router = useRouter();
  const params = useParams();
  const id = Number(params.id);

  const { data: customer, isLoading } = useCustomer(id);

  if (isLoading) return <PageLoading />;
  if (!customer) return <div className="p-8 text-center text-[var(--md-on-surface-variant)]">Customer not found</div>;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" onClick={() => router.back()}>
          <ArrowLeft size={16} />
        </Button>
        <div>
          <h1 className="text-2xl font-bold text-[var(--md-on-surface)]">{customer.name}</h1>
          <p className="text-sm text-[var(--md-on-surface-variant)]">{customer.email || customer.phone}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
          <CardContent>
            <p className="text-sm text-[var(--md-on-surface-variant)]">Total Orders</p>
            <p className="text-2xl font-bold text-[var(--md-on-surface)]">{customer.total_orders}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <p className="text-sm text-[var(--md-on-surface-variant)]">Total Spent</p>
            <p className="text-2xl font-bold text-[var(--md-on-surface)]">
              {formatCurrency(customer.total_spent)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <p className="text-sm text-[var(--md-on-surface-variant)]">Customer Since</p>
            <p className="text-2xl font-bold text-[var(--md-on-surface)]">
              {formatDate(customer.created_at)}
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <h2 className="font-semibold text-[var(--md-on-surface)]">Contact Information</h2>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-[var(--md-on-surface-variant)]">Name</p>
              <p className="font-medium text-[var(--md-on-surface)]">{customer.name}</p>
            </div>
            <div>
              <p className="text-[var(--md-on-surface-variant)]">Phone</p>
              <p className="font-medium text-[var(--md-on-surface)]">{customer.phone}</p>
            </div>
            <div>
              <p className="text-[var(--md-on-surface-variant)]">Email</p>
              <p className="font-medium text-[var(--md-on-surface)]">{customer.email || "\u2014"}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
