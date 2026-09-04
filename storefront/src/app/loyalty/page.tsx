"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { Star, Phone } from "lucide-react";

interface ILoyaltyAccount {
  id: string;
  customer_phone: string;
  points_balance: number;
  lifetime_earned: number;
}

interface IStampCard {
  id: string;
  name: string;
  stamps_required: number;
  reward_description: string;
  points_per_stamp: number;
  is_active: boolean;
}

interface ICustomerStampCard {
  id: string;
  stamp_card: IStampCard;
  customer_phone: string;
  stamps_count: number;
  redeemed_count: number;
  last_stamp_at: string | null;
  progress_percent: number;
}

interface IPointsTransaction {
  id: string;
  delta: number;
  balance_after: number;
  source: string;
  reference: string;
  occurred_at: string;
}

export default function LoyaltyPage() {
  const [phone, setPhone] = useState("");
  const [searched, setSearched] = useState(false);

  const [account, setAccount] = useState<ILoyaltyAccount | null>(null);
  const [stampCards, setStampCards] = useState<IStampCard[]>([]);
  const [myStampCards, setMyStampCards] = useState<ICustomerStampCard[]>([]);
  const [transactions, setTransactions] = useState<IPointsTransaction[]>([]);
  const [loading, setLoading] = useState(false);

  // Load stamp card programs on mount
  useEffect(() => {
    api.get("/loyalty/stamp-cards/").then(({ data }) => setStampCards(data)).catch(() => {});
  }, []);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!phone.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const [accountRes, stampsRes, historyRes] = await Promise.allSettled([
        api.get(`/loyalty/account/?phone=${phone}`),
        api.get(`/loyalty/my-stamp-cards/?phone=${phone}`),
        api.get(`/loyalty/history/?phone=${phone}`),
      ]);
      if (accountRes.status === "fulfilled") setAccount(accountRes.value.data);
      if (stampsRes.status === "fulfilled") setMyStampCards(stampsRes.value.data);
      if (historyRes.status === "fulfilled") setTransactions(historyRes.value.data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-[var(--md-on-surface)]">
          Loyalty & Rewards
        </h1>
        <p className="mt-1 text-sm text-[var(--md-on-surface-variant)]">
          Check your points balance, stamp card progress, and transaction history.
        </p>
      </div>

      {/* Phone lookup */}
      <form onSubmit={handleSearch} className="mb-8">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Phone className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--md-on-surface-variant)]" />
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="Enter your phone number"
              className="w-full rounded-xl border border-[var(--md-outline)] bg-[var(--md-surface)] py-3 pl-10 pr-4 text-sm focus:border-[var(--md-primary)] focus:outline-none"
            />
          </div>
          <button
            type="submit"
            className="rounded-xl px-6 py-3 text-sm font-medium text-white"
            style={{ backgroundColor: "var(--color-primary)" }}
          >
            Look Up
          </button>
        </div>
      </form>

      {!searched && (
        <div className="space-y-6">
          {stampCards.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold text-[var(--md-on-surface)] mb-4">
                Our Rewards Programs
              </h2>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                {stampCards.map((card) => (
                  <div key={card.id} className="rounded-xl border border-[var(--md-outline-variant)] bg-[var(--md-surface)] p-6">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[var(--md-primary-container)]">
                        <Star className="h-5 w-5 text-[var(--md-primary)]" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-[var(--md-on-surface)]">{card.name}</h3>
                        <p className="text-xs text-[var(--md-on-surface-variant)]">
                          {card.stamps_required} stamps to earn reward
                        </p>
                      </div>
                    </div>
                    <p className="text-sm text-[var(--md-on-surface-variant)]">
                      Reward: <span className="font-medium text-[var(--md-on-surface)]">{card.reward_description}</span>
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="rounded-xl border border-[var(--md-outline-variant)] bg-[var(--md-surface)] py-12 text-center">
            <Star className="mx-auto mb-4 h-12 w-12 text-[var(--md-on-surface-variant)] opacity-40" />
            <p className="text-[var(--md-on-surface-variant)]">
              Enter your phone number above to check your points and stamp card progress.
            </p>
          </div>
        </div>
      )}

      {searched && loading && (
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-32 animate-pulse rounded-xl bg-[var(--md-surface-container)]" />
          ))}
        </div>
      )}

      {searched && !loading && !account && (
        <div className="rounded-xl border border-[var(--md-outline-variant)] bg-[var(--md-surface)] py-12 text-center">
          <p className="text-[var(--md-on-surface-variant)]">
            No loyalty account found for this phone number.
          </p>
          <p className="mt-2 text-sm text-[var(--md-on-surface-variant)]">
            Place an order to start earning points!
          </p>
        </div>
      )}

      {searched && account && (
        <div className="space-y-6">
          {/* Points balance */}
          <div className="rounded-xl border border-[var(--md-outline-variant)] bg-[var(--md-surface)] p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-[var(--md-on-surface-variant)]">Your Points Balance</p>
                <p className="text-4xl font-bold text-[var(--md-primary)] mt-1">
                  {account.points_balance.toLocaleString()}
                </p>
                <p className="text-xs text-[var(--md-on-surface-variant)] mt-1">
                  Lifetime earned: {account.lifetime_earned.toLocaleString()} points
                </p>
              </div>
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[var(--md-primary-container)]">
                <Star className="h-8 w-8 text-[var(--md-primary)]" />
              </div>
            </div>
          </div>

          {/* Stamp cards progress */}
          {myStampCards.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold text-[var(--md-on-surface)] mb-4">
                Your Stamp Cards
              </h2>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                {myStampCards.map((sc) => (
                  <div key={sc.id} className="rounded-xl border border-[var(--md-outline-variant)] bg-[var(--md-surface)] p-6">
                    <h3 className="font-semibold text-[var(--md-on-surface)] mb-2">
                      {sc.stamp_card.name}
                    </h3>
                    <div className="mb-3">
                      <div className="flex justify-between text-xs text-[var(--md-on-surface-variant)] mb-1">
                        <span>{sc.stamps_count} / {sc.stamp_card.stamps_required} stamps</span>
                        <span>{sc.progress_percent}%</span>
                      </div>
                      <div className="h-2 rounded-full bg-[var(--md-surface-container)]">
                        <div
                          className="h-full rounded-full transition-all"
                          style={{
                            width: `${sc.progress_percent}%`,
                            backgroundColor: "var(--color-primary)",
                          }}
                        />
                      </div>
                    </div>
                    <p className="text-xs text-[var(--md-on-surface-variant)]">
                      Reward: {sc.stamp_card.reward_description}
                    </p>
                    {sc.redeemed_count > 0 && (
                      <p className="text-xs text-[var(--md-primary)] mt-1">
                        Redeemed {sc.redeemed_count} time{sc.redeemed_count > 1 ? "s" : ""}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Transaction history */}
          {transactions.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold text-[var(--md-on-surface)] mb-4">
                Points History
              </h2>
              <div className="rounded-xl border border-[var(--md-outline-variant)] bg-[var(--md-surface)] overflow-hidden">
                <div className="divide-y divide-[var(--md-outline-variant)]">
                  {transactions.map((tx) => (
                    <div key={tx.id} className="flex items-center justify-between px-4 py-3">
                      <div>
                        <span className={tx.delta > 0 ? "text-green-600 font-medium" : "text-red-500 font-medium"}>
                          {tx.delta > 0 ? "+" : ""}{tx.delta}
                        </span>
                        <span className="ml-2 text-sm text-[var(--md-on-surface-variant)]">
                          {tx.source === "order" ? "Order" : tx.source === "redemption" ? "Redemption" : tx.source}
                        </span>
                      </div>
                      <span className="text-xs text-[var(--md-on-surface-variant)]">
                        {new Date(tx.occurred_at).toLocaleDateString()}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
