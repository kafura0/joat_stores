"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { DataTable, TableSkeleton } from "@/components/ui/DataTable";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Dialog } from "@/components/ui/Dialog";
import { Input } from "@/components/ui/Input";
import { StatCard } from "@/components/ui/StatCard";
import { Card, CardHeader, CardContent } from "@/components/ui/Card";
import { formatDateTime } from "@/lib/utils";
import { useUIStore } from "@/stores/uiStore";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Star, Users, Trophy, Gift } from "lucide-react";

interface IStampCard {
  id: string;
  name: string;
  stamps_required: number;
  reward_description: string;
  points_per_stamp: number;
  is_active: boolean;
}

interface ICustomerProfile {
  id: string;
  customer_phone: string;
  customer_email: string;
  customer_name: string;
  order_count: number;
  total_spent: string;
  first_order_at: string | null;
  last_order_at: string | null;
}

interface ILoyaltyAccount {
  id: string;
  customer_phone: string;
  points_balance: number;
  lifetime_earned: number;
}

interface IPointsTransaction {
  id: string;
  delta: number;
  balance_after: number;
  source: string;
  reference: string;
  occurred_at: string;
}

const stampCardSchema = z.object({
  name: z.string().min(1, "Name is required"),
  stamps_required: z.string().min(1, "Required"),
  reward_description: z.string().min(1, "Reward description is required"),
  points_per_stamp: z.string().optional(),
});

type StampCardFormData = z.infer<typeof stampCardSchema>;

function useStampCards() {
  return useQuery({
    queryKey: ["stamp-cards"],
    queryFn: async () => {
      const { data } = await api.get("/loyalty/stamp-cards/");
      return data as IStampCard[];
    },
  });
}

function useCustomerProfiles() {
  return useQuery({
    queryKey: ["customer-profiles"],
    queryFn: async () => {
      const { data } = await api.get("/loyalty/customers/");
      return data as ICustomerProfile[];
    },
  });
}

function useCustomerDetail(phone: string | null) {
  return useQuery({
    queryKey: ["customer-detail", phone],
    queryFn: async () => {
      if (!phone) return null;
      const { data } = await api.get(`/loyalty/customers/${phone}/`);
      return data as ICustomerProfile;
    },
    enabled: !!phone,
  });
}

function useCustomerLoyalty(phone: string | null) {
  return useQuery({
    queryKey: ["customer-loyalty", phone],
    queryFn: async () => {
      if (!phone) return null;
      const { data } = await api.get(`/loyalty/account/?phone=${phone}`);
      return data as ILoyaltyAccount;
    },
    enabled: !!phone,
  });
}

function useCustomerTransactions(phone: string | null) {
  return useQuery({
    queryKey: ["customer-transactions", phone],
    queryFn: async () => {
      if (!phone) return [];
      const { data } = await api.get(`/loyalty/history/?phone=${phone}`);
      return data as IPointsTransaction[];
    },
    enabled: !!phone,
  });
}

