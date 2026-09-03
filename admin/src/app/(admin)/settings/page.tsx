"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Save, Image, AlertTriangle } from "lucide-react";
import { useStoreSettings, useUpdateStoreSettings } from "@/hooks/useStoreSettings";
import { useAuthStore } from "@/stores/authStore";
import { useUIStore } from "@/stores/uiStore";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { PageLoading } from "@/components/ui/LoadingSpinner";

const schema = z.object({
  tagline: z.string().optional(),
  logo_url: z.string().url().or(z.literal("")).optional(),
  low_stock_threshold: z.number().min(0).max(1000),
  tax_rate: z.number().min(0).max(100),
  tax_inclusive: z.boolean(),
  currency_symbol: z.string().min(1).max(10),
  receipt_header: z.string().optional(),
  receipt_footer: z.string().optional(),
});

type FormData = z.infer<typeof schema>;

export default function SettingsPage() {
  const user = useAuthStore((s) => s.user);
  const addToast = useUIStore((s) => s.addToast);
  const { data: settings, isLoading } = useStoreSettings();
  const updateSettings = useUpdateStoreSettings();
  const [logoPreview, setLogoPreview] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isDirty },
    reset,
    watch,
    setValue,
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    values: settings
      ? {
          tagline: settings.tagline ?? "",
          logo_url: settings.logo_url ?? "",
          low_stock_threshold: settings.low_stock_threshold ?? 5,
          tax_rate: (settings.tax_rate ?? 0.16) * 100,
          tax_inclusive: settings.tax_inclusive ?? true,
          currency_symbol: settings.currency_symbol ?? "KES",
          receipt_header: settings.receipt_header ?? "",
          receipt_footer: settings.receipt_footer ?? "",
        }
      : undefined,
  });

  const logoUrl = watch("logo_url");

  const onSubmit = async (data: FormData) => {
    try {
      await updateSettings.mutateAsync({
        ...data,
        tax_rate: data.tax_rate / 100,
      });
      addToast({ type: "success", message: "Settings saved" });
      reset(data);
    } catch {
      addToast({ type: "error", message: "Failed to save settings" });
    }
  };

  if (isLoading) return <PageLoading />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--md-on-surface)]">Settings</h1>
        <p className="text-sm text-[var(--md-on-surface-variant)]">Store configuration</p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Logo & Branding */}
        <Card>
          <CardHeader>
            <h2 className="font-semibold text-[var(--md-on-surface)]">Logo & Branding</h2>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-start gap-6">
              {/* Logo preview */}
              <div className="flex-shrink-0">
                <div className="h-24 w-24 overflow-hidden rounded-2xl border-2 border-dashed border-[var(--md-outline-variant)] bg-[var(--md-surface-variant)]">
                  {logoUrl ? (
                    <img
                      src={logoUrl}
                      alt="Store logo"
                      className="h-full w-full object-cover"
                      onError={(e) => {
                        (e.target as HTMLImageElement).src = "";
                        setLogoPreview(null);
                      }}
                    />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center">
                      <Image size={32} className="text-[var(--md-on-surface-variant)]" />
                    </div>
                  )}
                </div>
              </div>

              {/* Logo URL input */}
              <div className="flex-1 space-y-3">
                <Input
                  label="Logo URL"
                  {...register("logo_url")}
                  placeholder="https://example.com/logo.png"
                  error={errors.logo_url?.message}
                />
                <p className="text-xs text-[var(--md-on-surface-variant)]">
                  Paste a URL to your logo image. Recommended: 200x200px, PNG or SVG.
                </p>
                {logoUrl && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setValue("logo_url", "", { shouldDirty: true });
                      setLogoPreview(null);
                    }}
                  >
                    Remove logo
                  </Button>
                )}
              </div>
            </div>

            <Input
              label="Store Tagline"
              {...register("tagline")}
              placeholder="e.g. Best drinks in town"
            />
            <Input
              label="Currency Symbol"
              {...register("currency_symbol")}
              error={errors.currency_symbol?.message}
            />
          </CardContent>
        </Card>

        {/* Tax Configuration */}
        <Card>
          <CardHeader>
            <h2 className="font-semibold text-[var(--md-on-surface)]">Tax Configuration</h2>
          </CardHeader>
          <CardContent className="space-y-4">
            <Input
              label="Tax Rate (%)"
              type="number"
              step="0.01"
              {...register("tax_rate", { valueAsNumber: true })}
              error={errors.tax_rate?.message}
              placeholder="16"
            />
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="tax_inclusive"
                {...register("tax_inclusive")}
                className="h-4 w-4 rounded border-[var(--md-outline)] accent-[var(--md-primary)]"
              />
              <label htmlFor="tax_inclusive" className="text-sm text-[var(--md-on-surface-variant)]">
                Tax-inclusive pricing (prices include tax)
              </label>
            </div>
            <div className="rounded-xl border border-[var(--md-outline-variant)] bg-[var(--md-surface-variant)] p-3">
              <div className="flex items-start gap-2">
                <AlertTriangle size={16} className="mt-0.5 text-[var(--md-on-surface-variant)]" />
                <p className="text-xs text-[var(--md-on-surface-variant)]">
                  Kenya standard: 16% VAT, tax-inclusive. Prices displayed to customers include tax.
                  The tax amount is calculated and shown on receipts.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Inventory Settings */}
        <Card>
          <CardHeader>
            <h2 className="font-semibold text-[var(--md-on-surface)]">Inventory</h2>
          </CardHeader>
          <CardContent>
            <Input
              label="Low Stock Threshold"
              type="number"
              {...register("low_stock_threshold", { valueAsNumber: true })}
              error={errors.low_stock_threshold?.message}
            />
            <p className="text-xs text-[var(--md-on-surface-variant)]">
              Alert when stock falls below this level
            </p>
          </CardContent>
        </Card>

        {/* Receipt */}
        <Card>
          <CardHeader>
            <h2 className="font-semibold text-[var(--md-on-surface)]">Receipt</h2>
          </CardHeader>
          <CardContent className="space-y-4">
            <Input
              label="Receipt Header"
              {...register("receipt_header")}
              placeholder="e.g. Thank you for your purchase!"
            />
            <Input
              label="Receipt Footer"
              {...register("receipt_footer")}
              placeholder="e.g. Visit us again!"
            />
            {/* Receipt preview */}
            <div className="rounded-xl border border-[var(--md-outline-variant)] bg-[var(--md-surface)] p-4">
              <p className="mb-2 text-xs font-medium uppercase text-[var(--md-on-surface-variant)]">
                Receipt Preview
              </p>
              <div className="space-y-1 text-center text-xs text-[var(--md-on-surface)]">
                <p className="font-bold">{user?.email?.split("@")[0] || "Your Store"}</p>
                {watch("receipt_header") && <p>{watch("receipt_header")}</p>}
                <div className="my-2 border-t border-dashed border-[var(--md-outline-variant)]" />
                <p>Tusker Lager x2 — KES 700</p>
                <p>Subtotal — KES 700</p>
                <p>VAT (16%) — KES 112</p>
                <p className="font-bold">Total — KES 812</p>
                <div className="my-2 border-t border-dashed border-[var(--md-outline-variant)]" />
                {watch("receipt_footer") && <p>{watch("receipt_footer")}</p>}
                <p className="text-[10px] text-[var(--md-on-surface-variant)]">Powered by joat stores</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Save */}
        <div className="flex justify-end">
          <Button type="submit" disabled={!isDirty || updateSettings.isPending}>
            <Save size={16} className="mr-2" />
            {updateSettings.isPending ? "Saving..." : "Save Settings"}
          </Button>
        </div>
      </form>
    </div>
  );
}
