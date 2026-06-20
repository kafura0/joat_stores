"use client";

import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import type { ThemeData, PresetItem } from "@/types/theme";
import { COLOR_LABELS, FONT_OPTIONS } from "@/types/theme";

const COLOR_FIELDS = Object.keys(COLOR_LABELS) as (keyof ThemeData)[];

export default function ThemeSettingsPage() {
  const { data: theme, isLoading, error, refresh } = useApi<ThemeData>("/store/themes/");
  const { data: presetsData, isLoading: presetsLoading } = useApi<{ presets: PresetItem[] }>("/store/themes/presets/");
  const [form, setForm] = useState<ThemeData | null>(null);
  const [saving, setSaving] = useState(false);
  const [applying, setApplying] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    if (theme) setForm(theme);
  }, [theme]);

  const updateField = useCallback((field: keyof ThemeData, value: string | number | boolean) => {
    setForm((prev) => (prev ? { ...prev, [field]: value } : prev));
  }, []);

  const handleSave = useCallback(async () => {
    if (!form) return;
    setSaving(true);
    setSaveMessage(null);
    try {
      await api.patch("/store/themes/", form);
      setSaveMessage({ type: "success", text: "Theme saved successfully." });
      refresh();
    } catch {
      setSaveMessage({ type: "error", text: "Failed to save theme. Check your connection and try again." });
    } finally {
      setSaving(false);
    }
  }, [form, refresh]);

  const handleApplyPreset = useCallback(async (slug: string) => {
    setApplying(slug);
    setSaveMessage(null);
    try {
      const res = await api.post("/store/themes/apply-preset/", { preset: slug });
      setForm(res.data.data);
      setSaveMessage({ type: "success", text: `Preset "${slug}" applied.` });
    } catch {
      setSaveMessage({ type: "error", text: "Failed to apply preset." });
    } finally {
      setApplying(null);
    }
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-300 border-t-blue-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
        <p className="text-red-700">{error}</p>
        <button onClick={refresh} className="mt-3 rounded bg-red-600 px-4 py-2 text-sm text-white hover:bg-red-700">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-xl font-semibold text-gray-900">Theme Settings</h2>
        <p className="mt-1 text-sm text-gray-500">
          Customize your store&apos;s look and feel. Changes appear immediately on your storefront.
        </p>
      </div>

      {saveMessage && (
        <div
          className={`rounded-lg border px-4 py-3 text-sm ${
            saveMessage.type === "success"
              ? "border-green-200 bg-green-50 text-green-700"
              : "border-red-200 bg-red-50 text-red-700"
          }`}
        >
          {saveMessage.text}
        </div>
      )}

      {/* ── Presets ────────────────────────────────────────────── */}
      <section>
        <h3 className="mb-3 text-lg font-medium text-gray-900">Presets</h3>
        <p className="mb-4 text-sm text-gray-500">
          Start from a pre-built style. Applying a preset overwrites all theme tokens.
        </p>
        {presetsLoading ? (
          <div className="text-sm text-gray-400">Loading presets...</div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {(presetsData?.presets ?? []).map((preset) => (
              <button
                key={preset.slug}
                onClick={() => handleApplyPreset(preset.slug)}
                disabled={applying === preset.slug}
                className={`rounded-lg border-2 p-4 text-left transition-all hover:shadow-md ${
                  form?.preset_slug === preset.slug
                    ? "border-blue-500 bg-blue-50"
                    : "border-gray-200 bg-white"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-gray-900">{preset.label}</span>
                  {applying === preset.slug && (
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
                  )}
                </div>
                <p className="mt-1 text-xs text-gray-500">{preset.description}</p>
              </button>
            ))}
          </div>
        )}
      </section>

      {form && (
        <>
          {/* ── Colors ──────────────────────────────────────────── */}
          <section>
            <h3 className="mb-3 text-lg font-medium text-gray-900">Colors</h3>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {COLOR_FIELDS.map((field) => (
                <div key={field}>
                  <label className="mb-1 block text-xs font-medium text-gray-600">
                    {COLOR_LABELS[field]}
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      type="color"
                      value={String(form[field])}
                      onChange={(e) => updateField(field, e.target.value)}
                      className="h-9 w-9 cursor-pointer rounded border border-gray-300"
                    />
                    <input
                      type="text"
                      value={String(form[field])}
                      onChange={(e) => updateField(field, e.target.value)}
                      className="flex-1 rounded border border-gray-300 px-2 py-1.5 text-sm"
                    />
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* ── Typography ──────────────────────────────────────── */}
          <section>
            <h3 className="mb-3 text-lg font-medium text-gray-900">Typography</h3>
            <div className="grid gap-4 sm:grid-cols-2">
              {(["font_family_heading", "font_family_body"] as const).map((field) => (
                <div key={field}>
                  <label className="mb-1 block text-xs font-medium text-gray-600">
                    {field === "font_family_heading" ? "Heading Font" : "Body Font"}
                  </label>
                  <select
                    value={String(form[field])}
                    onChange={(e) => updateField(field, e.target.value)}
                    className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
                    style={{ fontFamily: String(form[field]) }}
                  >
                    {FONT_OPTIONS.map((f) => (
                      <option key={f} value={f} style={{ fontFamily: f }}>
                        {f}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">Base Size</label>
                <input
                  type="text"
                  value={form.font_size_base}
                  onChange={(e) => updateField("font_size_base", e.target.value)}
                  className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
                  placeholder="1rem"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">Heading Scale</label>
                <input
                  type="number"
                  step="0.001"
                  min="1"
                  max="2"
                  value={form.font_size_scale}
                  onChange={(e) => updateField("font_size_scale", parseFloat(e.target.value) || 1.25)}
                  className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
                />
              </div>
            </div>
          </section>

          {/* ── Layout ──────────────────────────────────────────── */}
          <section>
            <h3 className="mb-3 text-lg font-medium text-gray-900">Layout & Spacing</h3>
            <div className="grid gap-4 sm:grid-cols-3">
              {(["section_padding_y", "card_padding", "container_max_width"] as const).map((field) => (
                <div key={field}>
                  <label className="mb-1 block text-xs font-medium text-gray-600 capitalize">
                    {field.replace(/_/g, " ")}
                  </label>
                  <input
                    type="text"
                    value={String(form[field])}
                    onChange={(e) => updateField(field, e.target.value)}
                    className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
                  />
                </div>
              ))}
            </div>
          </section>

          {/* ── Border Radius ───────────────────────────────────── */}
          <section>
            <h3 className="mb-3 text-lg font-medium text-gray-900">Border Radius</h3>
            <div className="grid gap-4 sm:grid-cols-4">
              {(["radius_sm", "radius_md", "radius_lg", "radius_full"] as const).map((field) => (
                <div key={field}>
                  <label className="mb-1 block text-xs font-medium text-gray-600 capitalize">
                    {field.replace("radius_", "")}
                  </label>
                  <input
                    type="text"
                    value={String(form[field])}
                    onChange={(e) => updateField(field, e.target.value)}
                    className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
                  />
                </div>
              ))}
            </div>
          </section>

          {/* ── Shadows ─────────────────────────────────────────── */}
          <section>
            <h3 className="mb-3 text-lg font-medium text-gray-900">Shadows</h3>
            <div className="grid gap-4 sm:grid-cols-3">
              {(["shadow_sm", "shadow_md", "shadow_lg"] as const).map((field) => (
                <div key={field}>
                  <label className="mb-1 block text-xs font-medium text-gray-600 capitalize">
                    {field.replace("shadow_", "")}
                  </label>
                  <input
                    type="text"
                    value={String(form[field])}
                    onChange={(e) => updateField(field, e.target.value)}
                    className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm font-mono"
                  />
                </div>
              ))}
            </div>
          </section>

          {/* ── Announcement Bar (Phase 3) ──────────────────────── */}
          <section>
            <h3 className="mb-3 text-lg font-medium text-gray-900">Announcement Bar</h3>
            <div className="space-y-3 rounded-lg border border-gray-200 p-4">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={form.announcement_enabled}
                  onChange={(e) => updateField("announcement_enabled", e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300"
                />
                <span className="text-sm text-gray-700">Enable announcement bar</span>
              </label>
              {form.announcement_enabled && (
                <input
                  type="text"
                  value={form.announcement_text}
                  onChange={(e) => updateField("announcement_text", e.target.value)}
                  placeholder="Free delivery on orders over KES 1,000!"
                  className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
                />
              )}
            </div>
          </section>

          {/* ── Custom CSS (Phase 3) ────────────────────────────── */}
          <section>
            <h3 className="mb-3 text-lg font-medium text-gray-900">Custom CSS</h3>
            <p className="mb-2 text-sm text-gray-500">
              Advanced: inject raw CSS. Overrides any token above. Use responsibly.
            </p>
            <textarea
              value={form.custom_css}
              onChange={(e) => updateField("custom_css", e.target.value)}
              rows={6}
              className="w-full rounded border border-gray-300 px-3 py-2 font-mono text-sm"
              placeholder="/* Your custom CSS here */
.my-section {
  --color-primary: rebeccapurple;
}"
            />
          </section>

          {/* ── Save ────────────────────────────────────────────── */}
          <div className="flex items-center gap-4 border-t border-gray-200 pt-6">
            <button
              onClick={handleSave}
              disabled={saving}
              className="rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save Changes"}
            </button>
            <button
              onClick={() => setForm(theme ?? null)}
              disabled={saving}
              className="rounded-lg border border-gray-300 px-6 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              Reset
            </button>
            <a
              href={typeof window !== "undefined" ? `${window.location.protocol}//${window.location.hostname}:3000` : "#"}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-lg border border-gray-300 px-6 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Preview Storefront
            </a>
          </div>
        </>
      )}
    </div>
  );
}
