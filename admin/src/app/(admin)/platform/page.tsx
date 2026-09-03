"use client";

import { useState } from "react";
import {
  Store,
  Users,
  DollarSign,
  Activity,
  Plus,
  ArrowUpRight,
  ArrowDownRight,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Clock,
  ShoppingCart,
  UserX,
  CreditCard,
  RefreshCw,
} from "lucide-react";
import {
  usePlatformMetrics,
  usePlatformStores,
  usePlatformSubscriptions,
  usePlans,
  useCreateStore,
} from "@/hooks/usePlatform";
import { StatCardSkeleton } from "@/components/ui/StatCard";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { formatCurrency, formatDate } from "@/lib/utils";
import { useUIStore } from "@/stores/uiStore";
import { IOnboarding } from "@/hooks/usePlatform";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

const storeSchema = z.object({
  name: z.string().min(1, "Store name is required"),
  domain: z.string().min(1, "Domain is required"),
  tenant_type: z.string().min(1, "Store type is required"),
  owner_email: z.string().email("Invalid email"),
});

type StoreFormData = z.infer<typeof storeSchema>;

const statusVariant: Record<string, "success" | "warning" | "danger" | "info"> = {
  active: "success",
  trial: "info",
  suspended: "danger",
  inactive: "warning",
};

const typeColors: Record<string, string> = {
  retail: "bg-blue-50 text-blue-600 border-blue-100",
  restaurant: "bg-amber-50 text-amber-600 border-amber-100",
  bar: "bg-purple-50 text-purple-600 border-purple-100",
  contracting: "bg-emerald-50 text-emerald-600 border-emerald-100",
};