export default function LoyaltyPage() {
  const queryClient = useQueryClient();
  const { addToast } = useUIStore();
  const [tab, setTab] = useState<"stamp-cards" | "customers">("stamp-cards");
  const [showCreate, setShowCreate] = useState(false);
  const [selectedPhone, setSelectedPhone] = useState<string | null>(null);

  const { data: stampCards = [], isLoading: loadingCards } = useStampCards();
  const { data: profiles = [], isLoading: loadingProfiles } = useCustomerProfiles();
  const { data: detail } = useCustomerDetail(selectedPhone);
  const { data: loyalty } = useCustomerLoyalty(selectedPhone);
  const { data: transactions = [] } = useCustomerTransactions(selectedPhone);

  const form = useForm<StampCardFormData>({
    resolver: zodResolver(stampCardSchema),
    defaultValues: {
      name: "",
      stamps_required: "10",
      reward_description: "",
      points_per_stamp: "0",
    },
  });

  const createMutation = useMutation({
    mutationFn: async (data: StampCardFormData) => {
      await api.post("/loyalty/stamp-cards/", {
        name: data.name,
        stamps_required: parseInt(data.stamps_required),
        reward_description: data.reward_description,
        points_per_stamp: parseInt(data.points_per_stamp || "0"),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["stamp-cards"] });
      setShowCreate(false);
      form.reset();
      addToast({ type: "success", message: "Stamp card created" });
    },
  });

  const totalPointsBalance = profiles.length; // placeholder — real data needs individual queries
  const totalCustomers = profiles.length;
  const topSpenders = [...profiles].sort((a, b) => parseFloat(b.total_spent) - parseFloat(a.total_spent)).slice(0, 5);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Loyalty & Rewards</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Manage stamp cards and view customer loyalty profiles.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard icon={<Star className="h-5 w-5" />} label="Stamp Cards" value={stampCards.length} />
        <StatCard icon={<Users className="h-5 w-5" />} label="Customers" value={totalCustomers} />
        <StatCard icon={<Trophy className="h-5 w-5" />} label="Active Programs" value={stampCards.filter(c => c.is_active).length} />
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-[var(--md-outline-variant)]">
        <button
          onClick={() => setTab("stamp-cards")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            tab === "stamp-cards"
              ? "border-[var(--md-primary)] text-[var(--md-primary)]"
              : "border-transparent text-[var(--md-on-surface-variant)] hover:text-[var(--md-on-surface)]"
          }`}
        >
          Stamp Cards
        </button>
        <button
          onClick={() => setTab("customers")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            tab === "customers"
              ? "border-[var(--md-primary)] text-[var(--md-primary)]"
              : "border-transparent text-[var(--md-on-surface-variant)] hover:text-[var(--md-on-surface)]"
          }`}
        >
          Customer Profiles
        </button>
      </div>

      {/* Stamp Cards Tab */}
      {tab === "stamp-cards" && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <Button onClick={() => setShowCreate(true)}>
              <Gift className="h-4 w-4 mr-2" /> New Stamp Card
            </Button>
          </div>

          {loadingCards ? (
            <TableSkeleton rows={3} cols={5} />
          ) : stampCards.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <Gift className="mx-auto mb-4 h-12 w-12 text-[var(--md-on-surface-variant)] opacity-40" />
                <p className="text-[var(--md-on-surface-variant)]">No stamp cards yet. Create one to start rewarding customers.</p>
              </CardContent>
            </Card>
          ) : (
            <DataTable
              columns={[
                { header: "Name", accessor: (c: IStampCard) => <span className="font-medium">{c.name}</span> },
                { header: "Stamps Required", accessor: (c: IStampCard) => c.stamps_required },
                { header: "Reward", accessor: (c: IStampCard) => c.reward_description },
                { header: "Bonus Points", accessor: (c: IStampCard) => c.points_per_stamp || "—" },
                {
                  header: "Status",
                  accessor: (c: IStampCard) => (
                    <Badge variant={c.is_active ? "success" : "default"}>
                      {c.is_active ? "Active" : "Inactive"}
                    </Badge>
                  ),
                },
              ]}
              data={stampCards}
              keyAccessor={(c) => c.id}
            />
          )}
        </div>
      )}

      {/* Customers Tab */}
      {tab === "customers" && (
        <div className="space-y-4">
          {loadingProfiles ? (
            <TableSkeleton rows={5} cols={5} />
          ) : profiles.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <Users className="mx-auto mb-4 h-12 w-12 text-[var(--md-on-surface-variant)] opacity-40" />
                <p className="text-[var(--md-on-surface-variant)]">No customer profiles yet. They appear after the first order.</p>
              </CardContent>
            </Card>
          ) : (
            <DataTable
              columns={[
                {
                  header: "Customer",
                  accessor: (p: ICustomerProfile) => (
                    <div>
                      <div className="font-medium">{p.customer_name || "Guest"}</div>
                      <div className="text-xs text-[var(--md-on-surface-variant)]">{p.customer_phone}</div>
                    </div>
                  ),
                },
                { header: "Orders", accessor: (p: ICustomerProfile) => p.order_count },
                {
                  header: "Total Spent",
                  accessor: (p: ICustomerProfile) => `KES ${parseFloat(p.total_spent).toLocaleString()}`,
                },
                {
                  header: "Last Order",
                  accessor: (p: ICustomerProfile) => p.last_order_at ? formatDateTime(p.last_order_at) : "—",
                },
                {
                  header: "",
                  accessor: (p: ICustomerProfile) => (
                    <Button size="sm" variant="ghost" onClick={() => setSelectedPhone(p.customer_phone)}>
                      View
                    </Button>
                  ),
                },
              ]}
              data={profiles}
              keyAccessor={(p) => p.id}
            />
          )}
        </div>
      )}

      {/* Customer Detail Dialog */}
      <Dialog open={!!selectedPhone} onClose={() => setSelectedPhone(null)} title={`Customer: ${selectedPhone}`}>
        {detail && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-[var(--md-on-surface-variant)]">Name</p>
                <p className="font-medium">{detail.customer_name || "Guest"}</p>
              </div>
              <div>
                <p className="text-xs text-[var(--md-on-surface-variant)]">Phone</p>
                <p className="font-medium">{detail.customer_phone}</p>
              </div>
              <div>
                <p className="text-xs text-[var(--md-on-surface-variant)]">Orders</p>
                <p className="font-medium">{detail.order_count}</p>
              </div>
              <div>
                <p className="text-xs text-[var(--md-on-surface-variant)]">Total Spent</p>
                <p className="font-medium">KES {parseFloat(detail.total_spent).toLocaleString()}</p>
              </div>
            </div>

            {loyalty && (
              <div className="rounded-lg bg-[var(--md-surface-container)] p-4">
                <p className="text-xs text-[var(--md-on-surface-variant)] mb-1">Loyalty Points</p>
                <p className="text-2xl font-bold text-[var(--md-primary)]">{loyalty.points_balance}</p>
                <p className="text-xs text-[var(--md-on-surface-variant)]">Lifetime earned: {loyalty.lifetime_earned}</p>
              </div>
            )}

            {transactions.length > 0 && (
              <div>
                <p className="text-sm font-medium mb-2">Recent Transactions</p>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {transactions.map((tx) => (
                    <div key={tx.id} className="flex items-center justify-between text-sm">
                      <div>
                        <span className={tx.delta > 0 ? "text-green-600" : "text-red-500"}>
                          {tx.delta > 0 ? "+" : ""}{tx.delta}
                        </span>
                        <span className="ml-2 text-[var(--md-on-surface-variant)]">{tx.source}</span>
                        {tx.reference && <span className="ml-1 text-xs text-[var(--md-on-surface-variant)]">({tx.reference})</span>}
                      </div>
                      <span className="text-xs text-[var(--md-on-surface-variant)]">
                        {formatDateTime(tx.occurred_at)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </Dialog>

      {/* Create Stamp Card Dialog */}
      <Dialog open={showCreate} onClose={() => setShowCreate(false)} title="Create Stamp Card">
        <form onSubmit={form.handleSubmit((data) => createMutation.mutate(data))} className="space-y-4">
          <Input label="Name" {...form.register("name")} placeholder="e.g. Coffee Club" />
          <Input label="Stamps Required" type="number" {...form.register("stamps_required")} />
          <Input label="Reward Description" {...form.register("reward_description")} placeholder="e.g. Free coffee after 10 stamps" />
          <Input label="Bonus Points on Completion" type="number" {...form.register("points_per_stamp")} />
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? "Creating..." : "Create"}
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