export default function PlatformPage() {
  const [showCreateStore, setShowCreateStore] = useState(false);
  const [onboarding, setOnboarding] = useState<IOnboarding | null>(null);
  const [onboardingStoreName, setOnboardingStoreName] = useState("");
  const addToast = useUIStore((s) => s.addToast);

  const { data: metrics, isLoading: metricsLoading } = usePlatformMetrics();
  const { data: stores } = usePlatformStores();
  const { data: plans } = usePlans();
  const createStore = useCreateStore();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<StoreFormData>({
    resolver: zodResolver(storeSchema),
    defaultValues: { tenant_type: "retail" },
  });

  const onSubmit = async (data: StoreFormData) => {
    try {
      const result = await createStore.mutateAsync({
        ...data,
        domain: data.domain.toLowerCase().replace(/[^a-z0-9.-]/g, ""),
      });
      addToast({ type: "success", message: "Store created successfully" });
      reset();
      setShowCreateStore(false);

      // Show onboarding dialog with credentials
      if (result.onboarding) {
        setOnboarding(result.onboarding);
        setOnboardingStoreName(result.name);
      }
    } catch {
      addToast({ type: "error", message: "Failed to create store" });
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-end justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-[var(--md-on-surface)]">
            Platform Overview
          </h2>
          <p className="mt-1 text-sm text-[var(--md-on-surface-variant)]">
            Monitor key metrics and recent activities across your network.
          </p>
        </div>
        <Button onClick={() => setShowCreateStore(true)}>
          <Plus size={16} className="mr-2" />
          Add Store
        </Button>
      </div>

      {/* Stats Grid — 4 columns */}
      {metricsLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <StatCardSkeleton key={i} />
          ))}
        </div>
      ) : (
        <>
          {/* Row 1: Core metrics */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard
              label="Total Stores"
              value={metrics?.stores.total ?? 0}
              icon={<Store size={20} />}
              change={`${metrics?.stores.new_mtd ?? 0} new this month`}
              changeType="up"
            />
            <MetricCard
              label="Active Stores"
              value={metrics?.stores.active ?? 0}
              icon={<Activity size={20} />}
              change={`${metrics?.stores.trial ?? 0} on trial`}
              changeType="neutral"
            />
            <MetricCard
              label="MRR"
              value={formatCurrency(metrics?.revenue.mrr ?? "0")}
              icon={<DollarSign size={20} />}
              change="Monthly recurring"
              changeType="up"
            />
            <MetricCard
              label="GMV (30d)"
              value={formatCurrency(metrics?.revenue.gmv_30d ?? "0")}
              icon={<TrendingUp size={20} />}
              change="Gross merchandise value"
              changeType="up"
            />
          </div>

          {/* Row 2: Growth & Health */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard
              label="Revenue MTD"
              value={formatCurrency(metrics?.revenue.revenue_mtd ?? "0")}
              icon={<CreditCard size={20} />}
              change={`${metrics?.orders.today ?? 0} orders today`}
              changeType="up"
            />
            <MetricCard
              label="Trial Conversion"
              value={`${metrics?.subscriptions.trial_conversion_rate ?? 0}%`}
              icon={<RefreshCw size={20} />}
              change="Trial to paid"
              changeType={Number(metrics?.subscriptions.trial_conversion_rate ?? 0) > 50 ? "up" : "down"}
            />
            <MetricCard
              label="Churn Rate"
              value={`${metrics?.health.churn_rate ?? 0}%`}
              icon={<UserX size={20} />}
              change={`${metrics?.health.dormant_stores ?? 0} dormant stores`}
              changeType={Number(metrics?.health.churn_rate ?? 0) < 5 ? "up" : "down"}
            />
            <MetricCard
              label="Expiring Soon"
              value={metrics?.subscriptions.expiring_soon ?? 0}
              icon={<AlertTriangle size={20} />}
              change="Subscriptions in 30d"
              changeType={Number(metrics?.subscriptions.expiring_soon ?? 0) > 5 ? "down" : "up"}
            />
          </div>

          {/* Row 3: Secondary metrics */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard
              label="Total Orders"
              value={metrics?.orders.total ?? 0}
              icon={<ShoppingCart size={20} />}
              change={`${metrics?.orders.last_30d ?? 0} in last 30d`}
              changeType="up"
            />
            <MetricCard
              label="Failed Renewals"
              value={metrics?.revenue.failed_renewals ?? 0}
              icon={<AlertTriangle size={20} />}
              change="Payment failures (30d)"
              changeType={Number(metrics?.revenue.failed_renewals ?? 0) > 0 ? "down" : "up"}
            />
            <MetricCard
              label="Dormant Stores"
              value={metrics?.stores.dormant ?? 0}
              icon={<Clock size={20} />}
              change="No activity in 30d"
              changeType="down"
            />
            <MetricCard
              label="Suspended"
              value={metrics?.stores.suspended ?? 0}
              icon={<UserX size={20} />}
              change="Account suspensions"
              changeType="down"
            />
          </div>
        </>
      )}

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Stores Table */}
        <div className="lg:col-span-8">
          <div className="premium-card overflow-hidden rounded-2xl border border-[var(--md-outline-variant)] bg-[var(--md-surface-container)] backdrop-blur-sm">
            <div className="flex items-center justify-between border-b border-[var(--md-outline-variant)] bg-[var(--md-surface-container)]/50 p-6">
              <h3 className="text-lg font-bold text-[var(--md-on-surface)]">
                All Stores
              </h3>
              <div className="flex items-center gap-2 text-xs text-[var(--md-on-surface-variant)]">
                <span className="rounded-full bg-[var(--md-success-container)] px-2 py-0.5 text-[var(--md-success)]">
                  {metrics?.stores.active ?? 0} active
                </span>
                <span className="rounded-full bg-[var(--md-tertiary-container)] px-2 py-0.5 text-[var(--md-tertiary)]">
                  {metrics?.stores.trial ?? 0} trial
                </span>
                <span className="rounded-full bg-[var(--md-error-container)] px-2 py-0.5 text-[var(--md-error)]">
                  {metrics?.stores.suspended ?? 0} suspended
                </span>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead className="border-b border-[var(--md-outline-variant)] bg-[var(--md-surface-container-high)]/50">
                  <tr>
                    <th className="px-6 py-3 text-xs font-semibold uppercase tracking-wider text-[var(--md-on-surface-variant)]">
                      Business Name
                    </th>
                    <th className="px-6 py-3 text-xs font-semibold uppercase tracking-wider text-[var(--md-on-surface-variant)]">
                      Type
                    </th>
                    <th className="px-6 py-3 text-xs font-semibold uppercase tracking-wider text-[var(--md-on-surface-variant)]">
                      Status
                    </th>
                    <th className="px-6 py-3 text-xs font-semibold uppercase tracking-wider text-[var(--md-on-surface-variant)]">
                      Created
                    </th>
                  </tr>
                </thead>
                <tbody className="text-sm">
                  {metrics?.recent_stores.map((store) => (
                    <tr
                      key={store.id}
                      className="border-b border-[var(--md-outline-variant)]/30 transition-colors hover:bg-[var(--md-surface-variant)]/50"
                    >
                      <td className="px-6 py-4 font-medium text-[var(--md-on-surface)]">
                        {store.name}
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize ${
                            typeColors[store.tenant_type] ?? "bg-gray-50 text-gray-600 border-gray-100"
                          }`}
                        >
                          {store.tenant_type}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <Badge variant={statusVariant[store.status] ?? "default"}>
                          {store.status}
                        </Badge>
                      </td>
                      <td className="px-6 py-4 text-[var(--md-on-surface-variant)]">
                        {store.created_at ? formatDate(store.created_at) : "\u2014"}
                      </td>
                    </tr>
                  ))}
                  {(!metrics?.recent_stores || metrics.recent_stores.length === 0) && (
                    <tr>
                      <td
                        colSpan={4}
                        className="px-6 py-12 text-center text-[var(--md-on-surface-variant)]"
                      >
                        No stores yet. Create your first store above.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right Column */}
        <div className="lg:col-span-4 flex flex-col gap-6">
          {/* Platform Health */}
          <div className="premium-card rounded-2xl border border-[var(--md-outline-variant)] bg-[var(--md-surface-container)] p-6 backdrop-blur-sm">
            <h3 className="mb-4 text-lg font-bold text-[var(--md-on-surface)]">
              Platform Health
            </h3>
            <div className="space-y-3">
              <HealthRow
                icon={<Activity size={16} />}
                label="API Uptime"
                value="99.99%"
                color="text-[var(--md-success)]"
              />
              <HealthRow
                icon={<Users size={16} />}
                label="Database Load"
                value="42%"
                color="text-[var(--md-on-surface)]"
              />
              <HealthRow
                icon={<RefreshCw size={16} />}
                label="Failed Renewals"
                value={`${metrics?.revenue.failed_renewals ?? 0}/mo`}
                color={Number(metrics?.revenue.failed_renewals ?? 0) > 0 ? "text-[var(--md-error)]" : "text-[var(--md-success)]"}
              />
              <HealthRow
                icon={<Clock size={16} />}
                label="Dormant Stores"
                value={`${metrics?.health.dormant_stores ?? 0}`}
                color={Number(metrics?.health.dormant_stores ?? 0) > 10 ? "text-[var(--md-warning)]" : "text-[var(--md-success)]"}
              />
            </div>
          </div>

          {/* Plan Distribution */}
          <div className="premium-card rounded-2xl border border-[var(--md-outline-variant)] bg-[var(--md-surface-container)] p-6 backdrop-blur-sm">
            <h3 className="mb-4 text-lg font-bold text-[var(--md-on-surface)]">
              Plan Distribution
            </h3>
            <div className="space-y-3">
              {metrics?.subscriptions.plan_distribution &&
                Object.entries(metrics.subscriptions.plan_distribution).map(
                  ([plan, count]) => (
                    <div
                      key={plan}
                      className="flex items-center justify-between"
                    >
                      <span className="text-sm font-medium text-[var(--md-on-surface)]">
                        {plan ?? "No Plan"}
                      </span>
                      <div className="flex items-center gap-2">
                        <div className="h-2 w-16 overflow-hidden rounded-full bg-[var(--md-surface-variant)]">
                          <div
                            className="h-full rounded-full bg-[var(--md-primary)]"
                            style={{
                              width: `${Math.min(
                                100,
                                ((count as number) /
                                  (metrics?.subscriptions.total ?? 1)) *
                                  100
                              )}%`,
                            }}
                          />
                        </div>
                        <span className="w-8 text-right text-xs font-semibold text-[var(--md-on-surface-variant)]">
                          {count as number}
                        </span>
                      </div>
                    </div>
                  )
                )}
              {(!metrics?.subscriptions.plan_distribution ||
                Object.keys(metrics.subscriptions.plan_distribution).length ===
                  0) && (
                <p className="py-4 text-center text-sm text-[var(--md-on-surface-variant)]">
                  No subscriptions yet
                </p>
              )}
            </div>
          </div>

          {/* Recent Signups */}
          <div className="premium-card flex-1 rounded-2xl border border-[var(--md-outline-variant)] bg-[var(--md-surface-container)] p-6 backdrop-blur-sm">
            <h3 className="mb-4 text-lg font-bold text-[var(--md-on-surface)]">
              Recent Signups
            </h3>
            <div className="space-y-3">
              {metrics?.recent_subscriptions.map((sub) => (
                <div
                  key={sub.id}
                  className="flex items-center gap-3 rounded-xl border border-[var(--md-outline-variant)]/30 p-3 transition-all hover:border-[var(--md-outline-variant)] hover:bg-[var(--md-surface-variant)]"
                >
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[var(--md-primary-container)]/20 text-sm font-bold text-[var(--md-primary)]">
                    {sub.store__name?.[0] ?? "S"}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-[var(--md-on-surface)]">
                      {sub.store__name ?? "Unknown"}
                    </p>
                    <p className="mt-0.5 truncate text-xs text-[var(--md-on-surface-variant)]">
                      {sub.created_at ? formatDate(sub.created_at) : "\u2014"} &middot;{" "}
                      {sub.plan__name ?? "No plan"}
                    </p>
                  </div>
                  <Badge variant={statusVariant[sub.status] ?? "default"}>
                    {sub.status}
                  </Badge>
                </div>
              ))}
              {(!metrics?.recent_subscriptions ||
                metrics.recent_subscriptions.length === 0) && (
                <p className="py-4 text-center text-sm text-[var(--md-on-surface-variant)]">
                  No subscriptions yet
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Create Store Dialog */}
      <Dialog
        open={showCreateStore}
        onClose={() => setShowCreateStore(false)}
        title="Create New Store"
      >
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input
            label="Store Name"
            {...register("name")}
            error={errors.name?.message}
            placeholder="e.g. Mama's Supermarket"
          />
          <Input
            label="Domain"
            {...register("domain")}
            error={errors.domain?.message}
            placeholder="e.g. mamas.ke"
          />
          <Select
            label="Store Type"
            options={[
              { value: "retail", label: "Retail" },
              { value: "restaurant", label: "Restaurant" },
              { value: "bar", label: "Bar / Nightclub" },
              { value: "contracting", label: "Contracting" },
            ]}
            {...register("tenant_type")}
            error={errors.tenant_type?.message}
          />
          <Input
            label="Owner Email"
            type="email"
            {...register("owner_email")}
            error={errors.owner_email?.message}
            placeholder="owner@example.com"
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setShowCreateStore(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={createStore.isPending}>
              {createStore.isPending ? "Creating..." : "Create Store"}
            </Button>
          </div>
        </form>
      </Dialog>

      {/* Onboarding Success Dialog */}
      <Dialog
        open={!!onboarding}
        onClose={() => setOnboarding(null)}
        title="Store Created Successfully!"
      >
        {onboarding && (
          <div className="space-y-4">
            <div className="rounded-xl border border-[var(--md-success)]/20 bg-[var(--md-success-container)] p-4 text-center">
              <p className="text-sm font-medium text-[var(--md-success)]">
                {onboardingStoreName} is now live!
              </p>
            </div>

            <div className="rounded-xl border border-[var(--md-outline-variant)] bg-[var(--md-surface-variant)] p-4">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-[var(--md-on-surface-variant)]">
                Owner Credentials
              </p>
              <p className="text-sm text-[var(--md-on-surface)]">
                Email: <span className="font-medium">{onboarding.owner_email}</span>
              </p>
              <p className="text-sm text-[var(--md-on-surface)]">
                Password:{" "}
                <span className="rounded bg-[var(--md-primary-container)] px-2 py-0.5 font-mono text-xs font-bold text-[var(--md-on-primary-container)]">
                  {onboarding.temporary_password}
                </span>
              </p>
              <p className="mt-2 text-xs text-[var(--md-on-surface-variant)]">
                Credentials sent via email to the store owner.
              </p>
            </div>

            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wider text-[var(--md-on-surface-variant)]">
                Store Links
              </p>
              <a
                href={onboarding.storefront_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-3 rounded-xl border border-[var(--md-outline-variant)] p-3 transition-all hover:border-[var(--md-primary)] hover:bg-[var(--md-surface-variant)]"
              >
                <div className="rounded-lg bg-[var(--md-primary-container)] p-2">
                  <svg className="h-5 w-5 text-[var(--md-primary)]" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 1.5H8.25A2.25 2.25 0 0 0 6 3.75v16.5a2.25 2.25 0 0 0 2.25 2.25h7.5A2.25 2.25 0 0 0 18 20.25V3.75a2.25 2.25 0 0 0-2.25-2.25H13.5m-3 0V3h3V1.5m-3 0h3m-3 18.75h3" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-semibold text-[var(--md-on-surface)]">
                    Storefront (PWA)
                  </p>
                  <p className="text-xs text-[var(--md-on-surface-variant)]">
                    {onboarding.storefront_url}
                  </p>
                </div>
              </a>
              <a
                href="https://joat-stores-admin.vercel.app/login"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-3 rounded-xl border border-[var(--md-outline-variant)] p-3 transition-all hover:border-[var(--md-primary)] hover:bg-[var(--md-surface-variant)]"
              >
                <div className="rounded-lg bg-[var(--md-tertiary-container)] p-2">
                  <svg className="h-5 w-5 text-[var(--md-tertiary)]" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 17.25v1.007a3 3 0 0 1-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0 1 15 18.257V17.25m6-12V15a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 15V5.25m18 0A2.25 2.25 0 0 0 18.75 3H5.25A2.25 2.25 0 0 0 3 5.25m18 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 7.41A2.25 2.25 0 0 1 2.25 5.498V5.25" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-semibold text-[var(--md-on-surface)]">
                    Admin Dashboard
                  </p>
                  <p className="text-xs text-[var(--md-on-surface-variant)]">
                    Login with owner credentials
                  </p>
                </div>
              </a>
            </div>

            <Button
              onClick={() => setOnboarding(null)}
              className="w-full"
            >
              Done
            </Button>
          </div>
        )}
      </Dialog>
    </div>
  );
}

/* ─── Helper Components ──────────────────────────────────────────────────── */

function MetricCard({
  label,
  value,
  icon,
  change,
  changeType,
}: {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  change?: string;
  changeType?: "up" | "down" | "neutral";
}) {
  return (
    <div className="premium-card rounded-2xl border border-[var(--md-outline-variant)] bg-[var(--md-surface-container)] p-6 backdrop-blur-sm transition-all duration-300 hover:shadow-[var(--shadow-elevated)] hover:-translate-y-0.5">
      <div className="mb-4 flex items-start justify-between">
        <span className="text-xs font-semibold uppercase tracking-widest text-[var(--md-on-surface-variant)]">
          {label}
        </span>
        <div className="rounded-lg bg-[var(--md-primary-container)] p-2">
          <span className="text-[var(--md-primary)]">{icon}</span>
        </div>
      </div>
      <div className="flex items-end justify-between">
        <span className="text-3xl font-bold tracking-tight text-[var(--md-on-surface)]">
          {value}
        </span>
        {change && (
          <span
            className={`flex items-center rounded-full px-2 py-0.5 text-xs font-bold ${
              changeType === "up"
                ? "bg-[var(--md-success-container)] text-[var(--md-success)]"
                : changeType === "down"
                  ? "bg-[var(--md-error-container)] text-[var(--md-error)]"
                  : "bg-[var(--md-surface-variant)] text-[var(--md-on-surface-variant)]"
            }`}
          >
            {changeType === "up" && <ArrowUpRight size={14} className="mr-0.5" />}
            {changeType === "down" && (
              <ArrowDownRight size={14} className="mr-0.5" />
            )}
            {change}
          </span>
        )}
      </div>
    </div>
  );
}

function HealthRow({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div className="flex items-center justify-between rounded-lg p-2 transition-colors hover:bg-[var(--md-surface-variant)]">
      <div className="flex items-center gap-3">
        <div className="rounded-md bg-[var(--md-on-surface-variant)]/10 p-1.5 text-[var(--md-on-surface-variant)]">
          {icon}
        </div>
        <span className="text-sm font-medium text-[var(--md-on-surface)]">
          {label}
        </span>
      </div>
      <span className={`text-sm font-semibold ${color}`}>{value}</span>
    </div>
  );
}
